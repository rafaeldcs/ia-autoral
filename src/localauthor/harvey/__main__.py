"""Operator CLI. Does not expose providers, training or shell tools to the LAN."""
import argparse
import json
import os
from pathlib import Path
import uuid

from ..errors import PolicyError
from ..foundation.models import ModelSpec
from ..foundation.gguf_bridge import DockerGgufRuntime
from .contracts import REVISION,content_hash,relative_file,validate_task
from .runner import adapter_hash,inventory,original_task,run_case,write_report


def atomic(path,value):
    pending=path.with_suffix('.tmp');pending.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(pending,path)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Harvey LAB com IA e sandbox locais; sem APIs externas')
    sub=parser.add_subparsers(dest='command',required=True)
    listing=sub.add_parser('inventory');listing.add_argument('--upstream',type=Path,required=True);listing.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('run');run.add_argument('--upstream',type=Path,required=True);run.add_argument('--home',type=Path,required=True)
    run.add_argument('--output',type=Path,required=True);run.add_argument('--image',required=True)
    source=run.add_mutually_exclusive_group(required=True);source.add_argument('--suite',type=Path);source.add_argument('--original',action='store_true')
    run.add_argument('--max-cases',type=int);run.add_argument('--max-turns',type=int,default=6);run.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv)
    args.upstream=args.upstream.resolve();args.output=args.output.resolve()
    catalog,files=inventory(args.upstream)
    if args.command=='inventory':
        if args.output.exists():raise PolicyError('Preserve o inventário anterior; escolha um arquivo novo.')
        args.output.parent.mkdir(parents=True,exist_ok=True);atomic(args.output,catalog);print(json.dumps({'total':catalog['total'],'revision':REVISION}));return 0
    if args.max_cases is not None and args.max_cases<1:raise PolicyError('Número de casos inválido.')
    if not 1<=args.max_turns<=200:raise PolicyError('Número de turnos inválido.')
    spec=ModelSpec.load(args.home.resolve()/'foundation/text-model.json','text')
    if spec.backend!='gguf-docker':raise PolicyError('Esta integração exige o runtime GGUF Docker local verificado.')
    if args.suite:
        suite=json.loads(args.suite.read_text(encoding='utf-8'))
        if suite.get('schema')!=1 or suite.get('frozen') is not True or not suite.get('cases'):raise PolicyError('Congele os critérios antes de executar.')
        ids=set();cases=[]
        for case in suite['cases']:
            if not isinstance(case.get('id'),str) or case['id'] in ids:raise PolicyError('Caso sem identidade única.')
            ids.add(case['id']);validate_task(case['task'])
            for name,text in case.get('documents',{}).items():
                relative_file(name)
                if not isinstance(text,str) or len(text.encode())>1_000_000:raise PolicyError('Documento de exemplo fora do orçamento.')
            cases.append(case)
    else:cases=catalog['tasks']
    frozen={'revision':REVISION,'adapter_sha256':adapter_hash(),'suite_sha256':content_hash(cases),'model_manifest':spec.manifest_sha256,'json_output':True,
            'image':args.image,'max_turns':args.max_turns,'total':len(cases),'judge_independent':False,'human_review_required':True}
    if args.resume:
        state=json.loads((args.output/'state.json').read_text(encoding='utf-8'))
        if state['frozen']!=frozen:raise PolicyError('Retomada exige mesmos casos, modelo, imagem e orçamento.')
        for row in state['cases']:
            if row['status']=='running':row.update(status='interrupted',error='Execução anterior interrompida; artefatos preservados.')
    else:
        args.output.mkdir(parents=True,exist_ok=False)
        state={'frozen':frozen,'cases':[{'id':row['id'],'status':'pending'} for row in cases]}
        atomic(args.output/'state.json',state)
    engine=None;processed=0
    try:
        for case,row in zip(cases,state['cases']):
            if row['status'] not in {'pending','interrupted'}:continue
            if args.max_cases is not None and processed>=args.max_cases:break
            if (args.output/'STOP_AFTER_CASE').exists():break
            processed+=1;row.update(status='running');atomic(args.output/'state.json',state)
            attempt=args.output/('case-'+content_hash(case['id'])[:12]+'-'+uuid.uuid4().hex[:8]);attempt.mkdir()
            row['attempt']=attempt.name;(attempt/'documents').mkdir()
            try:
                if args.suite:
                    task=case['task']
                    for name,text in case.get('documents',{}).items():
                        target=attempt/'documents'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
                else:
                    documents=args.output/'corpus'/content_hash(case['documents_prefix'])[:16];documents.mkdir(parents=True,exist_ok=True)
                    task=original_task(args.upstream,case,files,documents)
                if engine and (engine.closed or getattr(engine,'harvey_calls',0)+args.max_turns+len(task['criteria'])+5>=4800):
                    engine.close();engine=None
                if engine is None:
                    spec.verify();engine=DockerGgufRuntime(spec,diagnostics=args.output/'runtime',json_output=True)
                result=run_case(task,attempt,args.image,engine,args.max_turns,documents=documents if not args.suite else None)
                required=set(task.get('deliverables',{}).values()) or {name for criterion in task['criteria'] for name in criterion.get('deliverables',[])}
                artifacts_present=required.issubset(result['deliverables'])
                passed=(result['scores']['score']==1.0 and result['metrics']['finished_cleanly'] and artifacts_present)
                row.update(status='provisional_pass' if passed else 'failed',scores=result['scores'],metrics=result['metrics'],human_review_required=True,required_artifacts_present=artifacts_present)
                write_report(attempt,[row])
                # Keep the full original metrics and criteria in result.json;
                # the global checkpoint remains small for thousands of tasks.
                row['scores']={key:value for key,value in result['scores'].items() if key!='criteria_results'}
                row['metrics']={key:value for key,value in result['metrics'].items() if not isinstance(value,(list,dict))}
            except Exception as error:
                row.update(status='error',error=type(error).__name__+': '+str(error)[:1500]);atomic(attempt/'failure.json',row)
                write_report(attempt,[row])
            atomic(args.output/'state.json',state);write_report(args.output,state['cases'],detailed=False)
            print(json.dumps({'id':row['id'],'status':row['status'],'processed':processed,'total':len(cases)}),flush=True)
    finally:
        if engine:engine.close()
        atomic(args.output/'state.json',state);write_report(args.output,state['cases'],detailed=False)
    complete=all(row['status'] not in {'pending','running','interrupted'} for row in state['cases'])
    summary={'complete':complete,'total':len(cases),'processed':sum(row['status'] not in {'pending','running','interrupted'} for row in state['cases']),
             'provisional_pass':sum(row['status']=='provisional_pass' for row in state['cases']),
             'qualification':False,'human_review_required':True}
    atomic(args.output/'summary.json',summary);print(json.dumps(summary))
    return 0 if complete and summary['provisional_pass']==len(cases) else 2


if __name__=='__main__':raise SystemExit(main())
