"""Ask local trained weights what to do next, using actual run receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
from terreiro_qa_policy import TerreiroQaPolicy, STAGES
from terreiro_simulation_review import observations, required_action

p = argparse.ArgumentParser()
p.add_argument('--model', type=Path, required=True)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--label', required=True)
args = p.parse_args()
if not args.label.replace('-', '').isalnum():
    raise ValueError('Invalid observation label')
checkpoint = args.model / 'qa-policy.npz'
qualification = json.loads((args.model / 'report.json').read_text())
digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
if (digest != qualification['checkpointHash'] or qualification['heldoutTotal'] < 1
        or qualification['heldoutPassed'] != qualification['heldoutTotal']
        or qualification.get('originalRegressionPassed') != qualification.get('originalRegressionTotal')):
    raise ValueError('Unqualified or altered scheduler')
files = {'sandbox': 'sandbox.json', 'builds': 'builds/builds.json',
         'http': 'simulation/http-report.json', 'followup': 'simulation/followup-report.json',
         'browser': 'simulation/browser-report.json', 'interactions': 'simulation/interaction-report.json'}
receipts, hashes = {}, {}
for kind, relative in files.items():
    path = args.run / relative
    if path.is_file():
        receipts[kind] = json.loads(path.read_text(encoding='utf-8-sig'))
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
state = observations(**receipts)
model = TerreiroQaPolicy.load(checkpoint)
action = model.predict(state)
expected = required_action(state)
result = {'proposer': 'local-neural-qa-policy', 'checkpointHash': digest,
          'action': action, 'reviewExpected': expected, 'accepted': action == expected,
          'observations': state, 'receipts': hashes,
          'limits': ['Tutor-authored tests and evidence adapter', 'Bounded normalized-state classifier',
                     'No new code generation or weight update in this execution']}
directory = args.run / 'decisions'
directory.mkdir(exist_ok=True)
with (directory / (args.label + '.json')).open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
if args.label == 'initial':
    # Legacy worker requires a complete proposed catalog. This is hypothetical,
    # not completion evidence: retain the distinction explicitly in the plan.
    hypothetical = dict(state)
    actions = []
    for _ in range(len(STAGES) + 1):
        proposed = model.predict(hypothetical)
        if proposed != required_action(hypothetical):
            raise ValueError('Unsafe hypothetical plan')
        actions.append(proposed)
        if proposed == 'REPORT':
            break
        if not proposed.startswith('CHECK_'):
            raise ValueError('Cannot plan a blocked run')
        hypothetical[proposed[6:].lower()] = True
    (args.run / 'local-ai-plan.json').write_text(json.dumps({
        'proposer': result['proposer'], 'checkpointHash': digest, 'actions': actions,
        'hypotheticalOnly': True, 'doesNotAttestExecution': True}, indent=2))
print(json.dumps({'action': action, 'accepted': action == expected, 'observations': state}))
raise SystemExit(0 if action == expected else 1)
