"""Generate a private relay environment file without printing credentials."""
import argparse
import os
from pathlib import Path
import secrets
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
queue_id = uuid.uuid4().hex
data = (f'LOCALAUTHOR_RELAY_QUEUE_ID={queue_id}\n'
        f'LOCALAUTHOR_RELAY_WRITE_KEY={secrets.token_hex(32)}\n'
        f'LOCALAUTHOR_RELAY_READ_KEY={secrets.token_hex(32)}\n')
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:stream.write(data)
print('Ambiente privado criado. Fila: ' + queue_id)
print('Use as chaves apenas na configuração do backend e no formulário protegido da LocalAuthor; não as envie no chat.')
