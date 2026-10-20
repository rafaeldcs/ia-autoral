"""Opt-in execution of five recorded LocalAuthor artifacts in an offline Docker lab.

Never executes generated code on the host. Does not call an AI API or apply edits.
The operator feeds failures to the local model and preserves a new candidate.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from localauthor.foundation.instruction_review import code_blocks

FILES={'Tarefa.cs','TarefaService.cs','GeneratedTests.cs','ListaTarefas.tsx','tarefas.sql'}
EXPECTED={'csharp':16,'tsx':9,'sql':13}


def decode_candidate(candidate):
    if not isinstance(candidate,dict) or candidate.get('schema')!=1 or set(candidate.get('artifacts',{}))!=FILES:
        raise ValueError('Exactly the five supported recorded artifacts are required')
    files={};provenance={}
    for name,row in candidate['artifacts'].items():
        content=row.get('content');metadata=row.get('metadata',{})
        if not isinstance(content,str) or not 1<=len(content)<=40000:
            raise ValueError('Invalid response size')
        if metadata.get('origin')!='foundation_text' or metadata.get('possibly_truncated') is not False or not metadata.get('model',{}).get('model_id'):
            raise ValueError('A complete registered local-model response is required')
        digest=hashlib.sha256(content.encode()).hexdigest()
        if row.get('sha256')!=digest:raise ValueError('Original response hash mismatch')
        blocks=code_blocks(content)
        if len(blocks)!=1:raise ValueError('Each selected response must have exactly one original code block')
        files[name]=blocks[0]
        provenance[name]={'response_sha256':digest,'source_sha256':hashlib.sha256(blocks[0].encode()).hexdigest(),
                          'model':metadata['model'],'experience_id':metadata.get('experience_id'),
                          'source_conversation':row.get('source_conversation'),'turn':row.get('turn')}
    return files,provenance


def validate_container(config,image,runner):
    h=config['HostConfig'];mounts=config['Mounts']
    source=mounts[0].get('Source','').replace('\\','/').rstrip('/') if len(mounts)==1 else ''
    expected=runner.as_posix().rstrip('/')
    if source.startswith('/run/desktop/mnt/host/') and re.match(r'^[A-Za-z]:/',expected):
        expected='/run/desktop/mnt/host/'+expected[0].lower()+expected[2:]
    valid=(config['Image']==image and h['NetworkMode']=='none' and h['ReadonlyRootfs'] and not h['Privileged']
           and not h['PortBindings'] and not h['Devices'] and not h.get('DeviceRequests')
           and config['Config']['User']=='10001:10001' and h['CapDrop']==['ALL'] and not h.get('CapAdd')
           and 'no-new-privileges' in h['SecurityOpt'] and h['Memory']==4*1024**3
           and h['NanoCpus']==2_000_000_000 and h['PidsLimit']==512
           and h['PidMode']=='' and h.get('IpcMode')!='host' and not h.get('Binds')
           and len(mounts)==1 and mounts[0]['Type']=='bind' and mounts[0]['Destination']=='/runner'
           and not mounts[0]['RW'] and source.casefold()==expected.casefold()
           and h['Tmpfs']=={'/tmp':'rw,nosuid,nodev,size=2g,mode=1777'})
    if not valid:raise ValueError('Sandbox configuration rejected before start')


def summarize(report,mode):
    if report.get('infrastructure_error'):return False
    cases=report.get('cases',[])
    if not isinstance(cases,list) or len(cases)!=sum(EXPECTED.values()):return False
    if any(r.get('area') not in EXPECTED for r in cases):return False
    for area,count in EXPECTED.items():
        rows=[r for r in cases if r.get('area')==area]
        if len(rows)!=count or len({r.get('name') for r in rows})!=count:return False
        if any(type(r.get('passed')) is not bool for r in rows):return False
        if mode=='normal' and not all(r['passed'] for r in rows):return False
        if mode=='mutations' and not any(not r['passed'] for r in rows):return False
    required=('csharp_build_passed','tsx_typecheck_passed','next_build_passed','sql_script_passed')
    if not all(report.get(key) is True for key in required):return False
    if any(report.get(area+'_error') for area in EXPECTED):return False
    return report.get('csharp_test_exit')==(0 if mode=='normal' else 1)


def docker(args,seconds=30):
    return subprocess.run(['docker',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=seconds,check=True).stdout


def bounded_start(cid,payload,seconds):
    process=subprocess.Popen(['docker','start','--attach','--interactive',cid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output=bytearray();overflow=threading.Event()
    def drain():
        while chunk:=process.stdout.read(65536):
            if len(output)+len(chunk)>10_000_000:overflow.set()
            else:output.extend(chunk)
    thread=threading.Thread(target=drain,daemon=True);thread.start()
    process.stdin.write(json.dumps(payload,ensure_ascii=False).encode());process.stdin.close()
    start=time.monotonic()
    while process.poll() is None:
        if overflow.is_set() or time.monotonic()-start>seconds:
            docker(['stop','--time','2',cid],seconds=15)
            process.wait(timeout=15);thread.join(timeout=3)
            raise RuntimeError('Output limit or execution deadline exceeded')
        time.sleep(.2)
    thread.join(timeout=5)
    if thread.is_alive() or overflow.is_set():raise RuntimeError('Incomplete/excessive output')
    return process.returncode,bytes(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--image',required=True,help='Existing local sha256 image ID; no pull')
    parser.add_argument('--mode',choices=['normal','mutations'],default='normal')
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a new output directory; evidence is append-only')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',args.image):parser.error('Pin the existing image ID')
    if args.candidate.stat().st_size>1_000_000:parser.error('Candidate file too large')
    files,provenance=decode_candidate(json.loads(args.candidate.read_text(encoding='utf-8')))
    runner=(ROOT/'qa/chat-code-replay').resolve()
    if ',' in str(runner):parser.error('Runner path cannot contain a Docker mount separator')
    if any(p.is_symlink() for p in runner.iterdir()):parser.error('Runner must contain regular trusted files')
    args.output.mkdir(parents=True)
    for name,source in files.items():(args.output/name).write_bytes(source.encode())
    record={'mode':args.mode,'image':args.image,'provenance':provenance,'scope':'38 finite independent/model-authored cases; not universal qualification',
            'generated_code_on_host':False,'weights_trained':False,'no_dependency_downloads':True,
            'evaluator_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*runner.iterdir()] if p.is_file()}}
    cid=None
    try:
        docker(['image','inspect',args.image])
        cid=docker(['create','--pull=never','--name','localauthor-chat-code-'+uuid.uuid4().hex,
            '--network=none','--read-only','--user=10001:10001','--cap-drop=ALL','--security-opt=no-new-privileges',
            '--pids-limit=512','--memory=4g','--cpus=2','--tmpfs','/tmp:rw,nosuid,nodev,size=2g,mode=1777',
            '--mount',f'type=bind,source={runner},target=/runner,readonly','--interactive',
            '--entrypoint','python3',args.image,'-I','/runner/worker.py']).strip()
        config=json.loads(docker(['inspect',cid]))[0]
        (args.output/'container-inspect.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        validate_container(config,args.image,runner)
        record['container']=cid;record['inspection_passed']=True
        exit_code,raw=bounded_start(cid,{'files':files,'mode':args.mode},480)
        (args.output/'worker-output.txt').write_bytes(raw)
        result=json.loads(raw)
        saved=result.pop('files',{})
        allowed={'csharp-results.trx','browser-before.png','browser-after.png','next-server.txt'}
        for name,data in saved.items():
            if name not in allowed:raise ValueError('Unexpected worker artifact')
            decoded=base64.b64decode(data,validate=True)
            if len(decoded)>2_000_000:raise ValueError('Worker artifact too large')
            (args.output/name).write_bytes(decoded)
        record.update(worker_exit=exit_code,execution=result,success=exit_code==0 and summarize(result,args.mode))
    except Exception as exc:
        record['success']=False;record['error']=str(exc)[-6000:]
    finally:
        if cid:
            try:
                state=json.loads(docker(['inspect',cid]))[0]['State'];record['container_state']=state
                docker(['rm','--force',cid],seconds=20);record['owned_container_removed']=True
            except Exception as exc:record['cleanup_error']=str(exc);record['success']=False
        (args.output/'report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'success':record.get('success',False),'output':str(args.output),
        'cases':len(record.get('execution',{}).get('cases',[])),'error':record.get('error')}))
    return 0 if record.get('success') else 1


if __name__=='__main__':raise SystemExit(main())
