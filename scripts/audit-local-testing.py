"""Recheck original model tests and the running chat without training or repairs.

Requires the existing Orbit lab and verified Docker isolation. Private answers and
reports stay outside Git. Repeated cases are regression, never a fresh benchmark.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orbit-root', type=Path, required=True)
    parser.add_argument('--scope', choices=['historical', 'chat'], required=True)
    args = parser.parse_args()
    orbit = args.orbit_root.resolve(strict=True)
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    report_path = home / 'exports/jira-experimental/generalization-report.json'
    historical = json.loads(report_path.read_text(encoding='utf-8'))
    export = Path(historical['exportDirectory'])
    cases_path = export / 'cases.json'
    cases = json.loads(cases_path.read_text(encoding='utf-8'))
    references = json.loads((export / 'references.json').read_text(encoding='utf-8'))
    if digest(cases_path) != historical['evaluation']['casesHash']:
        raise ValueError('Frozen cases changed')
    if digest(Path(historical['selectedCheckpoint'])) != historical['checkpointHash']:
        raise ValueError('Historical model changed')
    if [{k: v for k, v in c.items() if k not in {'generated', 'exact'}}
            for c in historical['after']] != cases:
        raise ValueError('Original outputs do not match frozen cases')
    sys.path.insert(0, str(orbit / 'scripts'))
    from code_sandbox import Sandbox
    sandbox = Sandbox()
    verification = sandbox.verify()
    if not (references['total'] == references['passed'] == len(cases)
            and references['casesHash'] == digest(cases_path)
            and references['sandbox']['image'] == verification['image']):
        raise ValueError('No approved references for exact cases and immutable image')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = home / 'exports/jira-experimental' / ('testing-audit-' + args.scope + '-' + stamp)
    output.mkdir()
    report = {
        'at': stamp, 'scope': args.scope, 'state': 'running',
        'historicalReportHash': digest(report_path), 'casesHash': digest(cases_path),
        'historicalCheckpointHash': historical['checkpointHash'],
        'sandbox': verification, 'trainingPerformed': False,
        'modelSelectionChanged': False, 'generatedCodeRepaired': False,
        'evaluationType': 'regression of previously seen cases',
        'runnerAuthor': 'Codex', 'testCodeAuthor': 'local model',
        'applicationUnderTest': 'isolated teaching fixtures, not Orbit',
        'allRequiredSystemFlowsTested': False,
        'cases': [], 'newChallenges': [],
    }
    write(output / 'report.json', report)
    print(json.dumps({'report': str(output / 'report.json'), 'sandboxVerified': True}), flush=True)

    token = (home / 'api.token').read_text().strip() if args.scope == 'chat' else None

    def request(path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', 8765, timeout=30)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               None if body is None else json.dumps(body).encode('utf-8'),
                               {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            data = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError(f'Local API status {response.status}')
            return data
        finally:
            connection.close()

    if args.scope == 'chat':
        project = next(p for p in request('/api/projects') if Path(p['root']).resolve() == orbit)
        conversation = request('/api/conversations', {
            'project_id': project['id'], 'title': 'Auditoria: testes gerados pela IA ' + stamp[:15]})
        report['conversationId'] = conversation['id']

    def generate(prompt):
        job = request('/api/chat', {'project_id': project['id'],
                      'conversation_id': conversation['id'], 'message': prompt, 'mode': 'model'})['job']
        deadline = time.monotonic() + 120
        while job['state'] in {'queued', 'running'}:
            if time.monotonic() >= deadline:
                request('/api/jobs/' + job['id'] + '/cancel', {})
                raise TimeoutError('Generation timed out; cancellation requested')
            time.sleep(.5)
            job = request('/api/jobs/' + job['id'])
        if job['state'] != 'completed':
            return {'generated': '', 'jobState': job['state'], 'generationFailed': True}
        message = job['result']['messages'][-1]
        if message['role'] != 'assistant' or message['metadata']['origin'] != 'local_model':
            raise ValueError('Response was not generated by the local model')
        return {'generated': message['content'], 'metadata': message['metadata'], 'jobState': job['state']}

    def evaluate(case):
        result = {**case, **sandbox.evaluate(case, case['generated'])}
        write(output / (case['id'] + '.json'), result)
        return result

    if args.scope == 'historical':
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(evaluate, case) for case in historical['after']]
            for future in as_completed(futures):
                result = future.result()
                report['cases'].append(result)
                write(output / 'report.json', report)
                print(json.dumps({'case': result['id'], 'passed': result['passed']}), flush=True)
    else:
        for case in cases:
            result = evaluate({**case, **generate(case['prompt'])})
            report['cases'].append(result)
            write(output / 'report.json', report)
            print(json.dumps({'case': result['id'], 'passed': result['passed'],
                              'accepted': result['accepted'], 'metadata': result.get('metadata')}), flush=True)
        # Outputs below need review: no reference implementation exists for these
        # full workflows. Never execute them on the host or auto-label them passed.
        challenges = [
            ('password', 'xUnit: senha valida tem 12 a 256 caracteres. Teste ValidPassword com 11, 12, 256 e 257 letras. Gere metodo Fact.'),
            ('workflow', 'Playwright: teste login, criar projeto, criar tarefa, concluir tarefa e recarregar para conferir persistencia. Gere teste.'),
            ('permissions', 'xUnit HTTP: leitor tenta criar sprint e recebe 403; gestor cria sprint e recebe 201. Gere teste com ambos os usuarios.'),
            ('wip', 'xUnit: Kanban com limite 2 e 1 item ativo. Duas criacoes simultaneas: uma aceita e outra rejeitada. Gere teste.')
        ]
        for name, prompt in challenges:
            result = {'id': name, 'prompt': prompt, **generate(prompt),
                      'executed': False, 'reviewRequired': True}
            report['newChallenges'].append(result)
            write(output / 'report.json', report)
            print(json.dumps({'challenge': name, 'response': result['generated']}, ensure_ascii=True), flush=True)
    report.update(state='completed', total=len(report['cases']),
                  passed=sum(c['passed'] for c in report['cases']),
                  accepted=sum(c['accepted'] for c in report['cases']),
                  correctImplementationPassed=sum(c.get('referencePass', False) for c in report['cases']),
                  controlledDefectsDetected=sum(c.get('mutantKilled', False) for c in report['cases']))
    write(output / 'report.json', report)
    print(json.dumps({k: report[k] for k in ('state', 'total', 'passed', 'accepted',
                                           'correctImplementationPassed', 'controlledDefectsDetected')}), flush=True)
    # Completion means the audit ran, not that the candidate passed.


if __name__ == '__main__':
    main()
