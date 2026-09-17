"""Confirm that deployed chat returns the exact functional code executed in Docker."""
import argparse
import hashlib
import http.client
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--orbit-root', type=Path, required=True)
args = parser.parse_args()
home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
certificate = json.loads((home / 'exports/functional-testing-report.json').read_text(encoding='utf-8'))
folder = Path(certificate['evidenceDirectory'])
for name, expected in certificate['evidenceHashes'].items():
    if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
        raise ValueError('Execution evidence changed')
training = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
token = (home / 'api.token').read_text().strip()


def request(path, body=None):
    connection = http.client.HTTPConnection('127.0.0.1', 8765, timeout=30)
    try:
        connection.request('GET' if body is None else 'POST', path,
                           None if body is None else json.dumps(body).encode(),
                           {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Local API status ' + str(response.status))
        return json.loads(response.read())
    finally:
        connection.close()


project = next(p for p in request('/api/projects') if Path(p['root']).resolve() == args.orbit_root.resolve())
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
conversation = request('/api/conversations', {'project_id': project['id'], 'title': 'Testes funcionais validados ' + stamp[:15]})
result = {'state': 'running', 'conversationId': conversation['id'], 'cases': [], 'passed': 0,
          'executionEvidence': str(folder / 'functional-execution.json'),
          'method': 'Byte equality with unchanged raw outputs previously executed in verified Docker; no second execution.'}
path = folder / ('chat-verification-' + stamp + '.json')
for case in training['after']:
    job = request('/api/chat', {'project_id': project['id'], 'conversation_id': conversation['id'],
                               'message': case['prompt'], 'mode': 'model'})['job']
    deadline = time.monotonic() + 120
    while job['state'] in {'queued', 'running'}:
        if time.monotonic() > deadline:
            request('/api/jobs/' + job['id'] + '/cancel', {})
            raise TimeoutError('Chat generation timed out')
        time.sleep(.5)
        job = request('/api/jobs/' + job['id'])
    if job['state'] != 'completed':
        raise RuntimeError('Generation did not complete')
    message = job['result']['messages'][-1]
    metadata = message['metadata']
    passed = (message['content'] == case['generated'] and metadata.get('origin') == 'local_model'
              and metadata.get('skill') == 'orbit_functional_tests' and not metadata.get('possibly_truncated')
              and metadata.get('model') == str(Path(certificate['selectedCheckpoint']).relative_to(home / 'models')))
    result['cases'].append({'id': case['id'], 'passed': passed, 'generated': message['content'], 'metadata': metadata})
    result['passed'] += int(passed)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'id': case['id'], 'passed': passed}), flush=True)
result.update(state='completed', total=len(result['cases']))
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'passed': result['passed'], 'total': result['total'], 'report': str(path)}))
raise SystemExit(0 if result['passed'] == result['total'] == 36 else 1)
