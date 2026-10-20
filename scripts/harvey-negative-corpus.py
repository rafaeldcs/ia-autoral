"""Run every original rubric through the original scorer with missing outputs.

This is a negative software contract test, never a model-capability score.
Requires the optional upstream library environment (Python 3.12 or 3.13).
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from localauthor.harvey.contracts import REVISION,validate_task
from localauthor.harvey.runner import inventory


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--upstream',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();catalog,_=inventory(args.upstream)
    from lab_core.evaluation import scoring
    def forbidden(*args,**kwargs):raise AssertionError('Cloud client or filename fallback must not run in the missing-output fixture')
    scoring.anthropic.Anthropic=forbidden;scoring._llm_match_deliverables=forbidden
    class NegativeJudge:
        count=0
        def evaluate_from_file(self,prompt_name,variables):
            self.count+=1
            assert prompt_name=='rubric_criterion' and variables['match_criteria']
            return {'verdict':'fail','reasoning':'Explicit missing-output negative software fixture. No model inference.'}
    judge=NegativeJudge();identifiers=[row['git_blob'] for row in catalog['tasks']]
    batch=subprocess.run(['git','-C',str(args.upstream),'cat-file','--batch'],input=('\n'.join(identifiers)+'\n').encode(),capture_output=True,check=True,timeout=120)
    offset=0;results=[];criteria=0
    with tempfile.TemporaryDirectory(prefix='harvey-negative-') as directory:
        run=Path(directory);(run/'output').mkdir()
        for row in catalog['tasks']:
            end=batch.stdout.index(b'\n',offset);size=int(batch.stdout[offset:end].split()[2]);offset=end+1
            task=validate_task(json.loads(batch.stdout[offset:offset+size]));offset+=size+1
            score=scoring.score_rubric(task['criteria'],run,judge,task['title'],parallel=1)
            assert score.score==0 and score.n_grading_errors==0 and len(score.criteria_results)==len(task['criteria']),row['id']
            assert all(item['verdict']=='fail' for item in score.criteria_results),row['id']
            criteria+=len(task['criteria']);results.append({'id':row['id'],'criteria':len(task['criteria']),'expected_failure':True})
    assert len(results)==catalog['total'] and judge.count==criteria
    report={'success':True,'original_tasks':len(results),'original_criteria':criteria,'judge_calls':judge.count,'real_model':False,
            'fixture':'missing deliverables; explicit deterministic failing judge','source_revision':REVISION,'model_qualification':False,'results':results}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='results'}))


if __name__=='__main__':main()
