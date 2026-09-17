"""Activate a narrow chat skill only after complete, unchanged execution evidence."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'qa/functional-lab'))
from course import examples
from localauthor.util import write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def certify(folder, home):
    paths = {name: folder / name for name in (
        'report.json', 'frozen-test-cases.json', 'functional-references.json', 'functional-execution.json')}
    evidence = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in paths.items()}
    training = evidence['report.json']
    reference = evidence['functional-references.json']
    execution = evidence['functional-execution.json']
    frozen = evidence['frozen-test-cases.json']
    checkpoint = Path(training['selectedCheckpoint'])
    if checkpoint.is_symlink() or not checkpoint.resolve().is_relative_to((home / 'models').resolve()):
        raise ValueError('Checkpoint outside the local model directory')
    if digest(checkpoint) != training['checkpointHash']:
        raise ValueError('Checkpoint changed since generation')
    if training['state'] != 'awaiting_execution' or frozen != examples([43, 47, 61, 79]):
        raise ValueError('Frozen curriculum mismatch')
    if len(training['after']) != len(frozen):
        raise ValueError('Missing generated cases')
    for original, generated in zip(frozen, training['after']):
        if any(generated.get(key) != value for key, value in original.items()) or generated['generated'] != original['answer']:
            raise ValueError('Generated code differs from approved contract')
    for report, expected in ((reference, examples([17])), (execution, frozen)):
        if report['state'] != 'completed' or report['total'] != report['passed'] or report['total'] != len(expected):
            raise ValueError('Incomplete execution')
        rows = report['cases']
        if len(rows) != len(expected) or {c['id'] for c in rows} != {c['id'] for c in expected}:
            raise ValueError('Missing or duplicated cases')
        by_id = {c['id']: c for c in expected}
        for row in rows:
            if any(row.get(k) != v for k, v in by_id[row['id']].items()) or row['generated'] != row['answer']:
                raise ValueError('Executed source mismatch')
            normal, fault = row['normal'], row['fault']
            if not (row['accepted'] and row['passed'] and row['correctApplicationPassed'] and row['controlledFaultDetected']
                    and normal.get('exit') == 0 and normal.get('stats', {}).get('expected') == 1
                    and normal.get('stats', {}).get('skipped') == 0
                    and fault.get('exit', 0) != 0 and fault.get('stats', {}).get('unexpected') == 1
                    and fault.get('assertionFailure') is True):
                raise ValueError('False positive or incomplete test evidence')
    if reference['sandbox'] != execution['sandbox']:
        raise ValueError('Sandbox/image differs between references and generated tests')
    return {
        'state': 'evaluated', 'chatEnabled': True, 'scope': 'orbit-functional-lab',
        'selectedCheckpoint': str(checkpoint), 'checkpointHash': digest(checkpoint),
        'functionalTests': {'total': 36, 'passed': 36, 'faultsDetected': 36},
        'sandbox': execution['sandbox'], 'evidenceDirectory': str(folder),
        'evidenceHashes': {name: digest(path) for name, path in paths.items()},
        'programmingQualified': False,
        'limitations': training['limitations'],
        'oldSkillRegression': {'total': len(training['regression']), 'exact': sum(c['exact'] for c in training['regression'])},
        'routing': 'Only Teste JS h: prompts; existing model retained for other prompts.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    certificate = certify(args.report.resolve().parent, home)
    target = home / 'exports/functional-testing-report.json'
    if target.exists():
        raise ValueError('A functional skill is already active; preserve and review its evidence before replacement')
    write_json(target, certificate)
    print(json.dumps({'certificate': str(target), 'tests': certificate['functionalTests']}))
