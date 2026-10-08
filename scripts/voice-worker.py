"""Single offline speech request inside the checksum-bound Docker image."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    fields = dict(x.split(':', 1) for x in Path('/proc/self/status').read_text().splitlines() if ':' in x)
    assert os.getuid() == 10001 and sorted(x.name for x in Path('/sys/class/net').iterdir()) == ['lo']
    assert fields['CapEff'].strip() == '0000000000000000' and fields['NoNewPrivs'].strip() == '1'
    assert fields['Seccomp'].strip() == '2'
    assert any(x.split()[1] == '/' and 'ro' in x.split()[3].split(',') for x in Path('/proc/mounts').read_text().splitlines())
    parser = argparse.ArgumentParser(); parser.add_argument('--sha256', required=True); args = parser.parse_args()
    model = Path('/weights/ggml-small-q5_1.bin')
    digest = hashlib.sha256()
    with model.open('rb') as stream:
        while block := stream.read(1024 * 1024): digest.update(block)
    assert digest.hexdigest() == args.sha256
    raw = sys.stdin.buffer.readline(1281000)
    assert len(raw) <= 1280100 and raw.endswith(b'\n')
    data = json.loads(raw); assert set(data) == {'audio'}
    audio = base64.b64decode(data['audio'], validate=True)
    assert 9644 <= len(audio) <= 960044
    Path('/tmp/input.wav').write_bytes(audio)
    result = subprocess.run(['/opt/voice/whisper-cli', '-m', str(model), '-f', '/tmp/input.wav', '-l', 'pt',
                             '-t', '4', '-nt', '-np', '-oj', '-of', '/tmp/result', '--no-gpu'],
                            capture_output=True, timeout=90)
    assert result.returncode == 0
    value = json.loads(Path('/tmp/result.json').read_text())
    text = ' '.join(x['text'].strip() for x in value['transcription']).strip()
    assert len(text) <= 8000
    sys.stdout.write(json.dumps({'text': text, 'offline': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
