"""Harvey's original loop/tools/scorer inside a host-verified Docker sandbox.

The only model transport is framed stdin/stdout to the local orchestrator.
No API keys or network transport are used by this worker.
"""
import base64
import ctypes
from contextlib import redirect_stdout
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import uuid
from datetime import datetime,timezone

from .contracts import MAX_FRAME,criterion_messages,parse_action,sign_frame,validate_task,verify_frame
from ..foundation.grounding import unmentioned_features

SESSION_KEY=None


def frame(value):
    raw=json.dumps(sign_frame(value,SESSION_KEY) if SESSION_KEY else value,ensure_ascii=False)
    if len(raw.encode())>MAX_FRAME:raise RuntimeError('RPC frame exceeds reviewed limit')
    sys.__stdout__.write(raw+'\n');sys.__stdout__.flush()


def receive():
    line=sys.stdin.buffer.readline(MAX_FRAME+1)
    if not line or len(line)>MAX_FRAME or not line.endswith(b'\n'):raise RuntimeError('Invalid local RPC frame')
    value=json.loads(line)
    return verify_frame(value,SESSION_KEY) if SESSION_KEY else value


def model(messages,purpose='judge'):
    frame({'op':'generate','messages':messages,'purpose':purpose})
    response=receive()
    if response.get('error'):raise RuntimeError(response['error'])
    if response.get('truncated'):raise RuntimeError('Local model output was truncated')
    return response['text']


def record(kind,data):
    if len(data)>64_000_000:raise RuntimeError('Record exceeds artifact budget')
    for offset in range(0,len(data),256_000):frame({'op':'record','kind':kind,'offset':offset,'data':base64.b64encode(data[offset:offset+256_000]).decode()})
    if not data:frame({'op':'record','kind':kind,'offset':0,'data':''})
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def main():
    global SESSION_KEY
    if (not Path('/.dockerenv').is_file() or os.getuid()!=10001 or
            os.environ.get('LOCALAUTHOR_HARVEY_ISOLATED')!='1'):
        raise RuntimeError('Worker only runs inside the verified sandbox')
    from lab_core.harness.adapters.base import ModelResponse,ToolCall
    from lab_core.harness.agent_loop import run_agent
    from lab_core.harness.tools import ToolExecutor
    from lab_core.sandbox.sandbox import Sandbox,ExecResult
    from lab_core.evaluation import scoring
    initial=receive();SESSION_KEY=bytes.fromhex(initial.pop('session_key'));task=validate_task(initial['task']);del initial
    if len(SESSION_KEY)!=32:raise RuntimeError('Invalid session key')
    # Generated child commands must not inspect the controller's memory or
    # descriptors, even when sharing its non-root UID inside the container.
    libc=ctypes.CDLL(None)
    if libc.prctl(4,0,0,0,0)!=0 or libc.prctl(3,0,0,0,0)!=0:raise RuntimeError('Controller memory protection unavailable')
    limits=receive();max_turns=limits['max_turns']
    Path('/workspace/history').symlink_to('/opt/localauthor/history',target_is_directory=True)
    class ContainedSandbox(Sandbox):
        def start(self):self._started=True
        def stop(self):self._started=False
        def exec(self,command,*,cwd='/workspace',timeout=None,env=None):
            self.assert_sandbox_path(cwd)
            timeout=min(timeout or self.default_timeout,60)
            # Output is capped in the container before capture; neither generated
            # shell commands nor document parsers ever execute on the host.
            wrapped='timeout --kill-after=2 '+str(timeout)+' bash -lc '+shlex.quote(command)
            result=subprocess.run(['bash','-c',wrapped+' 2>&1 | head -c 131072; exit ${PIPESTATUS[0]}'],
                cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,timeout=timeout+5)
            return ExecResult(stdout=result.stdout.decode('utf-8',errors='replace'),stderr=result.stderr.decode('utf-8',errors='replace'),
                              returncode=result.returncode,timed_out=result.returncode in {124,137})
    class Adapter:
        def __init__(self):self.protocol_retries=0
        def make_system_message(self,content):return {'role':'system','content':content}
        def make_user_message(self,content):return {'role':'user','content':content}
        def make_tool_result_messages(self,results):
            return [{'role':'user','content':'Tool result '+ident+': '+result} for ident,result in results]
        def chat(self,messages,tools):
            # Keep every tool and parameter, dropping only verbose schema prose.
            def concise(value):
                if isinstance(value,dict):return {key:concise(item) for key,item in value.items() if key!='description'}
                if isinstance(value,list):return [concise(item) for item in value]
                return value
            signatures={tool['name']:concise(tool['parameters']) for tool in tools}
            protocol=('Return exactly one JSON object, no markdown. Call a tool using '
                '{"tool":"read","arguments":{"file_path":"/workspace/documents/context.md"}} '
                'or finish with {"tool":"finish","arguments":{"summary":"done","deliverables":["response.md"]}}. '
                'Arguments must be a JSON object, never an array. Use exactly the argument names below. Tools: '+json.dumps(signatures,separators=(',',':')))
            while True:
                sent=[{'role':'system','content':messages[0]['content']+'\n'+protocol},*messages[1:]]
                text=model(sent,'agent')
                try:action=parse_action(text);break
                except Exception:
                    if self.protocol_retries>=2:raise
                    self.protocol_retries+=1
                    messages.extend([{'role':'assistant','content':text},{'role':'user','content':'That call was NOT executed: invalid protocol. Return one JSON object with tool (string) and arguments (JSON object, never array), or final (string). Preserve the task; do not invent a result.'}])
            calls=[] if 'final' in action else [ToolCall(id=uuid.uuid4().hex,name=action['tool'],arguments=json.dumps(action['arguments']))]
            return ModelResponse(message={'role':'assistant','content':text},tool_calls=calls,text=action.get('final',''),finish_reason='stop')
    class LocalJudge:
        def evaluate_from_file(self,prompt_name,variables):
            if prompt_name!='rubric_criterion':raise ValueError('Unexpected scoring prompt')
            output=model(criterion_messages(variables))
            value=json.loads(output)
            if not isinstance(value,dict) or set(value)!={'reasoning','verdict'} or value['verdict'] not in {'pass','fail'} or not isinstance(value['reasoning'],str):raise ValueError('Invalid local judge verdict')
            return value
    def local_filename_match(unresolved,available_files,output_dir):
        # Upstream's private fallback hardcodes a cloud provider. Keep its
        # matching stage but route it through the same local-only transport.
        previews={name:scoring.read_file_as_text(output_dir/name)[:500] for name in available_files}
        value=json.loads(model([{'role':'system','content':'Match deliverable keys to available filenames using the previews. Return a JSON object containing every requested key, whose value is an available filename or null. Never invent a file.'},
                               {'role':'user','content':json.dumps({'deliverables':unresolved,'files':previews})}]))
        if not isinstance(value,dict) or set(value)!=set(unresolved) or any(name is not None and name not in available_files for name in value.values()):
            raise ValueError('Invalid local filename match')
        return value
    scoring._llm_match_deliverables=local_filename_match
    class LocalToolExecutor(ToolExecutor):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.input_evidence=[];self.grounding_checks=[]
        def _read(self,file_path,offset,limit):
            result=super()._read(file_path,offset,limit)
            if self._resolve_read_path(file_path).startswith('/workspace/documents/') and not result.startswith('Error:'):
                self.input_evidence.append(result)
            return result
        def _grep(self,pattern_str,search_path,file_glob,output_mode):
            # The pinned upstream schema permits a FILE, but its implementation
            # calls Path.glob on that file and always returns no matches. Route
            # it through the original directory implementation with an exact glob.
            target=Path(self._resolve_search_path(search_path))
            if target.is_file():
                if file_glob and not target.match(file_glob):return "No matches for '"+pattern_str+"'"
                result=super()._grep(pattern_str,str(target.parent),target.name,output_mode)
            else:result=super()._grep(pattern_str,search_path,file_glob,output_mode)
            if str(target)=='/workspace/documents' or str(target).startswith('/workspace/documents/'):
                self.input_evidence.append(result)
            return result
        def check_grounding(self):
            if re.search(r'postagem|marketing|publicidade|an[úu]ncio',task['title']+' '+task['instructions'],re.I):
                texts=[]
                for path in Path('/workspace/output').rglob('*.md'):
                    if path.is_symlink():raise ValueError('Symlink output is not exportable')
                    if path.stat().st_size>1_000_000:raise ValueError('Marketing draft exceeds grounding review budget')
                    texts.append(path.read_text(encoding='utf-8'))
                candidate='\n'.join(texts);unsupported=unmentioned_features(candidate,'\n'.join(self.input_evidence))
                self.grounding_checks.append({'candidate':candidate,'sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                    'unsupported_families':unsupported,'decision':'reject' if unsupported else 'no_absent_known_features'})
                return {'checked':True,'unsupported_families':unsupported}
            return {'checked':False,'unsupported_families':[]}
        def _finish(self,summary,deliverables):
            grounding=self.check_grounding()
            if grounding['unsupported_families']:
                return ('Error: these product claims are absent from supplied evidence: '+', '.join(grounding['unsupported_families'])
                    +'. Re-read the sources and edit your own draft. Remove unsupported claims; do not just replace them with synonyms. '
                    +'Keep the post short when few facts are known. No completion was accepted.')
            return super()._finish(summary,deliverables)
    shutil.copytree('/opt/harvey-core/lab_core/harness/skills','/workspace/skills',dirs_exist_ok=True)
    sandbox=ContainedSandbox('/workspace/documents','/workspace/output','/workspace',default_timeout=30)
    sandbox.start();executor=LocalToolExecutor(sandbox=sandbox,shell_timeout=30)
    instructions=(Path('/opt/harvey-core/lab_core/harness/system_prompt.md').read_text()+
                  '\nThe sandbox is offline. Do not install dependencies or contact real people. When reporting tests, distinguish planned cases from observed executions; expected results are not execution evidence. For large documents, use read offset/limit or targeted grep/bash extraction. Working-memory excerpts always identify a read-only archive: revisit it in small ranges before relying on omitted details. Do not repeat an identical unsuccessful search: inspect a bounded page or try another method before concluding evidence is absent. Write the requested deliverables, then finish.\n'+limits['commercial_grounding'])
    with redirect_stdout(sys.stderr):
        result=run_agent(Adapter(),instructions,task['instructions'],executor,max_turns=max_turns,
                         transcript_path='/tmp/transcript.jsonl')
    # End the agent's process lifetime before evaluating its fixed outputs.
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit() and int(entry.name)!=os.getpid():
            try:
                if entry.stat().st_uid==os.getuid():os.kill(int(entry.name),signal.SIGKILL)
            except (ProcessLookupError,FileNotFoundError,PermissionError):pass
    # Also check natural no-tool-call stops: they cannot bypass the finish guard.
    final_grounding=executor.check_grounding()
    run=Path('/tmp/grade');run.mkdir();(run/'output').symlink_to('/workspace/output',target_is_directory=True)
    with redirect_stdout(sys.stderr):score=scoring.score_rubric(task['criteria'],run,LocalJudge(),task['title'],parallel=1).to_dict()
    metrics={**{k:v for k,v in result.items() if k!='messages'},**executor.get_metrics()}
    scores={**score,'task':task['title'],'run_id':limits['run_id'],'judge_model':'LocalAuthor local model (not independent)',
            'scored_at':datetime.now(timezone.utc).isoformat()}
    # Preserve original reports without rendering their unescaped model text.
    os.environ['LAB_ROOT']='/tmp/lab';official=Path('/tmp/lab/results')/limits['run_id'];official.mkdir(parents=True)
    (official/'scores.json').write_text(json.dumps(scores),encoding='utf-8')
    from lab_core.evaluation.report import generate_report
    with redirect_stdout(sys.stderr):original_report=generate_report(limits['run_id']).read_text()
    deliverables={}
    total_bytes=0
    for path in Path('/workspace/output').rglob('*'):
        if path.is_symlink():raise RuntimeError('Symlink output is not exportable')
        if path.is_file():
            name=str(path.relative_to('/workspace/output'))
            if path.stat().st_size>16_000_000:raise RuntimeError('Deliverable exceeds export budget')
            data=path.read_bytes()
            total_bytes+=len(data)
            if total_bytes>64_000_000 or len(deliverables)>=256:raise RuntimeError('Total artifact export budget exceeded')
            for offset in range(0,len(data),256_000):
                frame({'op':'artifact','path':name,'offset':offset,'data':base64.b64encode(data[offset:offset+256_000]).decode()})
            deliverables[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            if not data:frame({'op':'artifact','path':name,'offset':0,'data':''})
    result={'scores':scores,'metrics':metrics,'deliverables':deliverables,'grounding':final_grounding,'judge_independent':False,'human_review_required':True}
    records={'transcript':record('transcript',Path('/tmp/transcript.jsonl').read_bytes()),
             'report':record('report',original_report.encode()),
             'result':record('result',json.dumps(result,ensure_ascii=False).encode()),
             'grounding':record('grounding',''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in executor.grounding_checks).encode())}
    frame({'op':'done','records':records})


if __name__=='__main__':
    try:main()
    except Exception as error:
        frame({'op':'error','error':type(error).__name__+': '+str(error)[:1500]});raise
