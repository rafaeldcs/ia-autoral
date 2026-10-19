"""People, private project ownership and opaque, revocable browser sessions.

The LAN/device bearer remains a transport credential, never a person's identity.
Passwords and session secrets are not job payloads, model context or audit data.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
import unicodedata
import uuid
from pathlib import Path

from .errors import AccessDeniedError, AuthenticationError, ConflictError, NotFoundError, PolicyError, RateLimitError
from .safety import PathPolicy
from .util import utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile_users(
 id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','user')), active INTEGER NOT NULL,
 salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profile_sessions(
 digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES profile_users(id),
 expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS profile_attempts(
 key TEXT PRIMARY KEY, started INTEGER NOT NULL, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS project_owners(
 project_id TEXT PRIMARY KEY REFERENCES projects(id),
 user_id TEXT NOT NULL REFERENCES profile_users(id));
CREATE TABLE IF NOT EXISTS project_members(
 project_id TEXT NOT NULL REFERENCES projects(id), user_id TEXT NOT NULL REFERENCES profile_users(id),
 role TEXT NOT NULL CHECK(role IN ('reader','editor')), PRIMARY KEY(project_id,user_id));
CREATE TABLE IF NOT EXISTS profile_conversations(
 conversation_id TEXT PRIMARY KEY REFERENCES conversations(id),
 user_id TEXT NOT NULL REFERENCES profile_users(id));
"""
COOKIE_NAME = "la_profile"
SESSION_SECONDS = 12 * 60 * 60
_hash_slots = threading.BoundedSemaphore(2)


def _password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256 or not value.strip():
        raise PolicyError("Use uma senha de 12 a 256 caracteres, não apenas espaços.")
    return value.encode("utf-8")


def _derive(raw, salt):
    with _hash_slots:
        return hashlib.scrypt(raw, salt=bytes.fromhex(salt), n=2**17, r=8, p=1, maxmem=256*1024*1024).hex()


def _name(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 or any(ord(c)<32 or ord(c)==127 for c in value):
        raise PolicyError("Informe um nome de 1 a 80 caracteres.")
    return value.strip()


def _username(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,31}", value.strip().casefold()):
        raise PolicyError("Use de 3 a 32 letras sem acentos, números, ponto, hífen ou sublinhado no usuário.")
    return value.strip().casefold()


class IdentityService:
    def __init__(self, store, home):
        self.store, self.home = store, Path(home)
        self.lock = threading.RLock()
        # No directories or existing ownership are changed before first setup.
        self.workspace_base = self.home.parent / "LocalAuthor-Projects"
        with store.connect() as db:
            db.executescript(SCHEMA)

    @property
    def enabled(self):
        with self.store.connect() as db:
            return bool(db.execute("SELECT 1 FROM profile_users LIMIT 1").fetchone())

    def user(self, ident):
        if not isinstance(ident,str) or not re.fullmatch('[0-9a-f]{32}',ident):
            raise AuthenticationError('Perfil inválido. Entre novamente.')
        with self.store.connect() as db:
            row = db.execute("SELECT id,username,name,role,active,created_at FROM profile_users WHERE id=?", (ident,)).fetchone()
        if row is None or not row['active']:
            raise AuthenticationError("Entre novamente no seu perfil.")
        return dict(row)

    def workspace(self, user):
        return self.workspace_base / user['id']

    def public_user(self, user):
        return {**{k:user[k] for k in ('id','username','name','role','active')}, 'workspace':str(self.workspace(user))}

    def require_admin(self, user):
        if self.user(user['id'])['role'] != 'admin':
            raise AccessDeniedError("Somente o administrador pode gerenciar esta área.")

    def current(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            return None
        digest = hashlib.sha256(token.encode('ascii')).hexdigest()
        with self.store.connect() as db:
            row = db.execute("SELECT u.id,u.username,u.name,u.role,u.active FROM profile_sessions s "
                "JOIN profile_users u ON u.id=s.user_id WHERE s.digest=? AND s.expires>? AND u.active=1",
                (digest, int(time.time()))).fetchone()
        return dict(row) if row else None

    def _issue(self, db, user_id):
        now = int(time.time())
        db.execute("DELETE FROM profile_sessions WHERE expires<=?", (now,))
        if db.execute("SELECT count(*) FROM profile_sessions WHERE user_id=?", (user_id,)).fetchone()[0] >= 20:
            db.execute("DELETE FROM profile_sessions WHERE user_id=?", (user_id,))
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO profile_sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, now+SESSION_SECONDS))
        return token

    def bootstrap(self, username, name, password, *, local):
        if not local:
            raise AccessDeniedError("Crie o primeiro perfil no aplicativo desta máquina servidor.")
        username, name = _username(username), _name(name)
        salt = secrets.token_hex(16)
        derived = _derive(_password(password), salt)
        ident, now = uuid.uuid4().hex, utcnow()
        with self.lock, self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM profile_users LIMIT 1").fetchone():
                raise ConflictError("Os perfis já foram configurados. Entre na sua conta.")
            if db.execute("SELECT 1 FROM jobs WHERE state IN ('queued','running') LIMIT 1").fetchone():
                raise ConflictError("Aguarde as tarefas atuais terminarem antes de configurar os perfis.")
            db.execute("INSERT INTO profile_users VALUES(?,?,?,'admin',1,?,?,?)", (ident, username, name, salt, derived, now))
            db.execute("INSERT INTO project_owners SELECT id,? FROM projects", (ident,))
            db.execute("INSERT INTO profile_conversations SELECT id,? FROM conversations", (ident,))
            token = self._issue(db, ident)
        self.store.audit('identity.configured', {'user_id':ident})
        return self.user(ident), token

    def login(self, username, password, transport):
        # Invalid names still consume the device bucket; errors never enumerate accounts.
        normalized = username.strip().casefold() if isinstance(username,str) else ''
        normalized = normalized[:128]
        device = hashlib.sha256(str(transport).encode()).hexdigest()
        keys = [('device:'+device,20), ('login:'+hashlib.sha256((device+'|'+normalized).encode()).hexdigest(),6)]
        now = int(time.time())
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for key, limit in keys:
                row = db.execute("SELECT started,count FROM profile_attempts WHERE key=?", (key,)).fetchone()
                if row and now-row['started']<300 and row['count']>=limit:
                    raise RateLimitError("Muitas tentativas. Aguarde cinco minutos antes de tentar novamente.")
            for key, _ in keys:
                db.execute("INSERT INTO profile_attempts VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET "
                    "started=CASE WHEN ?-started>=300 THEN ? ELSE started END, "
                    "count=CASE WHEN ?-started>=300 THEN 1 ELSE count+1 END", (key,now,now,now,now))
            row = db.execute("SELECT * FROM profile_users WHERE username=?", (normalized,)).fetchone()
        raw = password.encode('utf-8') if isinstance(password,str) and len(password)<=256 else b''
        salt = row['salt'] if row else '00'*16
        candidate = _derive(raw, salt)
        if row is None or not row['active'] or not secrets.compare_digest(candidate,row['password_hash']):
            raise AuthenticationError("Usuário ou senha inválidos.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            fresh = db.execute("SELECT active,password_hash FROM profile_users WHERE id=?", (row['id'],)).fetchone()
            if not fresh['active'] or not secrets.compare_digest(fresh['password_hash'],candidate):
                raise AuthenticationError("Usuário ou senha inválidos.")
            for key, _ in keys:db.execute("DELETE FROM profile_attempts WHERE key=?", (key,))
            token = self._issue(db,row['id'])
        return self.user(row['id']),token

    def logout(self, token):
        if isinstance(token,str):
            with self.store.connect() as db:
                db.execute("DELETE FROM profile_sessions WHERE digest=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def users(self, actor, *, directory=False):
        if not directory:self.require_admin(actor)
        with self.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,username,name,role,active FROM profile_users "+
                ("WHERE active=1 " if directory else "")+"ORDER BY name,username")]

    def create_user(self, actor, username, name, password, role='user'):
        self.require_admin(actor)
        username, name = _username(username),_name(name)
        if role not in ('admin','user'):raise PolicyError("Papel de usuário inválido.")
        salt=secrets.token_hex(16);derived=_derive(_password(password),salt);ident=uuid.uuid4().hex
        with self.lock,self.store.connect() as db:
            if db.execute("SELECT 1 FROM profile_users WHERE username=?",(username,)).fetchone():
                raise ConflictError("Este nome de usuário já está cadastrado.")
            if db.execute("SELECT count(*) FROM profile_users").fetchone()[0]>=50:
                raise PolicyError("O servidor atingiu o limite de 50 perfis.")
            db.execute("INSERT INTO profile_users VALUES(?,?,?,?,1,?,?,?)",(ident,username,name,role,salt,derived,utcnow()))
        self.store.audit('identity.user-created',{'actor_id':actor['id'],'user_id':ident})
        return self.public_user(self.user(ident))

    def update_user(self, actor, ident, name, role, active, password=None):
        self.require_admin(actor)
        if not isinstance(ident,str) or not re.fullmatch('[0-9a-f]{32}',ident):raise PolicyError('Perfil inválido.')
        name=_name(name)
        if role not in ('admin','user') or type(active) is not bool:raise PolicyError("Perfil inválido.")
        salt=secrets.token_hex(16) if password is not None else None
        derived=_derive(_password(password),salt) if salt else None
        with self.lock,self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM profile_users WHERE id=?',(ident,)).fetchone()
            if old is None:raise NotFoundError('Perfil não encontrado.')
            if old['role']=='admin' and old['active'] and (role!='admin' or not active):
                if db.execute("SELECT count(*) FROM profile_users WHERE role='admin' AND active=1").fetchone()[0]<=1:
                    raise PolicyError('Mantenha pelo menos um administrador ativo.')
            db.execute('UPDATE profile_users SET name=?,role=?,active=? WHERE id=?',(name,role,int(active),ident))
            if salt:db.execute('UPDATE profile_users SET salt=?,password_hash=? WHERE id=?',(salt,derived,ident))
            # A reset, disable or role change invalidates every browser session.
            if salt or not active or old['role']!=role:
                db.execute('DELETE FROM profile_sessions WHERE user_id=?',(ident,))
        self.store.audit('identity.user-updated',{'actor_id':actor['id'],'user_id':ident})
        return {'updated':True}

    def change_password(self, actor, current_password, new_password):
        raw=_password(current_password);new=_password(new_password)
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM profile_users WHERE id=?',(actor['id'],)).fetchone()
        if not secrets.compare_digest(_derive(raw,row['salt']),row['password_hash']):
            raise AuthenticationError('Senha atual inválida.')
        salt=secrets.token_hex(16);derived=_derive(new,salt)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE profile_users SET salt=?,password_hash=? WHERE id=? AND password_hash=?',
                (salt,derived,actor['id'],row['password_hash'])).rowcount
            if changed!=1:raise ConflictError('O perfil mudou. Entre novamente.')
            db.execute('DELETE FROM profile_sessions WHERE user_id=?',(actor['id'],))
        return {'changed':True,'login_required':True}

    def project_role(self, user_id, project_id, db=None):
        if db is None:
            with self.store.connect() as connection:return self.project_role(user_id,project_id,connection)
        owner=db.execute('SELECT user_id FROM project_owners WHERE project_id=?',(project_id,)).fetchone()
        if owner and owner['user_id']==user_id:return 'owner'
        member=db.execute('SELECT role FROM project_members WHERE project_id=? AND user_id=?',(project_id,user_id)).fetchone()
        return member['role'] if member else None

    def require_project(self, actor, project_id, action='read', db=None):
        from .project_access import can_access_project
        if not isinstance(project_id,str) or not re.fullmatch('[0-9a-f]{32}',project_id):raise NotFoundError('Projeto não encontrado neste perfil.')
        self.user(actor['id'])
        role=self.project_role(actor['id'],project_id,db)
        if role is None:raise NotFoundError('Projeto não encontrado neste perfil.')
        if not can_access_project(role,action):raise AccessDeniedError('Seu acesso a este projeto não permite esta ação.')
        return role

    def projects(self, actor):
        with self.store.connect() as db:
            rows=db.execute("SELECT p.*,o.user_id AS owner_id,u.name AS owner_name,"
                "CASE WHEN o.user_id=? THEN 'owner' ELSE m.role END AS access "
                "FROM projects p JOIN project_owners o ON o.project_id=p.id JOIN profile_users u ON u.id=o.user_id "
                "LEFT JOIN project_members m ON m.project_id=p.id AND m.user_id=? "
                "WHERE o.user_id=? OR m.user_id=? ORDER BY p.created_at DESC",(actor['id'],)*4)
            return [dict(r) for r in rows]

    def add_project(self, actor, name, root=None, *, managed=False):
        if type(managed) is not bool:raise PolicyError('Opção de pasta inválida.')
        if managed:
            if root:raise PolicyError('A nova pasta é criada automaticamente; não informe outro caminho.')
            # Names are labels, never trusted path fragments.
            _name(name)
            slug=unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower()
            slug=re.sub('[^a-z0-9]+','-',slug).strip('-')[:40] or 'projeto'
            self.workspace_base.mkdir(parents=True,exist_ok=True)
            PathPolicy(self.workspace_base)
            workspace=self.workspace(actor);workspace.mkdir(exist_ok=True);PathPolicy(workspace)
            root=workspace/(slug+'-'+uuid.uuid4().hex[:8]);root.mkdir()
        try:
            if not isinstance(root,(str,Path)) or not str(root).strip():raise PolicyError('Informe uma pasta existente no servidor.')
            resolved=PathPolicy(Path(root)).root
        except (OSError,TypeError) as exc:
            raise PolicyError('Informe uma pasta existente e acessível no servidor.') from exc
        allowed=self.workspace(actor).resolve()
        if actor['role']!='admin' and (resolved==allowed or not resolved.is_relative_to(allowed)):
            raise AccessDeniedError('Use uma pasta dentro do seu espaço no servidor ou peça acesso a um projeto existente.')
        with self.store.connect() as db:
            for user in db.execute('SELECT id FROM profile_users WHERE id<>?',(actor['id'],)):
                other=(self.workspace_base/user['id']).resolve()
                if resolved.is_relative_to(other) or other.is_relative_to(resolved):
                    raise AccessDeniedError('Essa pasta pertence a outro espaço de usuário.')
            for project in db.execute('SELECT root FROM projects'):
                other=Path(project['root']).resolve()
                if resolved.is_relative_to(other) or other.is_relative_to(resolved):
                    raise ConflictError('Esta pasta já está vinculada a um projeto ou se sobrepõe a outro. Use o compartilhamento.')
        return self.store.add_project(name,str(resolved),owner_id=actor['id'])

    def members(self, actor, project_id):
        self.require_project(actor,project_id,'share')
        with self.store.connect() as db:
            rows=db.execute("SELECT u.id,u.username,u.name,u.active,'owner' AS access FROM project_owners o "
                "JOIN profile_users u ON u.id=o.user_id WHERE o.project_id=? UNION ALL "
                "SELECT u.id,u.username,u.name,u.active,m.role AS access FROM project_members m "
                "JOIN profile_users u ON u.id=m.user_id WHERE m.project_id=?",(project_id,project_id))
            return [dict(r) for r in rows]

    def share(self, actor, project_id, user_id, role):
        if role not in ('reader','editor','none'):raise PolicyError('Escolha somente leitura, edição ou remover acesso.')
        if not isinstance(user_id,str) or not re.fullmatch('[0-9a-f]{32}',user_id):raise PolicyError('Perfil inválido.')
        with self.lock,self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.require_project(actor,project_id,'share',db)
            target=db.execute('SELECT active FROM profile_users WHERE id=?',(user_id,)).fetchone()
            if target is None:raise NotFoundError('Perfil não encontrado.')
            if self.project_role(user_id,project_id,db)=='owner':raise PolicyError('O proprietário mantém o acesso ao projeto.')
            if role=='none':db.execute('DELETE FROM project_members WHERE project_id=? AND user_id=?',(project_id,user_id))
            else:
                if not target['active']:raise PolicyError('Este perfil está desativado.')
                db.execute('INSERT INTO project_members VALUES(?,?,?) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role',(project_id,user_id,role))
        self.store.audit('project.access-changed',{'actor_id':actor['id'],'project_id':project_id,'user_id':user_id,'role':role})
        return {'updated':True}
