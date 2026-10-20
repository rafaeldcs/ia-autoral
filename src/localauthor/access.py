"""HTTP and queued-work authorization. Unknown routes fail closed after setup."""
import json
import re

from .errors import AccessDeniedError, AuthenticationError, NotFoundError, PolicyError

PROJECT_GET = {
    '/api/marketing/campaigns','/api/marketing/campaign','/api/marketing/export',
    '/api/marketing/channels','/api/marketing/deliveries','/api/browser/sessions',
    '/api/browser/session','/api/browser/image','/api/foundation/image','/api/investigations',
    '/api/conversations','/api/conversation','/api/project-preferences',
    '/api/leads/context','/api/leads','/api/leads/item','/api/leads/relay',
    '/api/chat-draft','/api/chat-request',
}
PROJECT_POST = {
    '/api/voice/transcribe','/api/voice/cancel','/api/marketing/campaigns',
    '/api/marketing/brand','/api/marketing/style','/api/marketing/choice','/api/marketing/approve',
    '/api/marketing/connect','/api/marketing/disconnect','/api/marketing/preview','/api/marketing/publish',
    '/api/marketing/research','/api/marketing/generate','/api/marketing/plan','/api/marketing/brand-analysis',
    '/api/foundation/business-metrics','/api/foundation/marketing-metrics','/api/browser/start',
    '/api/browser/action','/api/investigations','/api/investigations/observe','/api/conversations',
    '/api/project-preferences','/api/chat','/api/tasks','/api/jobs/index','/api/symbols',
    '/api/leads/context','/api/leads/ingest','/api/leads/reject','/api/leads/qualify',
    '/api/leads/review','/api/leads/move','/api/leads/relay','/api/leads/relay/disable',
    '/api/chat-draft','/api/chat-workspace',
}
SCOPE_GET = {'/api/sources','/api/relations'}
SCOPE_POST = {'/api/consult','/api/import','/api/sources/delete','/api/relations','/api/jobs/research'}
ADMIN_GET = {'/api/diagnostics','/api/models'}
SHARED_GET = {'/api/health','/api/foundation/status','/api/voice/status','/api/engineering-report','/api/communication-report','/api/app/installer','/api/app/installer/file'}


class ProjectAccess:
    def __init__(self, app, user):
        self.app,self.user,self.identity = app,user,app.identity

    def scope(self, scope, action='read'):
        if scope=='global':self.identity.require_admin(self.user)
        else:self.identity.require_project(self.user,scope,action)

    def job_project(self, job):
        payload=job['payload']
        if payload.get('project_id'):return payload['project_id']
        if payload.get('task_id'):return self.app.tasks.get(payload['task_id'])['project_id']
        return payload.get('scope','global')

    def job(self, ident, action='read'):
        job=self.app.jobs.get(ident)
        self.scope(self.job_project(job),action)
        return job

    def authorize(self, method, path, q, body):
        if '_actor_id' in body:raise PolicyError('A identidade da solicitação é definida pelo servidor.')
        data=q if method=='GET' else body
        if (method=='GET' and path in PROJECT_GET) or (method=='POST' and path in PROJECT_POST):
            readonly=method=='GET' or path in {'/api/symbols','/api/foundation/business-metrics','/api/foundation/marketing-metrics','/api/chat-workspace'}
            self.identity.require_project(self.user,data.get('project_id'),'read' if readonly else 'write')
            return
        if (method=='GET' and path in SCOPE_GET) or (method=='POST' and path in SCOPE_POST):
            scope=data.get('scope','global')
            self.scope(scope,'read' if method=='GET' or path=='/api/consult' else 'write')
            if path=='/api/consult' and body.get('include_global') is True:self.identity.require_admin(self.user)
            return
        match=re.fullmatch(r'/api/jobs/([0-9a-f]{32})(/cancel)?',path)
        if match:
            self.job(match[1],'write' if method=='POST' else 'read');return
        match=re.fullmatch(r'/api/tasks/([0-9a-f]{32})(?:/(files|file|proposal|apply|reject|recover|feedback|verify))?',path)
        if match:
            self.identity.require_project(self.user,self.app.tasks.get(match[1])['project_id'],'read' if method=='GET' else 'write');return
        if method=='GET' and path in ADMIN_GET:
            self.identity.require_admin(self.user);return
        if method=='POST' and path=='/api/jobs/train':
            self.identity.require_admin(self.user);return
        if method=='GET' and path in SHARED_GET|{'/api/projects','/api/tasks','/api/jobs','/api/chat-workspace'}:return
        if method=='POST' and path=='/api/projects':return
        raise NotFoundError('Rota não encontrada neste perfil.')

    def dispatch(self, method, path, q, body, fallback):
        self.authorize(method,path,q,body)
        if path=='/api/projects':
            if method=='GET':return self.identity.projects(self.user)
            if set(body)-{'name','root','managed'}:raise PolicyError('Envie somente nome e opção da pasta do projeto.')
            return self.identity.add_project(self.user,body['name'],body.get('root'),managed=body.get('managed',False))
        if method=='GET' and path=='/api/jobs':
            result=[]
            with self.app.store.connect() as db:ids=[r[0] for r in db.execute('SELECT id FROM jobs ORDER BY created_at DESC')]
            for ident in ids:
                try:result.append(self.job(ident))
                except (AccessDeniedError,NotFoundError):continue
                if len(result)==50:break
            return result
        if method=='GET' and path=='/api/tasks':
            visible={p['id'] for p in self.identity.projects(self.user)}
            with self.app.store.connect() as db:
                ids=[r['id'] for r in db.execute('SELECT id,project_id FROM tasks ORDER BY created_at DESC') if r['project_id'] in visible][:100]
            return [self.app.tasks.get(ident) for ident in ids]
        result=fallback(method,path,q,body)
        if method=='GET' and path=='/api/health':
            result={**result,'stats':self.stats(),'profile_required':True}
        if method=='GET' and path=='/api/conversations':
            with self.app.store.connect() as db:
                authors={r['conversation_id']:dict(r) for r in db.execute('SELECT c.conversation_id,c.user_id,u.name FROM profile_conversations c JOIN profile_users u ON u.id=c.user_id')}
            result=[{**row,'created_by':authors.get(row['id'])} for row in result]
            if q.get('mine')=='1':result=[r for r in result if (r['created_by'] or {}).get('user_id')==self.user['id']]
        return result

    def stats(self):
        ids=[p['id'] for p in self.identity.projects(self.user)]
        scopes=ids+(['global'] if self.user['role']=='admin' else [])
        clause=','.join('?' for _ in scopes) or 'NULL'
        project_clause=','.join('?' for _ in ids) or 'NULL'
        with self.app.store.connect() as db:
            def count(sql,params):return db.execute(sql,params).fetchone()[0]
            return {'projects':len(ids),
                'sources':count(f'SELECT count(*) FROM sources WHERE scope IN ({clause})',scopes),
                'versions':count(f'SELECT count(*) FROM versions v JOIN sources s ON s.id=v.source_id WHERE s.scope IN ({clause})',scopes),
                'chunks':count(f'SELECT count(*) FROM chunks c JOIN versions v ON v.id=c.version_id JOIN sources s ON s.id=v.source_id WHERE s.scope IN ({clause})',scopes),
                'relations':count(f'SELECT count(*) FROM relations WHERE scope IN ({clause})',scopes),
                'tasks':count(f'SELECT count(*) FROM tasks WHERE project_id IN ({project_clause})',ids),
                'database_bytes':self.app.store.path.stat().st_size if self.user['role']=='admin' else 0}


def check_queued_job(app, payload):
    if not app.identity.enabled:return None
    actor=payload.get('_actor_id')
    if not actor:raise AuthenticationError('Tarefa sem perfil de origem; crie uma nova solicitação autenticada.')
    user=app.identity.user(actor)
    access=ProjectAccess(app,user)
    access.scope(access.job_project({'payload':payload}),'write')
    return user
