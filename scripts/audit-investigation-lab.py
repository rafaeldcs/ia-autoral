"""Independently reload saved weights and audit without training or repairs."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from localauthor.investigation_policy import InvestigationPolicy, FIELDS, ACTIONS
from localauthor.dataset import validate_dataset
from localauthor.nn.checkpoint import load_checkpoint
from localauthor.util import write_json
from investigation_lab import journeys, run_journey


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    source = args.report.resolve(strict=True)
    if not source.is_relative_to((home / 'exports').resolve()):
        raise ValueError('Report must be in local private exports.')
    report = json.loads(source.read_text(encoding='utf-8'))
    checkpoint = Path(report['selectedCheckpoint']).resolve(strict=True)
    if not checkpoint.is_relative_to((home / 'models').resolve()) or digest(checkpoint) != report['checkpointHash']:
        raise ValueError('Saved weights do not match evaluated candidate.')
    corpus = home / 'corpus' / source.parent.name
    dataset = validate_dataset(corpus / 'manifest.json')
    if dataset['manifest_hash'] != report['manifestHash']:
        raise ValueError('Dataset changed after evaluation.')
    # Read frozen targets directly from hash-verified test files, not teacher().
    test = []
    for item in dataset['splits']['test']:
        fingerprint, action = (corpus / item['path']).read_text(encoding='utf-8').splitlines()
        if len(fingerprint) != len(FIELDS) or set(fingerprint) - {'0', '1'} or action not in ACTIONS:
            raise ValueError('Invalid frozen test.')
        test.append((fingerprint, dict(zip(FIELDS, (v == '1' for v in fingerprint))), action))
    if len(test) != report['counts']['test'] or len(test) < 192:
        raise ValueError('Incomplete test set cannot pass the gate.')
    if any(sum(row[2] == action for row in test) < 16 for action in ACTIONS):
        raise ValueError('Every investigation point must have its complete audit cases.')
    policy = InvestigationPolicy.load(checkpoint)
    decisions, durations = [], []
    for fingerprint, observation, expected in test:
        started = time.perf_counter()
        actual = policy.predict(observation)
        durations.append((time.perf_counter() - started) * 1000)
        decisions.append({'id': fingerprint, 'expected': expected, 'generated': actual, 'passed': actual == expected})
    episodes = [run_journey(policy, definition) for definition in journeys(novel=True)]
    original = Path(report['originalCheckpoint']).resolve(strict=True)
    if not original.is_relative_to((home / 'models').resolve()) or digest(original) != report['originalHashBefore']:
        raise ValueError('Original model changed.')
    previous = json.loads((home / 'exports/engineering-report.json').read_text(encoding='utf-8'))
    if Path(previous['selectedCheckpoint']).resolve() != original or previous['checkpointHash'] != digest(original):
        raise ValueError('Original model certification mismatch.')
    if len(previous['evaluation']['cases']) != 32:
        raise ValueError('Incomplete engineering regression cannot pass.')
    model, _, tokenizer, _, _ = load_checkpoint(original)
    regression = []
    for case in previous['evaluation']['cases']:
        tokens = model.generate([tokenizer.bos_id] + tokenizer.encode(case['prompt']), max_tokens=64, temperature=.05, seed=31)
        actual = tokenizer.decode(tokens)
        regression.append({'id': case['id'], 'passed': actual == case['answer'], 'generated': actual})
    result = {'state': 'audited', 'trainingPerformed': False, 'checkpointHash': digest(checkpoint),
              'decisions': decisions, 'journeys': episodes, 'engineeringRegression': regression,
              'perPoint': {a: {'passed': sum(d['passed'] for d in decisions if d['expected'] == a),
                               'total': sum(d['expected'] == a for d in decisions)} for a in ACTIONS},
              'inferenceMs': {'p50': float(np.percentile(durations, 50)), 'p95': float(np.percentile(durations, 95))},
              'realSiteAutonomy': False, 'freeTextInvestigationQualified': False,
              'scope': 'learned specialist on code-normalized observations; stateful synthetic lab'}
    result['labApproved'] = all(d['passed'] for d in decisions) and all(j['passed'] for j in episodes) and all(r['passed'] for r in regression)
    write_json(source.parent / 'independent-audit.json', result)
    print(json.dumps({'decisions': [sum(d['passed'] for d in decisions), len(decisions)],
                      'journeys': [sum(j['passed'] for j in episodes), len(episodes)],
                      'engineeringRegression': [sum(r['passed'] for r in regression), len(regression)],
                      'labApproved': result['labApproved'], 'inferenceMs': result['inferenceMs']}))
    if not result['labApproved']: raise SystemExit(1)


if __name__ == '__main__':
    main()
