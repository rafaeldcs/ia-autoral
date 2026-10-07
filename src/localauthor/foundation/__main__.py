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
    register.add_argument("--backend", choices=["transformers", "gguf-docker"], default="transformers")
    register.add_argument("--gguf-image-id")
    register.add_argument("--gguf-volume")
    register.add_argument("--reasoning-budget", type=int, default=0)
    knowledge = commands.add_parser("import-md")
    knowledge.add_argument("project_id")
    knowledge.add_argument("file", type=Path)
    knowledge.add_argument("--title", required=True)
    knowledge.add_argument("--source-id", help="Identidade estável; nova versão invalida derivados antigos")
    revoke = commands.add_parser("revoke-source")
    revoke.add_argument("project_id")
    revoke.add_argument("source_id")
    recall = commands.add_parser("recall")
    recall.add_argument("project_id")
    recall.add_argument("query")
    recall.add_argument("--code-revision", required=True)
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
    export.add_argument("--split", choices=["train", "validation"], default="train")
    args = parser.parse_args(argv)
    try:
        home = local_path(args.home)
        if args.command == "status":
            result = FoundationService(home).status()
        elif args.command == "register-model":
            if args.backend == "transformers" and (args.gguf_image_id or args.gguf_volume or args.reasoning_budget):
                raise PolicyError("Opções GGUF exigem backend gguf-docker.")
            runtime_profile = {"image_id": args.gguf_image_id, "volume": args.gguf_volume,
                               "reasoning_budget": args.reasoning_budget} if args.backend == "gguf-docker" else {}
            target = home / "foundation" / f"{args.kind}-model.json"
            register_model(args.directory, target, model_id=args.model_id,
                revision=args.revision, license=args.license, reviewed_by=args.reviewed_by,
                capability=args.kind, reviewed_local_code=args.reviewed_local_code,
                device=args.device, dtype=args.dtype, context_tokens=args.context_tokens,
                output_tokens=args.output_tokens, enable_thinking=args.enable_thinking, generation_seconds=args.generation_seconds, backend=args.backend, runtime_profile=runtime_profile)
            result = {"manifest": str(target), "registered": True, "inference_tested": False}
        elif args.command == "import-md":
            from .knowledge import import_markdown
            entry = import_markdown(home, args.project_id, args.file, args.title, args.source_id)
            result = {**entry, "source": entry["path"]}
        elif args.command == "revoke-source":
            from .knowledge import revoke_source
            result = revoke_source(home, args.project_id, args.source_id)
        elif args.command == "recall":
            result = ExperienceStore(home).recall(args.project_id, args.query, code_revision=args.code_revision)
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
            rows = ExperienceStore(home).training_rows(args.project_id, args.kind, args.split)
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
