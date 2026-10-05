"""Operator learning lifecycle. Read --help; none of these commands run from chat."""
import argparse
import json
from pathlib import Path
import sys

from ..errors import PolicyError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-data", help="Rejeita fontes sem direitos e contaminação")
    validate.add_argument("dataset", type=Path)
    converter = sub.add_parser("convert", help="JSONL revisado + curadoria de grupos/direitos para dataset; não autoriza dados")
    converter.add_argument("export", type=Path)
    converter.add_argument("curation", type=Path)
    converter.add_argument("--output", type=Path, required=True)
    trainer = sub.add_parser("train", help="Piloto/treino LoRA CPU Qwen3, somente em sandbox")
    trainer.add_argument("experiment", type=Path)
    trainer.add_argument("--base-manifest", type=Path, required=True)
    trainer.add_argument("--dataset", type=Path, required=True)
    trainer.add_argument("--output", type=Path, required=True)
    trainer.add_argument("--resume", type=Path)
    export = sub.add_parser("export", help="Funde LoRA em NOVA base Safetensors; comprova recarga")
    export.add_argument("experiment", type=Path)
    export.add_argument("--base-manifest", type=Path, required=True)
    export.add_argument("--dataset", type=Path, required=True)
    export.add_argument("--checkpoint", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--model-id", required=True)
    export.add_argument("--reviewed-by", required=True)
    export.add_argument("--output-bytes", type=int, default=10_000_000_000,
                        help="Orçamento separado para a base completa fundida; máximo 10 GB")
    evaluator = sub.add_parser("evaluate", help="Modelo real, oráculos textuais congelados")
    evaluator.add_argument("model_manifest", type=Path)
    evaluator.add_argument("cases", type=Path)
    evaluator.add_argument("--report", type=Path, required=True)
    comparison = sub.add_parser("compare", help="Base/candidato com os mesmos casos e condições congeladas")
    comparison.add_argument("--base-manifest", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--cases", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    promotion = sub.add_parser("promote", help="Ativação atômica exige aprovação humana")
    promotion.add_argument("--home", type=Path, required=True)
    promotion.add_argument("--candidate", type=Path, required=True)
    promotion.add_argument("--evaluation", type=Path, required=True)
    promotion.add_argument("--approval", type=Path, required=True)
    promotion.add_argument("--kind", choices=["text", "image"], default="text")
    rollback = sub.add_parser("rollback", help="Restaura somente a versão anterior do journal")
    rollback.add_argument("--home", type=Path, required=True)
    rollback.add_argument("journal", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-data":
            from .dataset import validate_dataset
            result = validate_dataset(args.dataset)
            result = {k: v for k, v in result.items() if k != "dataset"}
        elif args.command == "train":
            from .training import train
            result = train(args.experiment, args.base_manifest, args.dataset, args.output, resume=args.resume)
        elif args.command == "convert":
            from .conversion import convert_jsonl
            result = convert_jsonl(args.export, args.curation, args.output)
        elif args.command == "evaluate":
            from .evaluation import evaluate
            result = evaluate(args.model_manifest, args.cases, args.report)
        elif args.command == "export":
            from .export import export_candidate
            result = export_candidate(args.experiment, args.base_manifest, args.dataset, args.checkpoint,
                         args.output, model_id=args.model_id, reviewed_by=args.reviewed_by,
                         output_bytes=args.output_bytes)
        elif args.command == "compare":
            from .evaluation import compare
            result = compare(args.base_manifest, args.candidate, args.cases, args.output)
        elif args.command == "promote":
            from .promotion import promote
            result = promote(args.home, args.candidate, args.evaluation, args.approval, args.kind)
        else:
            from .promotion import rollback
            result = rollback(args.home, args.journal)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status", "completed") in {"completed", "passed", "exported-not-promoted"} else 1
    except (PolicyError, OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
