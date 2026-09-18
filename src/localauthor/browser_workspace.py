"""Project-scoped live browser sessions. Secrets travel through stdin only."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from urllib.parse import urlsplit

from .browser_capture import command
from .errors import PolicyError, NotFoundError
from .research import validate_url, public_addresses
from .util import utcnow, write_json, read_json


def selected_models(home):
    """Only approved, hash-matching local courses. No downloads or fallback."""
    selected = {}
    for prefix, approved, kind in (('investigation-lab-', 'labApproved', 'policy'),
                                   ('investigation-text-', 'labApproved', 'control'),
                                   ('site-reader-', 'courseApproved', 'screen')):
        for path in sorted((home/'exports').glob(prefix+'*/report.json'), reverse=True):
            report = read_json(path)
            if report.get(approved) is not True:
                continue
            info = {'path': report.get('selectedCheckpoint'), 'sha256': report.get('checkpointHash')} if kind == 'policy' else report.get('checkpoints', {}).get(kind, {})
            checkpoint = Path(info.get('path') or '')
            if not checkpoint.is_file() or checkpoint.is_symlink() or not checkpoint.resolve().is_relative_to((home/'models').resolve()):
                raise PolicyError('Checkpoint fora da pasta local de modelos.')
            if checkpoint.stat().st_size > 3_000_000 or hashlib.sha256(checkpoint.read_bytes()).hexdigest() != info.get('sha256'):
                raise PolicyError('Checkpoint alterado após a avaliação.')
            selected[kind] = checkpoint
            break
    if set(selected) != {'policy', 'control', 'screen'}:
        raise PolicyError('Prepare os três cursos aprovados: investigação, leitura de controles e finalidade de telas.')
    return selected


class BrowserWorkspace:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store
        self.root = settings.home/'browser-sessions'
        self.root.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.sessions = {}
        # A restart never resumes a browser or credential automatically.
        for file in self.root.glob('*/session.json'):
            row = read_json(file)
            if row.get('state') in ('starting', 'busy', 'ready'):
                row.update(state='interrupted', error='Servidor reiniciado; abra uma nova sessão.')
                write_json(file, row)

    def _path(self, ident):
        if not isinstance(ident, str) or not re.fullmatch('[0-9a-f]{32}', ident):
            raise NotFoundError('Sessão não encontrada.')
        return self.root/ident

    def _owned(self, project_id, ident):
        self.store.project(project_id)
        path = self._path(ident)/'session.json'
        if not path.is_file():
            raise NotFoundError('Sessão não encontrada.')
        row = read_json(path)
        if row['project_id'] != project_id:
            raise NotFoundError('Sessão não encontrada neste projeto.')
        return row

    def list(self, project_id):
        self.store.project(project_id)
        with self.lock:
            rows = [read_json(p) for p in self.root.glob('*/session.json')]
            return sorted([r for r in rows if r['project_id'] == project_id], key=lambda r:r['created_at'], reverse=True)[:30]

    def get(self, project_id, ident):
        with self.lock:
            return self._owned(project_id, ident)

    def image(self, project_id, ident, frame):
        row = self.get(project_id, ident)
        if type(frame) is not int or not any(r['number'] == frame and r.get('file') for r in row['frames']):
            raise NotFoundError('Captura não encontrada.')
        path = self._path(ident)/f'{frame:03d}.png'
        raw = path.read_bytes()
        recorded = next(r for r in row['frames'] if r['number'] == frame)
        if hashlib.sha256(raw).hexdigest() != recorded['sha256']:
            raise PolicyError('Captura alterada após a execução.')
        return {'data': 'data:image/png;base64,'+base64.b64encode(raw).decode(), 'sha256': recorded['sha256']}

    def _save(self, row):
        # Hold self.lock. Atomic replacement avoids partially read progress.
        target = self._path(row['id'])/'session.json'
        temporary = target.with_suffix('.tmp')
        write_json(temporary, row)
        temporary.replace(target)

    def start(self, project_id, url, allow_network=False, asset_hosts=None, auth_hosts=None):
        self.store.project(project_id)
        if allow_network is not True:
            raise PolicyError('Autorize a conexão ao site para esta sessão.')
        asset_hosts = [] if asset_hosts is None else asset_hosts
        auth_hosts = [] if auth_hosts is None else auth_hosts
        if not isinstance(auth_hosts, list) or len(auth_hosts)>3 or any(not isinstance(h,str) or not re.fullmatch(r'[a-zA-Z0-9.-]{1,253}',h) for h in auth_hosts):
            raise PolicyError('Informe até três domínios de autenticação, sem caminhos.')
        if not isinstance(asset_hosts, list) or len(asset_hosts) > 8 or any(not isinstance(h, str) or not re.fullmatch(r'[a-zA-Z0-9.-]{1,253}', h) for h in asset_hosts):
            raise PolicyError('Informe até oito domínios de recursos, sem caminhos.')
        host = urlsplit(url).hostname or ''
        validate_url(url, [host])
        hosts = sorted(set([host]+[h.lower() for h in asset_hosts+auth_hosts]))
        for h in hosts: validate_url('https://'+h, hosts)
        models = selected_models(self.settings.home)
        with self.lock:
            if any(s['row']['state'] in ('starting', 'busy', 'ready') for s in self.sessions.values()):
                raise PolicyError('Encerre a sessão ativa antes de abrir outro navegador.')
            ident = uuid.uuid4().hex
            self._path(ident).mkdir()
            row = {'id':ident, 'project_id':project_id, 'url':url, 'state':'starting', 'created_at':utcnow(),
                   'frames':[], 'events':[], 'error':None, 'allSitesQualified':False,
                   'notice':'Exploração experimental de leitura. Não é um agente geral. Formulários ficam ocultos nas capturas.'}
            item = {'row':row, 'queue':queue.Queue(maxsize=1), 'stop':threading.Event(), 'name':'localauthor-live-'+ident,
                    'models':models, 'hosts':hosts, 'authHosts':sorted(set([host]+[h.lower() for h in auth_hosts])), 'deadline':time.monotonic()+1200}
            self.sessions[ident] = item
            self._save(row)
            thread = threading.Thread(target=self._run, args=(item,), daemon=True)
            item['thread'] = thread
            thread.start()
            return deepcopy(row)

    def act(self, project_id, ident, payload):
        with self.lock:
            row = self._owned(project_id, ident)
            action = payload.get('action')
            if action not in ('capture', 'link', 'back', 'scroll', 'explore', 'login', 'stop'):
                raise PolicyError('Ação não disponível.')
            item = self.sessions.get(ident)
            if not item or row['state'] not in ('starting', 'ready', 'busy'):
                raise PolicyError('Sessão encerrada. Abra uma nova sessão.')
            if action == 'stop':
                item['stop'].set()
                row.update(state='stopped', error=None)
                item['row'] = row
                self._save(row)
                return row
            if row['state'] != 'ready':
                raise PolicyError('Aguarde a ação atual terminar.')
            latest = row['frames'][-1] if row['frames'] else {}
            if payload.get('snapshot') != latest.get('snapshot') or not latest.get('snapshot'):
                raise PolicyError('Tela desatualizada. Atualize a captura antes de agir.')
            allowed = {'action', 'snapshot', 'target'} if action == 'link' else {'action', 'snapshot'}
            if action == 'login': allowed |= {'username', 'password'}
            if set(payload) != allowed:
                raise PolicyError('Campos não permitidos nesta ação.')
            if action == 'link' and not any(c['id'] == payload['target'] and c['safe'] for c in latest['controls']):
                raise PolicyError('Destino não foi observado como navegação disponível.')
            if action == 'login':
                if not latest.get('loginAvailable'):
                    raise PolicyError('Não há formulário de login compatível nesta tela.')
                if any(not isinstance(payload.get(k), str) or not 1 <= len(payload[k]) <= 256 for k in ('username', 'password')):
                    raise PolicyError('Preencha usuário e senha no formulário separado.')
            row.update(state='busy', error=None)
            item['row'] = row
            self._save(row)
            item['queue'].put_nowait(deepcopy(payload))  # Ephemeral; never saved in events/database.
            return deepcopy(row)

    def _run(self, item):
        row, name = item['row'], item['name']
        process = None
        output = self._path(row['id'])
        try:
            pins = {h:public_addresses(h)[0] for h in item['hosts']}
            image = command(['docker','image','inspect','localauthor-functional-lab:1','--format','{{.Id}}']).stdout.strip()
            with tempfile.TemporaryDirectory(prefix='localauthor-live-') as folder:
                source = Path(folder)
                for kind, path in item['models'].items(): shutil.copyfile(path, source/(kind+'.npz'))
                write_json(source/'job.json', {'url':row['url'], 'hosts':item['hosts'], 'authHosts':item['authHosts']})
                args = ['docker','create','--name',name,'--network','bridge','--read-only','--user','10001:10001',
                        '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','2g','--cpus','2','--pids-limit','256',
                        '--tmpfs','/tmp:rw,nosuid,nodev,size=512m,mode=1777','--shm-size','128m',
                        '--mount',f'type=bind,source={source},target=/input,readonly',
                        '--mount',f'type=bind,source={Path(__file__).resolve().parent},target=/runtime/src/localauthor,readonly',
                        '--mount',f'type=bind,source={output},target=/output',
                        '--env','HOME=/tmp','--env','PYTHONDONTWRITEBYTECODE=1','--entrypoint','sleep']
                for h, address in pins.items(): args += ['--add-host',h+':'+address]
                command(args+[image,'1250'])
                config = json.loads(command(['docker','inspect',name]).stdout)[0]
                h = config['HostConfig']
                mounts = {m['Destination']:m['RW'] for m in config['Mounts'] if m['Type']=='bind'}
                if not (h['ReadonlyRootfs'] and not h['Privileged'] and not h['Devices'] and not h['PortBindings']
                        and h['NetworkMode']=='bridge' and config['Config']['User']=='10001:10001'
                        and 'ALL' in h['CapDrop'] and 'no-new-privileges' in h['SecurityOpt']
                        and mounts=={'/input':False, '/runtime/src/localauthor':False, '/output':True}
                        and h['Memory']==2*1024**3 and h['NanoCpus']==2_000_000_000 and h['PidsLimit']==256):
                    raise PolicyError('Sandbox de navegador não verificada.')
                command(['docker','start',name])
                probe="import os,pathlib; s=pathlib.Path('/proc/self/status').read_text(); assert os.getuid()==10001 and 'CapEff:\\t0000000000000000' in s and 'NoNewPrivs:\\t1' in s and 'Seccomp:\\t2' in s"
                command(['docker','exec',name,'python3','-c',probe])
                write_json(output/'runtime.json', {'image':image, 'sandboxVerified':True, 'hosts':item['hosts'],
                           'models':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in item['models'].items()}})
                process = subprocess.Popen(['docker','exec','-i',name,'node','/runtime/src/localauthor/live_browser.cjs'],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                events = queue.Queue(maxsize=100)
                def read_events():
                    for line in process.stdout:
                        if len(line) > 500000: break
                        try: events.put(json.loads(line), timeout=1)
                        except (ValueError, queue.Full): break
                    try: events.put({'kind':'exit'}, timeout=1)
                    except queue.Full: pass
                threading.Thread(target=read_events, daemon=True).start()
                while not item['stop'].is_set() and time.monotonic() < item['deadline']:
                    try:
                        payload = item['queue'].get_nowait()
                        process.stdin.write(json.dumps(payload)+'\n')
                        process.stdin.flush()
                        payload.clear()
                    except queue.Empty: pass
                    try: event = events.get(timeout=.2)
                    except queue.Empty: continue
                    if event.get('kind') == 'exit':
                        raise PolicyError('Navegador encerrou a sessão.')
                    with self.lock:
                        row = item['row']
                        if event.get('kind') == 'frame':
                            frame = event['frame']
                            if frame.get('file'):
                                if frame['file'] != f"{frame['number']:03d}.png": raise PolicyError('Artefato inválido.')
                                raw = (output/frame['file']).read_bytes()
                                if not raw.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(raw).hexdigest()!=frame['sha256']:
                                    raise PolicyError('Captura não verificada.')
                            row['frames'].append(frame)
                        elif event.get('kind') == 'ready': row['state'] = 'ready'
                        elif event.get('kind') == 'error':
                            row['state'] = 'ready' if row['frames'] else 'failed'
                            row['error'] = event.get('message', 'Ação não concluída.')[:300]
                        if len(row['frames']) > 60: raise PolicyError('Limite de 60 observações atingido.')
                        row['events'] = (row['events']+[{'at':utcnow(), 'kind':event.get('kind'), 'action':event.get('action')}])[-100:]
                        self._save(row)
        except Exception:
            with self.lock:
                row = item['row']
                if not item['stop'].is_set():
                    row.update(state='failed', error=row.get('error') or 'Não foi possível executar o navegador. Verifique Docker, modelos e conexão. Nenhuma execução no host foi usada.')
                    self._save(row)
        finally:
            try: command(['docker','rm','-f',name], timeout=15)
            except (OSError, subprocess.SubprocessError): pass
            if process:
                if process.poll() is None: process.kill()
                process.wait(timeout=5)
            with self.lock:
                row = item['row']
                if row['state'] not in ('failed', 'stopped'):
                    row.update(state='stopped', error='Sessão encerrada ou limite de 20 minutos atingido.')
                self._save(row)
                while not item['queue'].empty(): item['queue'].get_nowait().clear()

    def close(self):
        for item in self.sessions.values(): item['stop'].set()
        for item in self.sessions.values(): item['thread'].join(timeout=20)
