"""Bounded stdio protocol; internal HTTP has no published port or external network."""
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def audio_context_size(byte_count):
    """Conservative 15.36s window only for <=8s PCM; longer audio keeps 30s."""
    if not 9644 <= byte_count <= 960044: raise ValueError('PCM size outside registered limits')
    return 768 if byte_count <= 44 + 8 * 32000 else 1500


def main():
    fields = dict(x.split(':', 1) for x in Path('/proc/self/status').read_text().splitlines() if ':' in x)
    assert os.getuid() == 10001 and sorted(x.name for x in Path('/sys/class/net').iterdir()) == ['lo']
    assert fields['CapEff'].strip() == '0000000000000000' and fields['NoNewPrivs'].strip() == '1'
    assert fields['Seccomp'].strip() == '2'
    assert any(x.split()[1] == '/' and 'ro' in x.split()[3].split(',') for x in Path('/proc/mounts').read_text().splitlines())
    parser = argparse.ArgumentParser(); parser.add_argument('--sha256', required=True)
    parser.add_argument('--threads',type=int,choices=(4,6),default=4);args = parser.parse_args()
    model = Path('/weights/ggml-small-q5_1.bin')
    with model.open('rb') as stream: assert hashlib.file_digest(stream, 'sha256').hexdigest() == args.sha256
    # Match the old CLI's beam/best-of settings. Do not trade accuracy for speed.
    # Reviewed source defaults no_context=true; -mc 0 also forbids carrying text history.
    server = subprocess.Popen(['/opt/voice/whisper-server', '-m', str(model), '-l', 'pt', '-t', str(args.threads),
        '-bs', '5', '-bo', '5', '-mc', '0', '-nt', '--no-gpu', '--host', '127.0.0.1', '--port', '8080'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 35
        while True:
            assert server.poll() is None and time.monotonic() < deadline
            connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=1)
            try:
                connection.request('GET', '/health'); response = connection.getresponse()
                if response.status == 200 and json.loads(response.read(1024)).get('status') == 'ok': break
            except (OSError, http.client.HTTPException): time.sleep(.05)
            finally: connection.close()
        print(json.dumps({'ready': True, 'protocol': 'persistent-v1', 'offline': True}), flush=True)
        for _ in range(10000):
            raw = sys.stdin.buffer.readline(1281000)
            if not raw: break
            assert len(raw) <= 1280100 and raw.endswith(b'\n') and server.poll() is None
            request = json.loads(raw)
            assert set(request) == {'id', 'audio'} and re.fullmatch('[a-f0-9]{32}', request['id'])
            audio = base64.b64decode(request['audio'], validate=True)
            assert 9644 <= len(audio) <= 960044 and audio[:4] == b'RIFF'
            # Every input sample is covered. Longer utterances retain the full
            # window after the intermediate adaptive candidate lost a final word.
            audio_context = audio_context_size(len(audio))
            boundary = 'LocalAuthorVoiceBoundary'
            payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="input.wav"\r\n'
                       'Content-Type: audio/wav\r\n\r\n').encode() + audio + (
                       f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="audio_ctx"\r\n\r\n'
                       f'{audio_context}\r\n--{boundary}--\r\n').encode()
            connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=90)
            try:
                connection.request('POST', '/inference', body=payload,
                                   headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
                response = connection.getresponse(); result = json.loads(response.read(40001))
                assert response.status == 200 and isinstance(result.get('text'), str) and 0 < len(result['text'].strip()) <= 8000
                print(json.dumps({'id': request['id'], 'text': result['text'].strip(), 'offline': True}, ensure_ascii=False), flush=True)
            finally:
                connection.close()
                del payload, audio, request, raw
    finally:
        server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)


if __name__ == '__main__': main()
