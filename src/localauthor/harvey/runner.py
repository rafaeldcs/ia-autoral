"""Operator-only Harvey LAB runner: local model, verified offline containers."""
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import posixpath
import queue
import re
import secrets
import subprocess
import shutil
import threading
import time
import uuid

from ..errors import PolicyError
from ..foundation.models import ModelSpec
from ..foundation.gguf_bridge import DockerGgufRuntime
from .contracts import MAX_FRAME,RECORDS,REVISION,UPSTREAM,content_hash,receive_record,relative_file,sign_frame,validate_task,verify_frame,verify_sandbox
from .context import fit_agent_context
from ..foundation.grounding import COMMERCIAL_GROUNDING

ROOT=Path(__file__).resolve().parents[3]
VERIFIED_CORPORA=set()


def adapter_hash():
    # Resume must also detect changes to the inference bridge, model loader and
    # isolation checks, not just changes to these four benchmark modules.
    sources=sorted((ROOT/'src/localauthor').rglob('*.py'))
    if not sources:raise PolicyError('Fontes do controlador ausentes; não congelar execução.')
    sources.append(ROOT/'scripts/foundation-gguf-rpc.py')
    return content_hash({path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sources})


def git(root,*args):
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=120)
    if result.returncode:raise PolicyError('Falha ao ler a revisão congelada do Harvey LAB.')
    return result.stdout


def verify_checkout(root):
    if git(root,'rev-parse','HEAD').decode().strip()!=REVISION:
        raise PolicyError('A revisão do Harvey LAB difere da revisão auditada.')
    return root


def inventory(root):
    verify_checkout(root)
    rows=git(root,'ls-tree','-r','-l','-z',REVISION,'tasks').split(b'\0')
    tasks={};files=[];stats={}
    for row in rows:
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,ident,size=metadata.split();name=name.decode('utf-8')
        if kind!=b'blob':continue
        files.append((name,int(size),mode.decode(),ident.decode()))
        if name.endswith('/task.json'):
            key=name[len('tasks/'):-len('/task.json')]
            tasks[key]={'id':key,'definition':name,'git_blob':ident.decode(),'document_files':0,'document_bytes':0}
        parent=posixpath.dirname(name)
        while parent:
            count,total=stats.get(parent,(0,0));stats[parent]=(count+1,total+int(size));parent=posixpath.dirname(parent)
    identifiers=[row['git_blob'] for row in tasks.values()]
    batch=subprocess.run(['git','-C',str(root),'cat-file','--batch'],input=('\n'.join(identifiers)+'\n').encode(),capture_output=True,timeout=120)
    if batch.returncode:raise PolicyError('Inventário de definições incompleto.')
    offset=0
    for row in tasks.values():
        end=batch.stdout.index(b'\n',offset);header=batch.stdout[offset:end].split();size=int(header[2]);offset=end+1
        raw=batch.stdout[offset:offset+size];offset+=size+1
        if header[0].decode()!=row['git_blob'] or header[1]!=b'blob':raise PolicyError('Blob de tarefa divergente.')
        task=json.loads(raw);row['definition_sha256']=hashlib.sha256(raw).hexdigest();row['criteria']=len(task.get('criteria',[]))
        source=task.get('docs_dir','documents')
        if not isinstance(source,str) or '\\' in source or source.startswith('/') or ':' in source:raise PolicyError('Raiz de documentos inválida.')
        prefix=posixpath.normpath(posixpath.join(posixpath.dirname(row['definition']),source))
        if not prefix.startswith('tasks/'):raise PolicyError('Documentos escapam da árvore de tarefas.')
        row['documents_prefix']=prefix
        row['document_files'],row['document_bytes']=stats.get(prefix,(0,0))
    return {'source':UPSTREAM,'revision':REVISION,'tasks':list(tasks.values()),'total':len(tasks),'complete_tree':True},files


def original_task(root,row,files,documents):
    if row['document_bytes']>4_000_000_000:raise PolicyError('Documentos excedem orçamento de 4 GB por corpus; caso não executado.')
    raw_task=git(root,'show',REVISION+':'+row['definition'])
    if hashlib.sha256(raw_task).hexdigest()!=row['definition_sha256']:raise PolicyError('Definição de tarefa divergente.')
    task=validate_task(json.loads(raw_task))
    prefix=row['documents_prefix']+'/'
    marker=documents.parent/(documents.name+'-source.json')
    identity={'revision':REVISION,'prefix':prefix,'bytes':row['document_bytes'],'files':row['document_files']}
    if marker.exists():
        recorded=json.loads(marker.read_text(encoding='utf-8'))
        if recorded.get('identity')!=identity:raise PolicyError('Cache de documentos divergente.')
        if str(marker) not in VERIFIED_CORPORA:
            for entry in recorded['manifest']:
                relative=relative_file(entry['path']);path=documents.joinpath(*relative.parts)
                if os.name=='nt':path=Path('\\\\?\\'+str(path.resolve()))
                if path.is_symlink() or path.stat().st_size!=entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
                    raise PolicyError('Arquivo do corpus foi alterado; não retomar sobre dados diferentes.')
            if len(recorded['manifest'])!=identity['files']:raise PolicyError('Manifesto de corpus incompleto.')
            VERIFIED_CORPORA.add(str(marker))
        return task
    if shutil.disk_usage(documents.parent).free<row['document_bytes']+512_000_000:raise PolicyError('Espaço livre insuficiente para preservar o corpus.')
    seen=set();manifest=[]
    for name,size,mode,ident in files:
        if not name.startswith(prefix):continue
        if name.endswith('/task.json'):raise PolicyError('A raiz de documentos inclui rubricas; não expor ao agente.')
        relative=relative_file(name[len(prefix):]);key=str(relative).casefold()
        if key in seen or mode not in {'100644','100755'}:raise PolicyError('Colisão de caminhos ou link na entrada original.')
        seen.add(key)
        destination=documents.joinpath(*relative.parts)
        # Extended Windows paths allow original long document names without
        # renaming them or changing the task's evidence.
        if os.name=='nt':destination=Path('\\\\?\\'+str(destination.resolve()))
        destination.parent.mkdir(parents=True,exist_ok=True)
        raw=git(root,'cat-file','blob',ident)
        if len(raw)!=size:raise PolicyError('Blob de documento incompleto.')
        destination.write_bytes(raw)
        manifest.append({'path':str(relative),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    marker.write_text(json.dumps({'identity':identity,'manifest':manifest}),encoding='utf-8');VERIFIED_CORPORA.add(str(marker))
    return task


def docker(args,timeout=30):
    result=subprocess.run(['docker',*args],capture_output=True,timeout=timeout)
    if result.returncode:raise PolicyError('Docker não concluiu a operação da sandbox: '+result.stderr.decode(errors='replace')[-800:])
    return result.stdout


def run_case(task,run,image,engine,max_turns=6,*,documents=None):
    validate_task(task)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise PolicyError('Use o ID imutável da imagem local revisada.')
    if type(max_turns) is not int or not 1<=max_turns<=200:raise PolicyError('Orçamento de turnos inválido.')
    for name in ('workspace','documents','output'):(run/name).mkdir(exist_ok=True)
    (run/'task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2),encoding='utf-8')
    controller=run/'controller';(controller/'localauthor/harvey').mkdir(parents=True)
    (controller/'history').mkdir()
    (controller/'localauthor/foundation').mkdir()
    for name in ['__init__.py','grounding.py']:shutil.copy2(ROOT/'src/localauthor/foundation'/name,controller/'localauthor/foundation'/name)
    for name in ['__init__.py','errors.py']:shutil.copy2(ROOT/'src/localauthor'/name,controller/'localauthor'/name)
    for name in ['__init__.py','contracts.py','worker.py']:shutil.copy2(Path(__file__).parent/name,controller/'localauthor/harvey'/name)
    expected={'/opt/localauthor':(str(controller),False),'/workspace/documents':(str(documents or run/'documents'),False)}
    args=['create','--pull=never','--interactive','--name','localauthor-harvey-'+uuid.uuid4().hex,
          '--network=none','--read-only','--user=10001:10001','--cap-drop=ALL','--security-opt=no-new-privileges',
          '--memory=2g','--memory-swap=2g','--cpus=2','--pids-limit=128','--tmpfs','/tmp:rw,nosuid,nodev,size=256m',
          '--tmpfs','/workspace:rw,nosuid,nodev,size=512m,mode=1777','--tmpfs','/workspace/output:rw,nosuid,nodev,size=64m,mode=1777',
          '--env','PYTHONPATH=/opt/localauthor:/opt/harvey-core','--env','HOME=/tmp',
          '--env','LOCALAUTHOR_HARVEY_ISOLATED=1','--env','WORKSPACE_DIR=/workspace',
          '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1',
          '--env','DOCUMENTS_DIR=/workspace/documents','--env','OUTPUT_DIR=/workspace/output']
    for destination,(source,writable) in expected.items():args+=['--mount','type=bind,source='+source+',target='+destination+('' if writable else ',readonly')]
    args+=[image,'python','-m','localauthor.harvey.worker']
    container=docker(args).decode().strip();process=None
    try:
        info=json.loads(docker(['inspect',container]))[0];verify_sandbox(info,image,expected)
        (run/'sandbox.json').write_text(json.dumps({'image':image,'network':'none','readonly_root':True,'non_root':True,'verified_before_start':True}),encoding='utf-8')
        process=subprocess.Popen(['docker','start','--attach','--interactive',container],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        frames=queue.Queue(maxsize=4);errors=bytearray()
        def reader():
            try:
                while True:
                    line=process.stdout.readline(MAX_FRAME+1)
                    if not line:break
                    if len(line)>MAX_FRAME or not line.endswith(b'\n'):raise PolicyError('Frame da sandbox fora do orçamento.')
                    frames.put(json.loads(line),timeout=5)
            except Exception as error:frames.put({'op':'error','error':type(error).__name__+': '+str(error)},timeout=5)
            finally:
                try:frames.put({'op':'eof'},timeout=5)
                except queue.Full:pass
        def drain():
            for block in iter(lambda:process.stderr.read(4096),b''):
                if len(errors)<100_000:errors.extend(block[:100_000-len(errors)])
        threading.Thread(target=reader,daemon=True).start();threading.Thread(target=drain,daemon=True).start()
        key=secrets.token_bytes(32)
        def send(value,bootstrap=False):
            raw=json.dumps(value if bootstrap else sign_frame(value,key),ensure_ascii=False).encode()+b'\n'
            if len(raw)>MAX_FRAME:raise PolicyError('Entrada RPC fora do orçamento.')
            process.stdin.write(raw);process.stdin.flush()
        send({'task':task,'session_key':key.hex()},bootstrap=True);send({'max_turns':max_turns,'run_id':run.name,'commercial_grounding':COMMERCIAL_GROUNDING})
        started=time.monotonic();model_calls=0;exported={};total_exported=0
        while time.monotonic()-started<3600:
            try:message=frames.get(timeout=300)
            except queue.Empty:raise PolicyError('Sandbox sem resposta por cinco minutos.')
            message=verify_frame(message,key);operation=message.get('op')
            if operation=='generate':
                model_calls+=1
                engine.harvey_calls=getattr(engine,'harvey_calls',0)+1
                if model_calls>max_turns+len(task['criteria'])+5:raise PolicyError('Chamadas de modelo excederam os critérios e turnos congelados.')
                try:
                    messages=message['messages']
                    def counted(rows):
                        engine.harvey_rpc_calls=getattr(engine,'harvey_rpc_calls',0)+1
                        return engine.count(rows)
                    if message.get('purpose')=='agent':
                        archive_name=str(model_calls).zfill(6)+'.json'
                        raw=json.dumps(messages,ensure_ascii=False,indent=2).encode()
                        (controller/'history'/archive_name).write_bytes(raw)
                        reference='/workspace/history/'+archive_name
                        messages,event=fit_agent_context(messages,counted,engine.spec.context_tokens-engine.spec.output_tokens,reference)
                        with (run/'context-events.jsonl').open('a',encoding='utf-8') as journal:
                            journal.write(json.dumps({**event,'call':model_calls,'archive':reference,'original_sha256':hashlib.sha256(raw).hexdigest(),'sent_sha256':content_hash(messages)})+'\n')
                    if len(json.dumps(messages,ensure_ascii=False).encode())>110_000:
                        raise PolicyError('context_length_exceeded: avaliação completa excede o transporte; não foi recortada.')
                    count=event['after_tokens'] if message.get('purpose')=='agent' else counted(messages)
                    if count+engine.spec.output_tokens>engine.spec.context_tokens:
                        raise PolicyError('context_length_exceeded: contexto local insuficiente; histórico não foi apagado.')
                    engine.harvey_rpc_calls=getattr(engine,'harvey_rpc_calls',0)+1
                    text,truncated=engine.generate(messages);send({'text':text,'truncated':truncated})
                    with (run/'generations.jsonl').open('a',encoding='utf-8') as audit:
                        audit.write(json.dumps({'call':model_calls,'input_tokens':count,'output':text,'truncated':truncated,'purpose':message.get('purpose','judge')},ensure_ascii=False)+'\n')
                except Exception as error:send({'error':type(error).__name__+': '+str(error)[:600]})
            elif operation=='done':
                if set(message.get('records',{}))!=set(RECORDS):raise PolicyError('Registros obrigatórios ausentes.')
                for kind,entry in message['records'].items():
                    data=(run/RECORDS[kind]).read_bytes()
                    if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise PolicyError('Registro incompleto ou alterado.')
                message=json.loads((run/RECORDS['result']).read_text(encoding='utf-8'))
                # Outputs are exported from container tmpfs through authenticated
                # chunks. Artifacts, transcripts and upstream HTML remain untrusted.
                for name,entry in message['deliverables'].items():
                    relative=relative_file(name);path=run/'output'/str(relative)
                    if path.is_symlink() or not path.resolve().is_relative_to((run/'output').resolve()) or path.stat().st_size!=entry['bytes']:
                        raise PolicyError('Artefato fora da pasta de saída ou incompleto.')
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise PolicyError('Hash de artefato divergente.')
                message.update(model_calls=model_calls,seconds=round(time.monotonic()-started,2),real_model=isinstance(engine,DockerGgufRuntime),task_sha256=content_hash(task),upstream_revision=REVISION)
                (run/'result.json').write_text(json.dumps(message,ensure_ascii=False,indent=2),encoding='utf-8')
                return message
            elif operation=='artifact':
                relative=relative_file(message['path']);data=base64.b64decode(message['data'],validate=True)
                offset=message.get('offset');name=str(relative)
                if (type(offset) is not int or offset!=exported.get(name,0) or offset+len(data)>16_000_000
                        or total_exported+len(data)>64_000_000 or (name not in exported and len(exported)>=256)):
                    raise PolicyError('Artefato fora de ordem ou acima do orçamento.')
                target=run/'output'/name;target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('wb' if offset==0 else 'ab') as stream:stream.write(data)
                exported[name]=offset+len(data);total_exported+=len(data)
            elif operation=='record':receive_record(run,message)
            else:raise PolicyError(message.get('error','Sandbox encerrou sem resultado completo.'))
        raise PolicyError('Orçamento máximo de uma hora por tarefa atingido.')
    finally:
        if process and process.stdin:
            try:process.stdin.close()
            except OSError:pass
        try:docker(['rm','-f',container])
        finally:
            if process:
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
            (run/'worker-stderr.txt').write_bytes(bytes(errors) if 'errors' in locals() else b'')


def write_report(directory,rows,*,detailed=True):
    cards=[]
    labels={'pending':'Aguardando execução','running':'Em execução','interrupted':'Interrompido — não aprovado','provisional_pass':'Aprovação provisória — revisão humana pendente','failed':'Reprovado','error':'Erro — não aprovado'}
    for row in rows:
        criteria=row.get('scores',{}).get('criteria_results',[]) if detailed else []
        lines=''.join('<li>'+html.escape(str(c.get('verdict','error'))+': '+str(c.get('title',''))+' — '+str(c.get('reasoning','')))+'</li>' for c in criteria)
        link=''
        if not detailed and row.get('attempt'):
            path=str(relative_file(row['attempt']+'/report.html'));link='<p><a href="'+html.escape(path,quote=True)+'">Ver critérios e evidências desta tentativa</a></p>'
        cards.append('<section><h2>'+html.escape(row['id'])+'</h2><p>'+html.escape(labels.get(row['status'],row['status']))+'</p><p>'+html.escape(row.get('error',''))+'</p>'+link+'<ul>'+lines+'</ul></section>')
    counts={key:sum(row['status']==key for row in rows) for key in labels}
    summary=' · '.join(label+': '+str(counts[key]) for key,label in labels.items() if counts[key])
    body='<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>LocalAuthor · Harvey LAB</title><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><style>body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:16px;background:#191919;color:#eee}section{border:1px solid #555;border-radius:12px;padding:20px;margin:20px 0}li{margin:12px 0}a{color:#b7afff}</style><h1>LocalAuthor · Harvey LAB</h1><p>Modelo e avaliador locais. O avaliador não é independente. Revisão humana necessária. Erros e casos pendentes não são aprovações.</p><p>'+html.escape(summary)+'</p>'+''.join(cards)
    pending=directory/'report.html.tmp';pending.write_text(body,encoding='utf-8');os.replace(pending,directory/'report.html')
