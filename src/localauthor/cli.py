from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from .config import Settings, default_home
from .errors import LocalAIError
from .util import write_json, read_json


def print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="localauthor", description="Plataforma local e laboratório de modelo autoral CPU, sem APIs de IA.")
    parser.add_argument("--home", type=Path, default=None, help="Diretório local de dados (fora dos projetos).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("token")
    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--port", type=int)
    sub.add_parser("diagnose")
    dataset_p = sub.add_parser("validate-dataset")
    dataset_p.add_argument("manifest", type=Path)
    train_p = sub.add_parser("train")
    train_p.add_argument("manifest", type=Path)
    train_p.add_argument("--output", type=Path, required=True)
    train_p.add_argument("--config", type=Path)
    train_p.add_argument("--steps", type=int, default=100)
    train_p.add_argument("--batch-size", type=int, default=2)
    train_p.add_argument("--tokenizer", choices=["byte", "bpe"], default="byte")
    train_p.add_argument("--resume", type=Path)
    gen_p = sub.add_parser("generate")
    gen_p.add_argument("checkpoint", type=Path)
    gen_p.add_argument("--prompt", default="")
    gen_p.add_argument("--max-tokens", type=int, default=64)
    backup_p = sub.add_parser("backup")
    backup_p.add_argument("output", type=Path)
    restore_p = sub.add_parser("restore")
    restore_p.add_argument("archive", type=Path)
    restore_p.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "restore":
            from .backup import restore_home
            print_json(restore_home(args.archive, args.destination))
            return 0
        settings = Settings.load(args.home)
        if args.command == "init":
            print_json({"initialized": str(settings.home), "offline": settings.offline, "token_file": str(settings.home/"api.token")})
        elif args.command == "token":
            print(settings.token)
        elif args.command == "serve":
            if args.port is not None:
                if not 1024 <= args.port <= 65535: raise ValueError("Porta fora do intervalo permitido.")
                settings.port = args.port
            from .application import Application
            from .server import serve
            ui = Path(__file__).resolve().parents[2]/"ui"
            if not ui.exists():
                raise ValueError("Execute a distribuição-fonte completa com PYTHONPATH=src; ui ausente.")
            serve(Application(settings), ui)
        elif args.command == "diagnose":
            from .diagnostics import diagnose
            result = diagnose(settings.home)
            write_json(settings.home/"hardware.json", result)
            print_json(result)
        elif args.command == "validate-dataset":
            from .dataset import validate_dataset
            result = validate_dataset(args.manifest)
            print_json({"manifest_hash": result["manifest_hash"], "counts": {s: len(v) for s, v in result["splits"].items()}, "test_text_returned": False})
        elif args.command == "train":
            from .nn.train import train
            from .nn.transformer import ModelConfig
            import signal
            import threading
            cancel = threading.Event()
            previous = signal.signal(signal.SIGINT, lambda *_: cancel.set())
            try:
                config = ModelConfig(**read_json(args.config)) if args.config else None
                print_json(train(args.manifest, args.output, config, steps=args.steps, batch_size=args.batch_size, tokenizer_kind=args.tokenizer, resume=args.resume, cancel=cancel, callback=lambda v: print_json(v)))
            finally:
                signal.signal(signal.SIGINT, previous)
        elif args.command == "generate":
            from .nn.checkpoint import load_checkpoint
            model, _, tokenizer, _, _ = load_checkpoint(args.checkpoint)
            ids = tokenizer.encode(args.prompt)
            out = model.generate(ids, args.max_tokens)
            print_json({"experimental_completion": tokenizer.decode(out, errors="replace"), "programming_qualified": False, "notice": "Saída experimental; não é proposta autorizada nem solução verificada."})
        elif args.command == "backup":
            from .backup import backup_home
            print_json(backup_home(settings, args.output))
        return 0
    except (LocalAIError, OSError, ValueError, ImportError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
