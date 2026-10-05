"""Strict, provenance-bound development data. No human decisions are inferred."""
from __future__ import annotations

from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

from ..errors import PolicyError
from ..safety import reject_secrets
from .models import child, digest, identifier, local_path, read_object


def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _approval(value: dict, root: Path, binding: dict):
    if (not isinstance(value, dict) or any(value.get(flag) is not True for flag in
            ("accepted", "verified", "rights_reviewed", "training_allowed"))
            or not isinstance(value.get("reviewer"), str) or not value["reviewer"].strip()
            or not re.fullmatch(r"[a-f0-9]{64}", str(value.get("receipt_sha256", "")))):
        raise PolicyError("Aceitação, verificação, direitos e autorização exigem recibo humano explícito.")
    receipt_path = child(root, value.get("receipt_file"))
    if digest(receipt_path) != value["receipt_sha256"]:
        raise PolicyError("Recibo ausente ou alterado.")
    receipt = read_object(receipt_path)
    if (receipt.get("schema") != 1 or not isinstance(receipt.get("bindings"), list)
            or receipt.get("reviewer") != value["reviewer"]
            or any(receipt.get(flag) is not True for flag in
                   ("accepted", "verified", "rights_reviewed", "training_allowed"))
            or binding not in receipt.get("bindings", [])):
        raise PolicyError("Recibo não autoriza o conteúdo exato desta fonte/experiência.")


def validate_dataset(path: Path) -> dict:
    path = local_path(path)
    data = read_object(path)
    if data.get("schema") != 1 or data.get("purpose") != "foundation-development":
        raise PolicyError("Dataset deve ser de desenvolvimento; avaliação final não entra no trainer.")
    sources, rows = data.get("sources"), data.get("examples")
    if not isinstance(sources, dict) or not sources or not isinstance(rows, list) or not 2 <= len(rows) <= 2000:
        raise PolicyError("Declare fontes e exemplos suficientes, dentro do limite.")
    content_by_source = {}
    for key, source in sources.items():
        identifier(key)
        if not isinstance(source, dict):
            raise PolicyError("Fonte inválida.")
        _approval(source.get("approval"), path.parent, {"source_id": key, "sha256": source.get("sha256")})
        if (not isinstance(source.get("license"), str) or not source["license"].strip()
                or source.get("revoked") is not False):
            raise PolicyError("Licença e estado de revogação da fonte são obrigatórios.")
        content = child(path.parent, source.get("file"))
        if not content.is_file() or content.stat().st_size > 2000000 or digest(content) != source.get("sha256"):
            raise PolicyError("Fonte ausente, excessiva ou hash divergente.")
        text = content.read_text(encoding="utf-8")
        reject_secrets(text)
        content_by_source[key] = text
    ids, groups, normalized, comparisons = set(), {}, {}, []
    split_counts = {"train": 0, "validation": 0}
    for row in rows:
        if not isinstance(row, dict):
            raise PolicyError("Exemplo inválido.")
        ident = identifier(row.get("example_id"))
        if ident in ids:
            raise PolicyError("ID de exemplo repetido.")
        ids.add(ident)
        split = row.get("split")
        if split not in split_counts or row.get("modality") not in {"text", "code"}:
            raise PolicyError("Trainer aceita somente texto/código de treino e validação.")
        _approval(row.get("approval"), path.parent, {"example_id": ident,
                  "context_hash": row.get("context_hash"), "target_hash": row.get("target_hash")})
        for field in ("task_family", "project_group", "leakage_group"):
            identifier(row.get(field))
        for field in ("project_group", "leakage_group"):
            key = (field, row[field])
            if key in groups and groups[key] != split:
                raise PolicyError("Grupo de origem atravessa partições.")
            groups[key] = split
        refs = row.get("source_ids")
        if not isinstance(refs, list) or not refs or any(s not in sources for s in refs):
            raise PolicyError("Todo contexto e alvo exigem fontes autorizadas.")
        messages = row.get("messages")
        if (not isinstance(messages, list) or len(messages) < 2 or len(messages) > 32
                or any(not isinstance(m, dict) for m in messages)
                or messages[-1].get("role") != "assistant"
                or not any(m.get("role") == "user" for m in messages[:-1])):
            raise PolicyError("Conversa precisa de pedido e resposta-alvo.")
        for m in messages:
            if (set(m) != {"role", "content"} or m["role"] not in {"system", "user", "assistant"}
                    or not isinstance(m["content"], str) or not m["content"].strip()):
                raise PolicyError("Mensagem vazia ou formato inválido.")
            m["content"].encode("utf-8", errors="strict")
            reject_secrets(m["content"])
        if row.get("truncated") is not False:
            raise PolicyError("Exemplos truncados ou sem declaração de integridade não são aceitos.")
        if row.get("context_hash") != canonical_hash(messages[:-1]) or row.get("target_hash") != canonical_hash(messages[-1]):
            raise PolicyError("Hash do contexto/alvo não corresponde ao exemplo.")
        # Require full content in the approved source, including history. Merely
        # attaching an unrelated licensed README cannot authorize the example.
        full = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        def contains(text):
            if full in text: return True
            for line in text.splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if value == messages or (isinstance(value, dict) and value.get("messages") == messages):
                    return True
            return False
        if not any(contains(content_by_source[s]) for s in refs):
            raise PolicyError("Conteúdo integral não consta nas fontes revisadas.")
        # Shared product/system rules are provenance-bound above, but must not
        # turn unrelated tasks into near duplicates just because the boilerplate
        # is much longer than their requests. Keep the full conversational
        # history (including prior answers) in the problem fingerprint.
        normalized_input = " ".join(" ".join(m["role"] + ": " + m["content"]
                    for m in messages[:-1] if m["role"] != "system").casefold().split())
        if normalized_input in normalized:
            raise PolicyError("Entrada duplicada; deduplicar antes de treinar.")
        normalized[normalized_input] = split
        fingerprint = re.sub(r"\d+", "NUMBER", normalized_input)
        for other, other_split in comparisons:
            if other_split != split and SequenceMatcher(None, fingerprint, other, autojunk=False).ratio() >= 0.85:
                raise PolicyError("Possível variante entre partições; agrupe/revise a origem.")
        comparisons.append((fingerprint, split))
        split_counts[split] += 1
    if not all(split_counts.values()):
        raise PolicyError("Treino e validação precisam conter exemplos.")
    reserved = data.get("reserved_target_hashes")
    if not isinstance(reserved, list) or any(not isinstance(h, str) or not re.fullmatch(r"[a-f0-9]{64}", h) for h in reserved):
        raise PolicyError("Declare índice de exclusão das respostas reservadas, sem gabaritos.")
    for row in rows:
        # Exact known targets in *any* history message are contamination.
        if any(canonical_hash(m) in reserved for m in row["messages"]):
            raise PolicyError("Resposta reservada encontrada no contexto ou alvo.")
    return {"dataset": data, "sha256": digest(path), "split_counts": split_counts,
            "near_duplicate_review": "heurística conservadora; não garante deduplicação semântica universal"}


def validate_experiment(path: Path) -> dict:
    path = local_path(path)
    data = read_object(path)
    required = ("experiment_id", "code_revision", "base_manifest_sha256", "dataset_sha256",
                "tokenizer_hashes", "seed", "limits", "configuration", "hypothesis", "criteria", "code_inventory", "code_dirty")
    required += ("runtime_versions",)
    if data.get("schema") != 1 or any(k not in data for k in required):
        raise PolicyError("Manifesto de experimento incompleto.")
    identifier(data["experiment_id"])
    if not re.fullmatch(r"[a-f0-9]{40}", str(data["code_revision"])):
        raise PolicyError("Use revisão Git imutável.")
    for key in ("base_manifest_sha256", "dataset_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", str(data[key])):
            raise PolicyError("Hash de experimento inválido.")
    if type(data["seed"]) is not int or not 0 <= data["seed"] <= 2147483647:
        raise PolicyError("Seed inválida.")
    if not isinstance(data["tokenizer_hashes"], dict) or not data["tokenizer_hashes"]:
        raise PolicyError("Tokenizador precisa de inventário.")
    if type(data["code_dirty"]) is not bool or not isinstance(data["code_inventory"], dict) or not data["code_inventory"]:
        raise PolicyError("Declare alterações e hashes do código realmente executado.")
    root = Path(__file__).resolve().parents[3]
    required_code = {"src/localauthor/foundation/" + name for name in
                     (p.name for p in Path(__file__).parent.glob("*.py"))}
    required_code.update("src/localauthor/" + name for name in ("safety.py", "errors.py", "util.py"))
    if not required_code <= set(data["code_inventory"]):
        raise PolicyError("Inventário não cobre o trainer e seus controles.")
    for name, expected in data["code_inventory"].items():
        if not name.startswith("src/localauthor/") or digest(child(root, name)) != expected:
            raise PolicyError("Código do experimento mudou; congele um novo experimento.")
    if (not isinstance(data["runtime_versions"], dict) or set(data["runtime_versions"]) != {
            "torch", "transformers", "peft", "safetensors"}
            or any(not isinstance(v, str) or not v.strip() for v in data["runtime_versions"].values())):
        raise PolicyError("Congele as versões efetivas do runtime antes do treino.")
    for key, cap in (("steps", 10000), ("seconds", 7200), ("output_bytes", 10_000_000_000)):
        if not isinstance(data["limits"], dict):
            raise PolicyError("Limites inválidos.")
        value = data["limits"].get(key)
        if type(value) is not int or not 1 <= value <= cap:
            raise PolicyError("Orçamento explícito de passos/tempo/disco obrigatório.")
    if not data["hypothesis"] or not isinstance(data["criteria"], dict) or not data["criteria"]:
        raise PolicyError("Hipótese e critérios devem ser congelados antes do treino.")
    return data
