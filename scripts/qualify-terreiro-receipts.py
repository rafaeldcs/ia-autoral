"""Challenge local QA weights with controlled changes to real synthetic receipts.

This is an evaluation, not new training or a claim of arbitrary-site understanding.
Never modify the original receipts or the product database.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
from terreiro_qa_policy import TerreiroQaPolicy
from terreiro_simulation_review import observations

p = argparse.ArgumentParser()
p.add_argument('--model', type=Path, required=True)
p.add_argument('--run', type=Path, required=True)
args = p.parse_args()
paths = dict(sandbox='sandbox.json', builds='builds/builds.json', http='simulation/http-report.json',
             followup='simulation/followup-report.json', browser='simulation/browser-report.json',
             interactions='simulation/interaction-report.json')
original = {key: json.loads((args.run / path).read_text(encoding='utf-8-sig')) for key, path in paths.items()}
digest = hashlib.sha256((args.model / 'qa-policy.npz').read_bytes()).hexdigest()
certificate = json.loads((args.model / 'report.json').read_text())
if (digest != certificate['checkpointHash'] or certificate['heldoutPassed'] != certificate['heldoutTotal']
        or certificate['heldoutTotal'] < 1
        or certificate.get('originalRegressionPassed') != certificate.get('originalRegressionTotal')):
    raise ValueError('Model qualification mismatch')
model = TerreiroQaPolicy.load(args.model / 'qa-policy.npz')
cases = []


def check(name, expected, mutate=lambda receipts: None):
    receipts = deepcopy(original)
    mutate(receipts)
    state = observations(**receipts)
    proposed = model.predict(state)
    cases.append(dict(name=name, expected=expected, proposed=proposed,
                      passed=proposed == expected, observations=state))


check('Actual completed simulation', 'REPORT')
check('Follow-up omitted', 'CHECK_EVIDENCE', lambda r: r.pop('followup'))
check('Browser omitted', 'CHECK_BROWSER', lambda r: r.pop('browser'))
check('Interactions omitted', 'CHECK_BROWSER', lambda r: r.pop('interactions'))
check('HTTP failure overrides success flag', 'INVESTIGATE_FAILURE', lambda r: r['http']['checks'][0].update(passed=False))
check('Empty HTTP report cannot pass', 'INVESTIGATE_FAILURE', lambda r: r['http'].update(checks=[]))
check('Build command failed', 'INVESTIGATE_FAILURE', lambda r: r['builds']['results'][0].update(exitCode=1, passed=False))
check('Missing build completion', 'CHECK_BUILD', lambda r: r['builds'].update(complete=False))
check('Unit suite omitted', 'CHECK_BUILD', lambda r: r['builds'].update(results=[c for c in r['builds']['results'] if c['name'] != 'dotnet-test']))
check('Treasury receipts omitted', 'CHECK_TREASURY', lambda r: r['http'].update(checks=[c for c in r['http']['checks'] if c['stage'] != 'treasury']))
check('Unapproved environment', 'STOP_SCOPE', lambda r: r['sandbox'].update(origin='https://production.invalid'))
check('Unverified sandbox', 'STOP_SCOPE', lambda r: r['sandbox'].update(verified=False))
result = dict(checkpointHash=digest, weightUpdate=False, source='Counterfactual copies of this synthetic run',
              passed=sum(c['passed'] for c in cases), total=len(cases), cases=cases)
with (args.run / 'receipt-challenges.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({k: result[k] for k in ('passed', 'total', 'weightUpdate')}))
raise SystemExit(0 if result['passed'] == result['total'] else 1)
