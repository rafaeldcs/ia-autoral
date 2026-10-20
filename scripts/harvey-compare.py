"""Original Harvey comparison dashboards for completed development runs.

Requires the optional lab-core plotting environment. These are development
comparisons with a local, non-independent judge, not qualification scores.
"""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runs',nargs='+',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    manifests=[]
    for index,source in enumerate(args.runs):
        state=json.loads((source/'state.json').read_text(encoding='utf-8'));manifests.append({'source':str(source),'frozen':state['frozen']})
        for row in state['cases']:
            if row['status'] in {'pending','running','interrupted'}:raise ValueError('Comparisons require completed batches, including their failures')
            task='development/'+row['id'];run_id=task+'/adapter-'+str(index+1)+'/run-001'
            directory=args.output/'results'/run_id;directory.mkdir(parents=True)
            result_path=source/row['attempt']/'result.json'
            if result_path.exists():
                result=json.loads(result_path.read_text(encoding='utf-8'));scores=result['scores'];metrics=result['metrics']
            else:
                scores={'score':0,'max_score':1,'criteria_results':[{'id':'EXECUTION_ERROR','title':'Execution failed','verdict':'error','reasoning':row.get('error','No completed result')}]};metrics={}
            scores={**scores,'run_id':run_id,'task':task,'cost':{'wall_clock_seconds':metrics.get('wall_clock_seconds',0)}}
            (directory/'scores.json').write_text(json.dumps(scores),encoding='utf-8')
            (directory/'config.json').write_text(json.dumps({'model':'local-adapter-'+str(index+1),'reasoning_effort':None}),encoding='utf-8')
    os.environ['LAB_ROOT']=str(args.output.resolve())
    from lab_core.evaluation import compare
    for index in range(len(args.runs)):
        compare.MODEL_INFO['local-adapter-'+str(index+1)]=('LocalAuthor adapter '+str(index+1),0.0,0.0)
    dashboard=compare.compare_all(save_images=True)
    metadata={'upstream_compare_executed':True,'dashboard':str(dashboard),'qualification':False,'judge_independent':False,
              'output_token_counts_available':False,'cloud_cost_estimates_not_applicable':True,'runs':manifests}
    (args.output/'comparison-manifest.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in metadata.items() if key!='runs'}))


if __name__=='__main__':main()
