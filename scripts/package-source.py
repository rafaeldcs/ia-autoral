#!/usr/bin/env python3
"""Package an exact clean Git revision. This is source, not a trained-model release."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile

PRIVATE_SUFFIXES = {".safetensors", ".gguf", ".ggml", ".npz", ".npy", ".pt", ".pth",
                    ".ckpt", ".weights", ".onnx", ".sqlite3", ".db", ".pfx", ".p12", ".key"}


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60).stdout


def check_inventory(raw: bytes) -> None:
    if not raw:
        raise ValueError("Inventário Git vazio.")
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, _ = metadata.split()
        path = PurePosixPath(name.decode("utf-8"))
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise ValueError("Pacote de código não aceita links ou submódulos.")
        if path.is_absolute() or ".." in path.parts or "\\" in str(path):
            raise ValueError("Caminho inválido no inventário Git.")
        if (path.suffix.casefold() in PRIVATE_SUFFIXES or path.name.casefold().startswith(".env")
                or path.name in {"api.token", "server.lock"}
                or any(part in {"runtime-data", "corpus-private", "models-private", "checkpoints"} for part in path.parts)):
            raise ValueError("Arquivo de dados/pesos/credenciais não pode integrar o pacote de código: " + str(path))


def build(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if git(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("Checkout contém mudanças versionadas não commitadas.")
    commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree = git(root, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    check_inventory(git(root, "ls-tree", "-rz", commit))
    output.mkdir(parents=True, exist_ok=True)
    name = f"LocalAuthor-source-{commit[:12]}.zip"
    destination = output / name
    manifest = output / (name + ".json")
    if destination.exists() or manifest.exists():
        raise FileExistsError("O pacote desta revisão já existe; não foi sobrescrito.")
    with tempfile.TemporaryDirectory(prefix="localauthor-package-", dir=output) as temp:
        archive = Path(temp) / name
        git(root, "archive", "--format=zip", "--prefix=LocalAuthor/", "--output=" + str(archive), commit)
        checksum = hashlib.sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        result = {"schema": 1, "kind": "source_distribution", "commit_sha": commit,
                  "tree_sha": tree, "archive": name, "sha256": checksum.hexdigest(),
                  "weights_included": False, "models_trained": False,
                  "model_quality_certified": False,
                  "notice": "Git revision archive only. CI status must be checked for this exact commit."}
        # Same-volume publication. CI uses a clean, exclusively owned output directory.
        archive.rename(destination)
        try:
            with manifest.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist/source"))
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output), ensure_ascii=False, indent=2))
