"""Validate references first, then execute unmodified candidate functional tests."""
import argparse,json,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from functional_sandbox import FunctionalSandbox
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'qa/functional-lab'))
from course import examples
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--references',action='store_true')
args=parser.parse_args()
report=json.loads(args.report.read_text(encoding='utf-8'))
out=args.report.parent
sandbox=FunctionalSandbox();verification=sandbox.verify()
if args.references:
    cases=[{**c,'generated':c['answer']} for c in examples([17])]
else:
    reference=json.loads((out/'functional-references.json').read_text(encoding='utf-8'))
    if reference['passed']!=9 or reference['sandbox']['image']!=verification['image']:raise ValueError('References not approved on same image')
    if report['state']!='awaiting_execution':raise ValueError('Candidate not frozen')
    frozen=json.loads((out/'frozen-test-cases.json').read_text(encoding='utf-8'))
    if [{k:v for k,v in c.items() if k not in {'generated','exact'}} for c in report['after']]!=frozen:raise ValueError('Case mismatch')
    cases=report['after']
summary={'state':'running','sandbox':verification,'author':'Codex reference' if args.references else 'Local model raw output','total':len(cases),'passed':0,'cases':[]}
path=out/('functional-references.json' if args.references else 'functional-execution.json')
with ThreadPoolExecutor(max_workers=2) as pool:
    futures={pool.submit(sandbox.evaluate,c,c['generated']):c for c in cases}
    for future in as_completed(futures):
        case=futures[future];result={**case,**future.result()}
        summary['cases'].append(result);summary['passed']+=int(result['passed'])
        path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'id':case['id'],'passed':result['passed'],'reason':result.get('reason'),'normal':result.get('normal',{}).get('infrastructureError')}),flush=True)
summary['state']='completed';path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':summary['passed'],'total':len(cases),'report':str(path)}),flush=True)
if summary['passed']!=len(cases):raise SystemExit(1)
