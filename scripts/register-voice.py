"""Operator installation of already acquired local weights. Never downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.foundation.models import local_path, write_new
from localauthor.voice import validate_manifest

MODEL_SHA = 'ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb'
REVISION = '5359861c739e955e79d9a303bcbc70fb988958b1'


def docker(args):
    result = subprocess.run(['docker', *args], capture_output=True, timeout=60, check=True)
    return result.stdout.decode('utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--accept-mit-license', action='store_true', required=True)
    args = parser.parse_args()
    target = local_path(args.home / 'voice/model.json')
    if target.exists(): raise RuntimeError('Registro existente; preserve e revise antes de substituir.')
    if not re.fullmatch('sha256:[a-f0-9]{64}', args.image_id): raise RuntimeError('Imagem deve ser identificada por hash.')
    model = local_path(args.model)
    if model.name != 'ggml-small-q5_1.bin' or model.stat().st_size != 190085487:
        raise RuntimeError('Arquivo de modelo inesperado.')
    digest = hashlib.sha256()
    with model.open('rb') as stream:
        while block := stream.read(1024 * 1024): digest.update(block)
    if digest.hexdigest() != MODEL_SHA: raise RuntimeError('Hash do modelo diverge da revisão adquirida.')
    image = json.loads(docker(['image', 'inspect', args.image_id]))[0]
    if image['Id'] != args.image_id or image['Config']['User'] != '10001:10001': raise RuntimeError('Imagem local incompatível.')
    volume = 'localauthor-voice-' + uuid.uuid4().hex
    ident = None
    try:
        docker(['volume', 'create', '--label', 'localauthor.capability=voice', volume])
        ident = docker(['create', '--pull', 'never', '--network', 'none', '--read-only', '--entrypoint', 'sh',
                        '--mount', f'type=volume,src={volume},dst=/weights', args.image_id, '-c', 'true'])
        if not re.fullmatch('[a-f0-9]{64}', ident): raise RuntimeError('Identidade de instalação inválida.')
        docker(['cp', str(model), ident + ':/weights/ggml-small-q5_1.bin'])
        spec = validate_manifest({'schema': 1, 'model': 'whisper-small-q5_1', 'source': 'https://huggingface.co/ggerganov/whisper.cpp',
                                  'revision': REVISION, 'license': 'MIT', 'license_accepted': args.accept_mit_license,
                                  'sha256': MODEL_SHA, 'image_id': args.image_id, 'volume': volume})
        target.parent.mkdir(parents=True, exist_ok=True)
        write_new(target, spec)
        print('Voz registrada; áudio não é armazenado; nenhum download ou treinamento executado.')
    finally:
        if ident: docker(['rm', ident])
        # Preserve any acquired volume after failure for inspection; never overwrite others.


if __name__ == '__main__': main()
