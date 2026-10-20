"""Draft snapshots and read-only reconciliation of accepted chat requests.

Unsent drafts are private application data, never model context or training data.
Request recovery observes persisted work; it never replays a job or side effect.
"""
import json
import re

from .errors import AccessDeniedError, ConflictError, NotFoundError, PolicyError
from .identity_context import current_actor
from .util import utcnow

SCHEMA="""
CREATE TABLE IF NOT EXISTS chat_workspaces(
 actor TEXT PRIMARY KEY,project_id TEXT NOT NULL,conversation_id TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_drafts(
 actor TEXT NOT NULL,project_id TEXT NOT NULL,conversation_id TEXT NOT NULL,
 text TEXT NOT NULL,mode TEXT NOT NULL,pending TEXT,revision INTEGER NOT NULL,updated_at TEXT NOT NULL,
 PRIMARY KEY(actor,project_id,conversation_id));
"""
MODES={'auto','guide','knowledge','model','foundation','image','investigation','browser'}


def identifier(value, *, empty=False):
    if empty and value=='':return value
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise PolicyError('Identificador de recuperação inválido.')
    return value


class ChatRecovery:
    def __init__(self, app):
        self.app=app
        with app.store.connect() as db:db.executescript(SCHEMA)

    def actor(self):
        actor=current_actor.get()
        if self.app.identity.enabled:self.app.identity.user(actor)
        return actor or 'local'

    def scope(self, project_id, conversation_id='', *, action='read'):
        identifier(project_id);identifier(conversation_id,empty=True)
        actor=self.actor()
        if self.app.identity.enabled:
            self.app.identity.require_project(self.app.identity.user(actor),project_id,action)
        else:self.app.store.project(project_id)
        if conversation_id:self.app.chat.get(project_id,conversation_id)
        return actor

    def workspace(self):
        actor=self.actor()
        with self.app.store.connect() as db:
            row=db.execute('SELECT project_id,conversation_id,updated_at FROM chat_workspaces WHERE actor=?',(actor,)).fetchone()
        if not row:return {'selection':None}
        try:self.scope(row['project_id'],row['conversation_id'])
        except (NotFoundError,AccessDeniedError):return {'selection':None}
        return {'selection':dict(row)}

    def select(self, project_id, conversation_id=''):
        actor=self.scope(project_id,conversation_id)
        with self.app.store.connect() as db:
            db.execute('INSERT INTO chat_workspaces VALUES(?,?,?,?) ON CONFLICT(actor) DO UPDATE SET project_id=excluded.project_id,conversation_id=excluded.conversation_id,updated_at=excluded.updated_at',
                       (actor,project_id,conversation_id,utcnow()))
        return {'saved':True}

    def draft(self, project_id, conversation_id=''):
        actor=self.scope(project_id,conversation_id)
        with self.app.store.connect() as db:
            row=db.execute('SELECT text,mode,pending,revision,updated_at FROM chat_drafts WHERE actor=? AND project_id=? AND conversation_id=?',(actor,project_id,conversation_id)).fetchone()
        return {**dict(row),'pending':json.loads(row['pending']) if row['pending'] else None} if row else {'text':'','mode':'auto','pending':None,'revision':0,'updated_at':None}

    def save(self, project_id, conversation_id, text, mode, revision, pending=None):
        actor=self.scope(project_id,conversation_id,action='write')
        if not isinstance(text,str) or len(text)>8000 or len(text.encode('utf-8'))>32000:
            raise PolicyError('O rascunho aceita até 8.000 caracteres e 32.000 bytes.')
        if not isinstance(mode,str) or mode not in MODES or type(revision) is not int or revision<0:
            raise PolicyError('Versão ou modo de rascunho inválido.')
        if pending is not None:
            if not isinstance(pending,dict) or set(pending)!={'request_id','conversation_id','message','mode'}:
                raise PolicyError('Envio pendente inválido.')
            identifier(pending['request_id']);identifier(pending['conversation_id'])
            if not isinstance(pending['message'],str) or not 1<=len(pending['message'])<=8000 or not pending['message'].strip() or len(pending['message'].encode('utf-8'))>32000 or not isinstance(pending['mode'],str) or pending['mode'] not in MODES:
                raise PolicyError('Conteúdo do envio pendente inválido.')
            if conversation_id and pending['conversation_id']!=conversation_id:
                raise PolicyError('Envio pendente pertence a outra conversa.')
        with self.app.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT revision,text,pending FROM chat_drafts WHERE actor=? AND project_id=? AND conversation_id=?',(actor,project_id,conversation_id)).fetchone()
            if (old[0] if old else 0)!=revision:
                raise ConflictError('Há outra versão deste rascunho no servidor. Sua cópia local foi preservada; compare antes de substituir.')
            if (text or pending) and (not old or (not old['text'] and not old['pending'])) and db.execute("SELECT count(*) FROM chat_drafts WHERE actor=? AND (text<>'' OR pending IS NOT NULL)",(actor,)).fetchone()[0]>=200:
                raise PolicyError('Limite de 200 rascunhos por perfil. Sua cópia local continua disponível.')
            now=utcnow()
            db.execute('INSERT INTO chat_drafts VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(actor,project_id,conversation_id) DO UPDATE SET text=excluded.text,mode=excluded.mode,pending=excluded.pending,revision=excluded.revision,updated_at=excluded.updated_at',
                       (actor,project_id,conversation_id,text,mode,json.dumps(pending) if pending else None,revision+1,now))
        return {'saved':True,'revision':revision+1,'updated_at':now}

    def request(self, project_id, request_id):
        actor=self.scope(project_id);identifier(request_id)
        with self.app.store.connect() as db:
            row=db.execute('SELECT job_id FROM job_requests WHERE actor=? AND request_id=?',(actor,request_id)).fetchone()
        if not row:raise NotFoundError('Este envio ainda não foi confirmado pelo servidor. Ele não foi reenviado automaticamente.')
        job=self.app.jobs.get(row['job_id'])
        if job['kind']!='chat' or job['payload']['project_id']!=project_id:raise NotFoundError('Envio não encontrado neste projeto.')
        conversation=self.app.chat.get(project_id,job['payload']['conversation_id'])
        # A crash may occur after the conversation transaction commits but
        # before the worker changes the job state. Committed messages win.
        committed=any(m['role']=='assistant' and m['metadata'].get('request_id')==request_id for m in conversation['messages'])
        state='completed' if committed else job['state']
        return {'request_id':request_id,'job_id':job['id'],'state':state,'error':job['error'] if not committed else None,
                'conversation_id':conversation['id'],'result':conversation if state=='completed' else None}

    def route(self, method, path, query, body):
        data=query if method=='GET' else body
        if path=='/api/chat-workspace':
            if method=='GET':return self.workspace()
            if set(body)!={'project_id','conversation_id'}:raise PolicyError('Seleção inválida.')
            return self.select(**body)
        if path=='/api/chat-draft':
            if method=='GET':
                if set(query)!={'project_id','conversation_id'}:raise PolicyError('Selecione projeto e conversa do rascunho.')
                return self.draft(**query)
            if set(body)!={'project_id','conversation_id','text','mode','revision','pending'}:raise PolicyError('Rascunho inválido.')
            return self.save(**body)
        if path=='/api/chat-request' and method=='GET':
            if set(data)!={'project_id','request_id'}:raise PolicyError('Selecione projeto e envio.')
            return self.request(**data)
        raise NotFoundError('Rota de recuperação não encontrada.')
