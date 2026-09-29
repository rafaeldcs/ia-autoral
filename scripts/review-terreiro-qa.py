"""Evaluate the trained scheduler against real executor receipts, fail closed."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'qa')]
from terreiro_qa_policy import TerreiroQaPolicy,FIELDS

p=argparse.ArgumentParser()
p.add_argument('--checkpoint',type=Path,required=True)
p.add_argument('--http',type=Path,required=True)
p.add_argument('--browser',type=Path)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
http=json.loads(args.http.read_text())
browser=json.loads(args.browser.read_text()) if args.browser else None
state={field:False for field in FIELDS}
state['authorized']=http.get('origin')=='http://localhost:3180'
state['sandbox']=state['authorized']  # Caller must launch in the verified Docker sandbox.
state['failure']=not http.get('success',False) or bool(browser and not browser.get('success',False))
# Build/unit attestations are deliberately not inferred from HTTP results.
# This observation asks whether an observed failure overrides every missing stage.
action=TerreiroQaPolicy.load(args.checkpoint).predict(state)
expected='STOP_SCOPE' if not state['authorized'] else 'INVESTIGATE_FAILURE' if state['failure'] else 'CHECK_BUILD'
result={'action':action,'expected':expected,'passed':action==expected,'observations':state,
        'http_checks':len(http.get('checks',[])),'browser_checks':len(browser.get('checks',[])) if browser else 0,
        'limitation':'Bounded next-action classification. Passing is not semantic understanding of the app.'}
args.output.write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ('action','expected','passed')}))
raise SystemExit(0 if result['passed'] else 1)
