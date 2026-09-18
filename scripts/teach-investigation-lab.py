"""Train an isolated neural decision specialist, then grade frozen lab journeys."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from localauthor.investigation_policy import InvestigationPolicy, ACTIONS, FIELDS, vector
from localauthor.nn.tensor import cross_entropy, no_grad
from localauthor.nn.optimizer import AdamW
from localauthor.dataset import validate_dataset
from localauthor.util import write_json
from investigation_lab import make_splits, corrective_splits, journeys, run_journey


def grade(policy, rows):
    return [{'id': row['id'], 'expected': row['action'],
             'generated': (proposal := policy.predict(row['state'])),
             'passed': proposal == row['action']} for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=4000)
    parser.add_argument('--corrective', action='store_true', help='Teach sparse priority contrasts; preserves old test and freezes new audit cases.')
    args = parser.parse_args()
    if not 500 <= args.steps <= 12000 or args.steps % 500:
        raise ValueError('Steps must be a multiple of 500 between 500 and 12000.')
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    name = 'investigation-lab-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out, corpus, export = [home / folder / name for folder in ('models', 'corpus', 'exports')]
    for folder in (out, corpus, export): folder.mkdir(parents=True)
    splits, fresh_ids = corrective_splits() if args.corrective else (make_splits(), set())
    records = []
    for split, rows in splits.items():
        for row in rows:
            path = corpus / split / (row['id'] + '.txt')
            path.parent.mkdir(exist_ok=True)
            path.write_text(row['id'] + '\n' + row['action'], encoding='utf-8')
            records.append({'path': path.relative_to(corpus).as_posix(), 'split': split,
                'group': row['id'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'training_allowed': split != 'test', 'provenance': {
                    'kind': 'synthetic-authorized', 'owner': 'Rafael; original lab authored by Codex',
                    'license_or_permission': 'User requested teaching and evaluating investigation. Synthetic state only; no site or credential data.'}})
    manifest = corpus / 'manifest.json'
    write_json(manifest, {'schema_version': 1, 'dataset_id': name, 'records': records})
    validated = validate_dataset(manifest)
    write_json(export / 'frozen-test.json', splits['test'])
    policy = InvestigationPolicy()
    baseline = grade(policy, splits['test'])
    previous = json.loads((home / 'exports/engineering-report.json').read_text(encoding='utf-8'))
    original = Path(previous['selectedCheckpoint'])
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    report = {'state': 'training', 'architecture': 'own 18-64-12 MLP over boolean observations',
              'module': 'investigation_specialist', 'textTransformerTrained': False,
              'weightsUpdated': False, 'activated': False, 'autonomousBrowserQualified': False,
              'originalCheckpoint': str(original), 'originalHashBefore': original_hash,
              'selectedCheckpoint': str(out / 'best-validation.npz'),
              'manifestHash': validated['manifest_hash'], 'counts': {s: len(r) for s, r in splits.items()},
              'before': baseline, 'history': [], 'fields': FIELDS, 'actions': ACTIONS,
              'correctiveCourse': args.corrective, 'freshAuditIds': sorted(fresh_ids),
              'limitations': ['Normalized flags provided by code, not perception of arbitrary DOM.',
                'Teacher rules provide training labels only; inference uses neural weights.',
                'State tracking, secret filtering and execution guards are deterministic.',
                'Passing synthetic lab does not qualify real-site autonomous use.',
                'Previous free-text investigation benchmark remains failed and is not replaced by this result.']}
    write_json(export / 'report.json', report)
    print(json.dumps({'report': str(export / 'report.json'), 'counts': report['counts']}), flush=True)
    x = np.stack([vector(r['state']) for r in splits['train']])
    y = np.array([ACTIONS.index(r['action']) for r in splits['train']])
    rng = np.random.default_rng(22926)
    optimizer = AdamW(policy.parameters, lr=.003, weight_decay=.0001)
    best = (-1, float('-inf'))
    validation_x = np.stack([vector(r['state']) for r in splits['validation']])
    validation_y = np.array([ACTIONS.index(r['action']) for r in splits['validation']])
    started = time.monotonic()
    for step in range(1, args.steps + 1):
        indexes = rng.integers(0, len(x), 128)
        loss = cross_entropy(policy.forward(x[indexes]), y[indexes])
        loss.backward(); optimizer.step()
        if step % 500 == 0:
            validation = grade(policy, splits['validation'])
            score = sum(r['passed'] for r in validation)
            with no_grad():
                validation_loss = float(cross_entropy(policy.forward(validation_x), validation_y).data)
            # Original journeys become regression/development after the first
            # failure. Fresh composed journeys remain sealed until evaluation.
            development = [run_journey(policy, d) for d in journeys()] if args.corrective else []
            selection_score = (score + sum(r['passed'] for r in development), -validation_loss)
            if selection_score > best:
                best = selection_score; report['selectedStep'] = step
                report['selectedValidationPassed'] = score
                policy.save(out / 'best-validation.npz')
            row = {'step': step, 'passed': score, 'total': len(validation), 'loss': float(loss.data),
                   'validationLoss': validation_loss,
                   'developmentJourneys': sum(r['passed'] for r in development)}
            report['history'].append(row)
            write_json(export / 'report.json', report)
            print(json.dumps(row), flush=True)
    policy = InvestigationPolicy.load(out / 'best-validation.npz')
    after = grade(policy, splits['test'])
    episodes = [run_journey(policy, definition) for definition in journeys(novel=args.corrective)]
    report.update(state='evaluated', weightsUpdated=True, after=after, journeys=episodes,
                  originalHashAfter=hashlib.sha256(original.read_bytes()).hexdigest(),
                  checkpointHash=hashlib.sha256((out / 'best-validation.npz').read_bytes()).hexdigest(),
                  elapsedSeconds=time.monotonic() - started,
                  trainingFit=grade(policy, splits['train']))
    report['gate'] = {'validation': report['selectedValidationPassed'] == len(splits['validation']),
                      'heldout': all(r['passed'] for r in after),
                      'journeys': all(r['passed'] for r in episodes),
                      'originalUnchanged': report['originalHashAfter'] == original_hash}
    report['labApproved'] = all(report['gate'].values())
    report['freshAuditPassed'] = sum(r['passed'] for r in after if r['id'] in fresh_ids)
    write_json(export / 'report.json', report)
    print(json.dumps({'report': str(export / 'report.json'), 'gate': report['gate'],
                      'heldoutPassed': sum(r['passed'] for r in after), 'heldoutTotal': len(after),
                      'journeysPassed': sum(r['passed'] for r in episodes), 'journeysTotal': len(episodes),
                      'labApproved': report['labApproved'], 'realSiteQualified': False}), flush=True)
    if not report['labApproved']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
