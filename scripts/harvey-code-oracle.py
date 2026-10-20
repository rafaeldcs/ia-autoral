"""Independent frozen checks of model-generated code, executed only in Docker."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from localauthor.harvey.runner import run_case
from importlib.util import module_from_spec,spec_from_file_location
loader=spec_from_file_location('harvey_software_fixture',ROOT/'scripts/harvey-smoke.py');fixture=module_from_spec(loader);loader.loader.exec_module(fixture)

CHECK="""python -I - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('generated_billing','/workspace/documents/billing.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
cases=[(1,9),(7,13),(0,12),(3,0),(2,1.25)]
for quantity,price in cases:
 result=module.monthly_total(quantity,price)
 assert type(result) in (int,float) and result==quantity*price,(quantity,price,result)
for quantity in [-1,-10]:
 try:module.monthly_total(quantity,7)
 except ValueError:pass
 else:raise AssertionError('negative quantity accepted')
print('INDEPENDENT_BILLING_CHECKS_COMPLETE:7')
PY"""


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--image',required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();source=args.source.resolve();assert source.name=='billing.py' and source.is_file() and not source.is_symlink()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    engine=fixture.ScriptedEngine();engine.actions=iter([('bash',{'command':CHECK}),('write',{'file_path':'response.md','content':'Independent oracle fixture; inspect execution trace.'}),('finish',{'summary':'independent checks completed','deliverables':['response.md']})])
    task={'title':'Independent code oracle','instructions':'Execute the frozen independent check. This scripted evaluator does not claim to be a model.',
          'deliverables':{'response.md':'response.md'},'criteria':[{'id':'C1','title':'software route','match_criteria':'response.md exists','deliverables':['response.md']}]}
    with tempfile.TemporaryDirectory(prefix='harvey-code-oracle-') as directory:
        run=Path(directory);(run/'documents').mkdir();shutil.copyfile(source,run/'documents/billing.py')
        run_case(task,run,args.image,engine,max_turns=4)
        trace=[json.loads(line) for line in (run/'transcript.jsonl').read_text(encoding='utf-8').splitlines()]
        execution=next(row for row in trace if row['role']=='tool' and row['tool_name']=='bash')['result']
        assert execution.strip()=='INDEPENDENT_BILLING_CHECKS_COMPLETE:7',execution
        report={'success':True,'checks':7,'generated_source_sha256':digest,'independent_assertions':True,'real_docker_execution':True,'model_generated_source':True,'judge_model_used':False}
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
