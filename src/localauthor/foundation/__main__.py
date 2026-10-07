"""Operator-only commands. Generated answers cannot authorize curation or training."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from ..errors import PolicyError
from .experience import ExperienceStore
from .models import child, identifier, local_path, read_object, register_model, write_new
from .service import FoundationService


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LocalAuthor: modelos locais, conhecimento e curadoria")
    parser.add_argument("--home", type=Path, required=True, help="Mesma pasta de dados usada pelo servidor LocalAuthor")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    register = commands.add_parser("register-model")
    register.add_argument("kind", choices=["text", "image"])
    register.add_argument("directory", type=Path)
    for name in ("model-id", "revision", "license", "reviewed-by"):
        register.add_argument("--" + name, required=True)
    register.add_argument("--reviewed-local-code", action="store_true")
    register.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    register.add_argument("--dtype", choices=["float32", "float16", "bfloat16"], default="float32")
    register.add_argument("--context-tokens", type=int, default=4096)
    register.add_argument("--output-tokens", type=int, default=768)
    register.add_argument("--enable-thinking", action="store_true", help="Exige template/modelo textual homologado; não altera os pesos.")
    register.add_argument("--generation-seconds", type=int, default=300, help="Orçamento cooperativo de geração, entre 1 e 3600 segundos; não limita carregamento.")
    knowledge = commands.add_parser("import-md")
    knowledge.add_argument("project_id")
    knowledge.add_argument("file", type=Path)
    knowledge.add_argument("--title", required=True)
    show = commands.add_parser("experience")
    show.add_argument("project_id")
    show.add_argument("run_id")
    review = commands.add_parser("review")
    review.add_argument("project_id")
    review.add_argument("run_id")
    review.add_argument("--expected-hash", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--verification-note", default="")
    review.add_argument("--split", choices=["train", "validation", "test"], default="train")
    for flag in ("accepted", "training-allowed", "rights-reviewed", "verified"):
        review.add_argument("--" + flag, action="store_true")
    export = commands.add_parser("export-training")
    export.add_argument("project_id")
    export.add_argument("kind", choices=["text", "code", "image"])
    args = parser.parse_args(argv)
    try:
        home = local_path(args.home)
        if args.command == "status":
            result = FoundationService(home).status()
        elif args.command == "register-model":
            target = home / "foundation" / f"{args.kind}-model.json"
            register_model(args.directory, target, model_id=args.model_id,
                revision=args.revision, license=args.license, reviewed_by=args.reviewed_by,
                capability=args.kind, reviewed_local_code=args.reviewed_local_code,
                device=args.device, dtype=args.dtype, context_tokens=args.context_tokens,
                output_tokens=args.output_tokens, enable_thinking=args.enable_thinking,
                generation_seconds=args.generation_seconds)
            result = {"manifest": str(target), "registered": True, "inference_tested": False}
        elif args.command == "import-md":
            identifier(args.project_id)
            if (home / "server.lock").exists():
                raise PolicyError("Encerre o servidor antes de atualizar o manifesto Markdown pelo CLI.")
            file = local_path(args.file)
            if file.suffix.lower() != ".md":
                raise PolicyError("Selecione Markdown.")
            with file.open("rb") as stream:
                raw = stream.read(200001)
            if len(raw) > 200000:
                raise PolicyError("Markdown excede 200 KB.")
            text = raw.decode("utf-8")
            from ..safety import reject_secrets
            reject_secrets(text)
            root = local_path(home / "foundation" / "knowledge" / args.project_id)
            root.mkdir(parents=True, exist_ok=True)
            manifest = root / "sources.json"
            data = read_object(manifest) if manifest.exists() else {"schema": 1, "sources": []}
            if data.get("schema") != 1 or not isinstance(data.get("sources"), list) or len(data["sources"]) >= 200:
                raise PolicyError("Manifesto inválido ou limite de fontes atingido.")
            name = uuid.uuid4().hex + ".md"
            destination = child(root, name)
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
            data["sources"].append({"path": name, "scope": args.project_id,
                "title": args.title, "sha256": hashlib.sha256(raw).hexdigest(), "training_allowed": False})
            temporary = root / (uuid.uuid4().hex + ".json")
            try:
                write_new(temporary, data)
                local_path(manifest)
                os.replace(temporary, manifest)
            except Exception:
                destination.unlink(missing_ok=True)
                temporary.unlink(missing_ok=True)
                raise
            result = {"source": name, "scope": args.project_id, "training_allowed": False}
        elif args.command == "experience":
            result = ExperienceStore(home).get(args.project_id, args.run_id)
        elif args.command == "review":
            ExperienceStore(home).review(args.project_id, args.run_id,
                expected_hash=args.expected_hash, accepted=args.accepted,
                training_allowed=args.training_allowed, rights_reviewed=args.rights_reviewed,
                verified=args.verified, reviewer=args.reviewer,
                verification_note=args.verification_note, split=args.split)
            result = {"reviewed": True, "weights_modified": False}
        else:
            rows = ExperienceStore(home).training_rows(args.project_id, args.kind)
            if not rows:
                raise PolicyError("Não há experiências autorizadas e verificadas para exportação.")
            if args.kind == "image":
                service = FoundationService(home)
                for row in rows:
                    service.image(args.project_id, row["metadata"]["artifact_id"])
                    row["image_file"] = str(child(home / "foundation" / "artifacts",
                        f"{args.project_id}/{row['metadata']['artifact_id']}.png"))
            target = local_path(home / "exports" / ("foundation-" + uuid.uuid4().hex + ".jsonl"))
            target.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            result = {"file": str(target), "examples": len(rows), "weights_modified": False,
                "notice": "Dataset candidato; exige adaptação à receita de treino e revisão de duplicatas semânticas. Revogação futura não apaga exportações anteriores."}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PolicyError, OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
