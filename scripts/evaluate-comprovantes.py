"""Evaluate a saved comprobantes checkpoint without training or output repair.

The evaluator is intended for the reviewed Docker lab. It reads the frozen
reserved cases, reloads the checkpoint by hash/provenance, and records the
model's raw decoded answer. It never changes the active model.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.dataset import validate_dataset
from localauthor.nn.checkpoint import load_checkpoint

p = argparse.ArgumentParser()
p.add_argument('--checkpoint', type=Path, required=True)
p.add_argument('--manifest', type=Path, required=True)
p.add_argument('--cases', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
if not Path('/.dockerenv').is_file():
    raise RuntimeError('Reviewed Docker sandbox required')
for path in (args.checkpoint, args.manifest, args.cases):
    if not path.is_file():
        raise ValueError('Missing evaluation input')
checkpoint_hash = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
dataset = validate_dataset(args.manifest)
model, _, tokenizer, _, metadata = load_checkpoint(args.checkpoint)
if metadata.get('provenance', {}).get('manifest_hash') != dataset['manifest_hash']:
    raise ValueError('Checkpoint and corpus manifest do not match')
cases = json.loads(args.cases.read_text(encoding='utf-8'))
if cases.get('status') != 'frozen_before_training' or not isinstance(cases.get('cases'), list) or len(cases['cases']) < 1:
    raise ValueError('Reserved evaluation set is invalid')
results = []
reserved = [case for case in cases['cases'] if case.get('split') == 'test']
if not reserved:
    raise ValueError('Reserved evaluation set has no test cases')
for case in reserved:
    if set(case) != {'id', 'split', 'group', 'prompt', 'expected'} or case['split'] != 'test':
        raise ValueError('Unexpected evaluation case')
    generated = tokenizer.decode(model.generate([tokenizer.bos_id] + tokenizer.encode(case['prompt']),
                                                max_tokens=96, temperature=.05, seed=31))
    match = re.search(r'(?:^|\n)Proxima_verificacao: ([A-Z_]+)(?:\n|$)', generated)
    label = match.group(1) if match else None
    results.append({'id': case['id'], 'group': case['group'], 'expected': case['expected'],
                    'generated': generated, 'label': label, 'passed': label == case['expected']})
result = {'state': 'evaluated', 'trainingPerformed': False, 'activeModelChanged': False,
          'checkpointHash': checkpoint_hash, 'manifestHash': dataset['manifest_hash'],
          'cases': len(results), 'passed': sum(row['passed'] for row in results),
          'results': results,
          'limits': ['Synthetic reserved exercise', 'Exact protocol label parsing; no fuzzy repair or label lookup',
                     'This domain test does not qualify general programming or site investigation']}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: result[key] for key in ('checkpointHash', 'cases', 'passed', 'activeModelChanged')}))
raise SystemExit(0 if result['passed'] == result['cases'] else 1)
