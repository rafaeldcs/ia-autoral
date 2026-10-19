"""Opt-in outbound relay polling. Credentials stay in server-user DPAPI, never jobs."""
import threading

from .errors import PolicyError
from .foundation.marketing_channels import WindowsVault
from .foundation.marketing_workflow import fingerprint
from .lead_relay import RelayTransport, sync_once
from .util import utcnow


class LeadConnections:
    def __init__(self, store, service, settings, *, vault=None, transport_factory=RelayTransport):
        self.store, self.service, self.settings = store, service, settings
        self.vault, self.transport_factory = vault or WindowsVault(), transport_factory
        self.stop = threading.Event();self.wakeup = threading.Event();self.lock = threading.RLock()
        self.active = {};self.thread = None
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS lead_connections(project_id TEXT PRIMARY KEY REFERENCES projects(id),
                queue_id TEXT NOT NULL UNIQUE,url TEXT NOT NULL,sealed_key TEXT NOT NULL,revision TEXT NOT NULL,
                enabled INTEGER NOT NULL,state TEXT NOT NULL,checked_at TEXT,received INTEGER NOT NULL)''')

    def get(self, project):
        self.store.project(project)
        with self.store.connect() as db:
            row = db.execute('SELECT project_id,queue_id,url,enabled,state,checked_at,received FROM lead_connections WHERE project_id=?', (project,)).fetchone()
        return {'connection': dict(row) if row else None, 'network_allowed': not self.settings.offline,
                'notice': 'Sincronização com backend HTTPS configurado; não conecta automaticamente contas Meta ou WhatsApp.'}

    def save(self, project, url, queue_id, read_key, enabled):
        self.store.project(project)
        if type(enabled) is not bool:raise PolicyError('Informe se a conexão deve ficar ativa.')
        import re
        if not isinstance(queue_id, str) or not re.fullmatch(r'[a-f0-9]{32}', queue_id):raise PolicyError('Identidade de fila inválida.')
        self.transport_factory(url, read_key)  # syntax validation only; production factory does no network here
        sealed = self.vault.seal(read_key)
        revision = fingerprint({'url': url, 'queue': queue_id, 'sealed': sealed, 'at': utcnow()})
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner = db.execute('SELECT project_id FROM lead_connections WHERE queue_id=?', (queue_id,)).fetchone()
            if owner and owner[0] != project:raise PolicyError('Esta fila já está conectada a outro projeto.')
            bound = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lead_relay_bindings'").fetchone()
            if bound:
                binding = db.execute('SELECT project_id FROM lead_relay_bindings WHERE queue_id=?', (queue_id,)).fetchone()
                if binding and binding[0] != project:raise PolicyError('A fila já foi vinculada a outro projeto e não pode ser redirecionada.')
            if project in self.active:self.active[project].set()
            db.execute('INSERT INTO lead_connections VALUES(?,?,?,?,?,?,?,NULL,0) ON CONFLICT(project_id) DO UPDATE SET queue_id=excluded.queue_id,url=excluded.url,sealed_key=excluded.sealed_key,revision=excluded.revision,enabled=excluded.enabled,state=excluded.state',
                       (project, queue_id, url, sealed, revision, int(enabled), 'waiting' if enabled else 'disabled'))
        self.wakeup.set();return self.get(project)

    def disable(self, project):
        self.store.project(project)
        with self.lock, self.store.connect() as db:
            if project in self.active:self.active[project].set()
            db.execute("UPDATE lead_connections SET enabled=0,state='disabled' WHERE project_id=?", (project,))
        return self.get(project)

    def sync(self, project):
        self.store.project(project)
        with self.lock:
            if self.stop.is_set():raise PolicyError('Sincronização em encerramento.')
            if project in self.active:raise PolicyError('Este projeto já está sincronizando.')
            with self.store.connect() as db:row = db.execute('SELECT * FROM lead_connections WHERE project_id=?', (project,)).fetchone()
            if not row or not row['enabled']:raise PolicyError('Conecte e ative a fila deste projeto.')
            cancel = threading.Event();self.active[project] = cancel
        state, received = 'error', 0
        try:
            if self.settings.offline:raise PolicyError('Rede desativada nas configurações do servidor.')
            key = self.vault.open(row['sealed_key'])
            transport = self.transport_factory(row['url'], key)
            result = sync_once(self.service, project, row['queue_id'], transport, cancel)
            state, received = 'ok', result['received']
        except Exception:
            state, received = 'offline' if self.settings.offline else 'error', 0
            # Do not persist transport exceptions: they may contain URLs, bodies or credentials.
        finally:
            with self.lock:
                self.active.pop(project, None)
                with self.store.connect() as db:
                    db.execute('UPDATE lead_connections SET state=?,checked_at=?,received=received+? WHERE project_id=? AND revision=? AND enabled=1',
                               (state, utcnow(), received, project, row['revision']))
        return self.get(project)

    def start(self):
        if self.thread:return
        self.thread = threading.Thread(target=self._run, daemon=True, name='localauthor-lead-sync');self.thread.start()

    def _run(self):
        while not self.stop.is_set():
            self.wakeup.clear()
            with self.store.connect() as db:projects = [r[0] for r in db.execute('SELECT project_id FROM lead_connections WHERE enabled=1')]
            for project in projects:
                if self.stop.is_set():break
                try:self.sync(project)
                except PolicyError:pass  # concurrent disable/sync; no private exception details logged
            self.wakeup.wait(30)

    def close(self):
        self.stop.set();self.wakeup.set()
        with self.lock:
            for cancel in self.active.values():cancel.set()
        if self.thread:self.thread.join(timeout=15)
        if self.thread and self.thread.is_alive():raise PolicyError('Coletor de leads ainda está encerrando; nenhum modelo foi liberado durante o fechamento.')
