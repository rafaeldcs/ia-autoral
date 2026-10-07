#!/usr/bin/env python3
"""Opt-in checkpoint smoke: real inference, no doubles or competence claims."""
import argparse
import importlib.metadata
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from localauthor.foundation.context import markdown_evidence
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.knowledge import import_markdown
from localauthor.foundation.models import ModelSpec, digest, register_model, write_new
from localauthor.foundation.service import FoundationService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Use relatório novo; não sobrescrever evidência.")
    canaries = require_isolated_process()
    manifest = args.home / "foundation/text-model.json"
    if not manifest.exists():
        register_model(args.weights, manifest, model_id="Qwen/Qwen3-0.6B", revision=args.revision,
                       license="Apache-2.0", reviewed_by="Codex: revisão técnica, não aprovação humana de promoção",
                       capability="text", device="cpu", dtype="float32", context_tokens=4096, output_tokens=192)
    spec = ModelSpec.load(manifest, "text")
    spec.verify()
    imports = []
    notes = sorted((ROOT / "docs/aprendizado-local/conhecimento").glob("*.md"))
    if len(notes) != 7:
        raise ValueError("Seleção de conhecimento incorreta.")
    for note in notes:
        imports.append(import_markdown(args.home, "learning-v1", note, note.stem, note.stem))
    service = FoundationService(args.home)
    # Thirty internal retrieval checks, with explicit expected source identities.
    queries = [
        ("01_", ["procedência confiabilidade", "hipótese evidência", "permissões ferramentas", "identidade LocalAuthor"]),
        ("02_", ["orçamento contexto", "conflitos fontes", "histórico conversa", "português identificadores"]),
        ("03_", ["PostgreSQL NULLS LAST", "CancellationToken async", "Dapper transações", "Null validação", "TargetFramework"]),
        ("04_", ["webhooks idempotência", "SSR hidratação", "APIs autenticação", "filas confirmação"]),
        ("05_", ["teste regressão", "zero testes", "sandbox ferramentas", "cancelamento repetição"]),
        ("06_", ["composição visual", "cores PNG", "ícones série", "legenda imagem", "brief vaso"]),
        ("07_", ["memória treinamento", "esquecimento revogação", "relações hipótese", "experiência obsoleta"]),
    ]
    retrieval = []
    root = args.home / "foundation/knowledge/learning-v1"
    for prefix, prompts in queries:
        for prompt in prompts:
            evidence = markdown_evidence(root, prompt, "learning-v1")
            retrieval.append({"query": prompt, "expected_prefix": prefix,
                              "passed": any(e["title"].startswith(prefix) for e in evidence),
                              "sources": evidence})
    other_root = args.home / "foundation/knowledge/isolated-v1"
    if markdown_evidence(other_root, "CancellationToken", "isolated-v1"):
        raise ValueError("Mistura de projetos.")
    outputs = []
    for prompt, fmt, history in [
        ("Explique em duas frases a diferença entre memória e treinamento.", "text", []),
        ("Escreva somente uma função C# bool IsPositive(int value) que retorne se value é maior que zero.", "code", []),
        ("Qual nome escolhemos para o projeto? Responda apenas o nome.", "text",
         [{"role": "user", "content": "Escolhemos o nome Aurora para o projeto."},
          {"role": "assistant", "content": "O projeto se chama Aurora."}]),
    ]:
        started = time.monotonic()
        result = service.answer("learning-v1", prompt, history, [], input_format=fmt)
        outputs.append({"prompt": prompt, "result": result, "seconds": time.monotonic() - started})
    report = {"kind": "real-checkpoint-smoke-not-qualification", "model": spec.provenance(),
              "model_manifest_sha256": digest(manifest), "isolation": canaries,
              "versions": {p: importlib.metadata.version(p) for p in ("torch", "transformers", "peft", "diffusers")},
              "imports": imports, "retrieval": retrieval, "retrieval_passed": sum(r["passed"] for r in retrieval),
              "retrieval_total": len(retrieval), "outputs": outputs, "promotion": False,
              "weights_modified": False, "human_review": "pending"}
    write_new(args.report, report)
    print(json.dumps({"report": str(args.report), "outputs": len(outputs),
                      "retrieval": [report["retrieval_passed"], len(retrieval)], "qualification": False}))


if __name__ == "__main__":
    main()
