"""Optional server-to-server HTTPS relay and outbound-only LAN pull worker.

Run behind an HTTPS reverse proxy on the website host. Keys belong in the
backend's environment, never in a public page or the model prompt.
"""
import argparse
import contextlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .errors import ConflictError, PolicyError
from .foundation.leads import LeadService, validate_event
from .foundation.marketing_workflow import canonical, fingerprint
from .research import validate_url, public_addresses, PinnedHTTPSConnection
from .util import utcnow
from .foundation.runtime import check_cancel


class RelayQueue:
    def __init__(self, path, queue_id):
        if not re.fullmatch(r'[a-f0-9]{32}', queue_id):raise PolicyError('Use um UUID hexadecimal de fila, com 32 caracteres.')
        self.path, self.queue_id = Path(path), queue_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('CREATE TABLE IF NOT EXISTS identity(id TEXT PRIMARY KEY); CREATE TABLE IF NOT EXISTS events(source TEXT,event_id TEXT,payload TEXT,digest TEXT,acked INTEGER,at TEXT,PRIMARY KEY(source,event_id));')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT id FROM identity').fetchone()
            if row and row[0] != queue_id:raise ConflictError('Este banco pertence a outra fila.')
            db.execute('INSERT OR IGNORE INTO identity VALUES(?)', (queue_id,))

    @contextlib.contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:yield connection
        finally:connection.close()

    def put(self, event):
        event = validate_event(event); raw = canonical(event); digest = fingerprint(event)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT digest FROM events WHERE source=? AND event_id=?', (event['source'], event['event_id'])).fetchone()
            if row:
                if row[0] != digest:raise ConflictError('Evento repetido com conteúdo diferente.')
                return {'accepted': True, 'deduplicated': True}
            count, used = db.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(payload AS BLOB))),0) FROM events').fetchone()
            if count >= 20000 or used + len(raw.encode('utf-8')) > 64_000_000:raise PolicyError('Fila cheia. Nenhum evento foi descartado; revise o armazenamento.')
            db.execute('INSERT INTO events VALUES(?,?,?,?,0,?)', (event['source'], event['event_id'], raw, digest, utcnow()))
        return {'accepted': True, 'deduplicated': False}

    def pending(self):
        with self.connect() as db:
            rows = db.execute('SELECT payload,digest FROM events WHERE acked=0 ORDER BY rowid LIMIT 20').fetchall()
        return {'queue_id': self.queue_id, 'events': [{'event': json.loads(r[0]), 'digest': r[1]} for r in rows]}

    def ack(self, source, event_id, digest):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT digest FROM events WHERE source=? AND event_id=?', (source, event_id)).fetchone()
            if not row or not hmac.compare_digest(row[0], digest):raise ConflictError('Recibo não corresponde ao evento.')
            db.execute('UPDATE events SET acked=1 WHERE source=? AND event_id=?', (source, event_id))
        return {'acknowledged': True}


def relay_handler(queue, write_key, read_key):
    if any(not isinstance(k, str) or len(k) < 32 or re.search(r'\s', k) for k in (write_key, read_key)) or hmac.compare_digest(write_key, read_key):
        raise PolicyError('Configure duas chaves diferentes, aleatórias e com pelo menos 32 caracteres.')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):pass
        def setup(self):
            super().setup(); self.connection.settimeout(10)
        def respond(self, code, data):
            raw = canonical(data).encode('utf-8')
            self.send_response(code);self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store');self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(raw)));self.end_headers();self.wfile.write(raw)
        def handle_route(self, method):
            try:
                if self.path not in ('/events', '/pending', '/ack'):
                    return self.respond(404, {'error': 'Rota não encontrada.'})
                key = write_key if self.path == '/events' else read_key
                if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + key).encode()):
                    return self.respond(401, {'error': 'Autenticação obrigatória.'})
                if method == 'GET' and self.path == '/pending':return self.respond(200, queue.pending())
                if method != 'POST' or self.path == '/pending':return self.respond(405, {'error': 'Método não permitido.'})
                if (self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1
                        or self.headers.get_content_type() != 'application/json'):raise PolicyError('Use JSON com tamanho explícito.')
                size = int(self.headers['Content-Length'])
                if not 1 <= size <= 16000:raise PolicyError('Evento excede limite de bytes.')
                raw = self.rfile.read(size)
                if len(raw) != size:raise PolicyError('Evento incompleto.')
                body = json.loads(raw)
                if self.path == '/events':result = queue.put(body)
                else:
                    if not isinstance(body, dict) or set(body) != {'source', 'event_id', 'digest'}:raise PolicyError('Recibo inválido.')
                    if any(not isinstance(v, str) for v in body.values()):raise PolicyError('Recibo inválido.')
                    result = queue.ack(body['source'], body['event_id'], body['digest'])
                self.respond(200, result)
            except ConflictError:self.respond(409, {'error': 'Evento ou recibo em conflito; confira a origem.'})
            except (PolicyError, ValueError, TypeError, KeyError, UnicodeError):self.respond(400, {'error': 'Dados de entrada inválidos ou fila cheia.'})
            except (OSError, TimeoutError):pass
            except Exception:self.respond(500, {'error': 'Falha interna; evento não confirmado.'})
        def do_GET(self):self.handle_route('GET')
        def do_POST(self):self.handle_route('POST')
    return Handler


class RelayTransport:
    def __init__(self, url, key):
        parsed = urlsplit(url)
        validate_url(url, [parsed.hostname or ''])
        if parsed.path not in ('', '/') or parsed.query:raise PolicyError('Use somente a origem HTTPS pública do relay.')
        if not isinstance(key, str) or len(key) < 32 or re.search(r'\s', key):raise PolicyError('Chave de leitura inválida.')
        self.host, self.key = parsed.hostname, key
    def call(self, path, body=None):
        addresses = public_addresses(self.host)
        conn = PinnedHTTPSConnection(self.host, addresses[0])
        try:
            conn.request('POST' if body is not None else 'GET', path,
                canonical(body).encode('utf-8') if body is not None else None,
                {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
            response = conn.getresponse(); raw = response.read(500001)
            if response.status != 200 or len(raw) > 500000:raise PolicyError('Relay não confirmou a operação; não houve confirmação local do recibo.')
            return json.loads(raw)
        finally:conn.close()


def sync_once(service, project, queue_id, transport, cancel=None):
    service.store.project(project)
    if not re.fullmatch(r'[a-f0-9]{32}', queue_id):raise PolicyError('Identidade de fila inválida.')
    with service.store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS lead_relay_bindings(queue_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id))')
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT project_id FROM lead_relay_bindings WHERE queue_id=?', (queue_id,)).fetchone()
        if row and row[0] != project:raise ConflictError('Esta fila já pertence a outro projeto local.')
        db.execute('INSERT OR IGNORE INTO lead_relay_bindings VALUES(?,?)', (queue_id, project))
    check_cancel(cancel)
    result = transport.call('/pending')
    check_cancel(cancel)
    if not isinstance(result, dict) or set(result) != {'queue_id', 'events'} or result['queue_id'] != queue_id:
        raise PolicyError('O relay retornou a identidade errada. Nenhum lead importado.')
    if not isinstance(result['events'], list) or len(result['events']) > 20:raise PolicyError('Lote remoto inválido.')
    # Validate the whole batch before importing any element.
    for row in result['events']:
        if not isinstance(row, dict) or set(row) != {'event', 'digest'}:raise PolicyError('Evento remoto inválido.')
        event = validate_event(row['event'])
        if fingerprint(event) != row['digest']:raise PolicyError('Hash do evento não confere.')
    receipts = []
    for row in result['events']:
        check_cancel(cancel)
        event = row['event']; imported = service.ingest(project, event)
        if imported['event_digest'] != row['digest']:raise PolicyError('O recibo local diverge do evento remoto; confirmação bloqueada.')
        check_cancel(cancel)
        ack = transport.call('/ack', {k: event[k] for k in ('source', 'event_id')} | {'digest': row['digest']})
        if ack != {'acknowledged': True}:raise PolicyError('Recibo remoto não confirmado. A próxima consulta será deduplicada.')
        receipts.append({'id': imported['id'], 'deduplicated': imported['deduplicated']})
    return {'received': len(receipts), 'receipts': receipts, 'sent_messages': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve');serve.add_argument('--database', type=Path, required=True)
    serve.add_argument('--queue-id', required=True);serve.add_argument('--port', type=int, default=8848)
    pull = sub.add_parser('pull');pull.add_argument('--home', type=Path, required=True)
    pull.add_argument('--project-id', required=True);pull.add_argument('--queue-id', required=True)
    pull.add_argument('--url', required=True);pull.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    if args.command == 'serve':
        queue = RelayQueue(args.database, args.queue_id)
        handler = relay_handler(queue, os.environ.get('LOCALAUTHOR_RELAY_WRITE_KEY'), os.environ.get('LOCALAUTHOR_RELAY_READ_KEY'))
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
        print('Relay restrito a loopback. Para internet, configure proxy HTTPS e chaves apenas no backend.', flush=True)
        try:server.serve_forever()
        finally:server.server_close()
    else:
        from .config import Settings
        from .store import Store
        settings = Settings.load(args.home)
        if settings.offline:raise PolicyError('Autorize rede na configuração do servidor antes de buscar eventos.')
        service = LeadService(Store(settings.home / 'memory.sqlite3', settings.max_store_bytes), None)
        transport = RelayTransport(args.url, os.environ.get('LOCALAUTHOR_RELAY_READ_KEY'))
        while True:
            try:print(canonical(sync_once(service, args.project_id, args.queue_id, transport)), flush=True)
            except Exception:
                print('Sincronização não confirmada; originais preservados. Confira serviço, rede e configuração.', flush=True)
                if not args.watch:raise PolicyError('Sincronização interrompida; nenhum erro foi convertido em sucesso.') from None
            if not args.watch:break
            time.sleep(30)


if __name__ == '__main__':main()
