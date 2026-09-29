"""Teach and evaluate a bounded local QA scheduler on synthetic demonstrations.

Run inside the verified laboratory container. Output stays outside source control.
The scheduler selects checks from an authored catalog; it does not write those tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from localauthor.nn.tensor import cross_entropy
from localauthor.nn.optimizer import AdamW
from terreiro_qa_policy import TerreiroQaPolicy, FIELDS, ACTIONS, STAGES, curriculum, reinforcement_curriculum

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--reinforce-receipts', type=Path, help='Reserve previously observed receipt challenges; train a fresh synthetic reinforcement course')
args = parser.parse_args()
out = args.output.resolve()
if out.is_relative_to(ROOT):
    raise ValueError('Keep weights, synthetic corpus and reports outside Git')
out.mkdir(parents=True, exist_ok=True)
legacy = curriculum()
reserved = set()
if args.reinforce_receipts:
    challenges = json.loads(args.reinforce_receipts.read_text())
    reserved = {''.join(str(int(c['observations'][k])) for k in FIELDS) for c in challenges['cases']}
    reserved.update(r['id'] for r in legacy['validation'] + legacy['test'])
    splits = reinforcement_curriculum(reserved)
else:
    splits = legacy
raw = json.dumps(splits, sort_keys=True).encode()
(out / 'synthetic-curriculum.json').write_bytes(raw)
model = TerreiroQaPolicy()
def grade(rows):
    return [{'id': r['id'], 'expected': r['action'], 'predicted': model.predict(r['state'])} for r in rows]
baseline = grade(splits['test'])
x = np.array([[float(r['state'][k]) for k in FIELDS] for r in splits['train']])
y = np.array([ACTIONS.index(r['action']) for r in splits['train']])
optimizer = AdamW(model.parameters, lr=.003, weight_decay=.01, clip_norm=1.0)
rng = np.random.default_rng(29)
best = -1
for step in range(1, (10001 if args.reinforce_receipts else 5001)):
    ids = rng.integers(len(x), size=128)
    loss = cross_entropy(model.forward(x[ids]), y[ids])
    loss.backward()
    optimizer.step()
    if step % 500 == 0:
        rows = grade(splits['validation'])
        passed = sum(r['expected'] == r['predicted'] for r in rows)
        if passed > best:
            best = passed
            model.save(out / 'qa-policy.npz')
        print(json.dumps({'step': step, 'validationPassed': passed, 'total': len(rows)}), flush=True)
model = TerreiroQaPolicy.load(out / 'qa-policy.npz')
final = grade(splits['test'])
# A planned sequence is not evidence that any product test ran.
state = dict.fromkeys(FIELDS, False)
state.update(authorized=True, sandbox=True, build=True, unit=True)
plan = []
for _ in range(len(STAGES) + 1):
    proposed = model.predict(state)
    plan.append(proposed)
    if proposed == 'REPORT':
        break
    if not proposed.startswith('CHECK_') or state.get(proposed[6:].lower(), True):
        raise ValueError('Invalid or repeated model proposal')
    state[proposed[6:].lower()] = True
report = {'state': 'evaluated', 'weightsUpdated': True, 'module': 'terreiro_qa_scheduler',
          'corpusHash': hashlib.sha256(raw).hexdigest(),
          'checkpointHash': hashlib.sha256((out / 'qa-policy.npz').read_bytes()).hexdigest(),
          'baselinePassed': sum(r['expected'] == r['predicted'] for r in baseline),
          'heldoutPassed': sum(r['expected'] == r['predicted'] for r in final), 'heldoutTotal': len(final),
          'validationPassed': best, 'test': final, 'proposedPlan': plan,
          'limits': ['Synthetic normalized observations, not arbitrary site comprehension',
                     'Test code and business assertions authored by Codex',
                     'Plan is not execution; real receipts are assessed separately',
                     'Existing language model checkpoints were not replaced']}
if args.reinforce_receipts:
    regression = grade(legacy['test'])
    report.update(course='priority-reinforcement-v2', reservedStateCount=len(reserved),
                  originalRegressionPassed=sum(r['expected'] == r['predicted'] for r in regression),
                  originalRegressionTotal=len(regression), originalRegression=regression,
                  receiptChallenges='Observed previously, excluded from training; retrospective retest is not a new holdout')
(out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(out / 'plan.json').write_text(json.dumps({'proposer': 'local-neural-qa-policy', 'checkpointHash': report['checkpointHash'], 'actions': plan}), encoding='utf-8')
print(json.dumps({k: report[k] for k in ('baselinePassed', 'heldoutPassed', 'heldoutTotal', 'proposedPlan')}))
if report['heldoutPassed'] != report['heldoutTotal'] or report.get('originalRegressionPassed') != report.get('originalRegressionTotal'):
    raise SystemExit(1)
