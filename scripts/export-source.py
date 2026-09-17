#!/usr/bin/env python3
"""Exporta apenas arquivos versionados. Não inclui dados locais ou chaves."""
import argparse
import subprocess
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("output",type=Path); args=parser.parse_args()
    files=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode().split("\0")
    with zipfile.ZipFile(args.output,"w",zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            if name and (ROOT/name).is_file(): archive.write(ROOT/name,arcname="ia-local-autoral/"+name)
    print(args.output)
