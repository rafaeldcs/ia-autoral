"""Project-scoped, evidence-based screen memory. Never executes page instructions."""
from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .errors import PolicyError, NotFoundError
from .research import validate_url
from .safety import reject_secrets
from .util import utcnow, sha256


SCHEMA = """
CREATE TABLE IF NOT EXISTS investigations(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 name TEXT NOT NULL, origin TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS investigation_screens(
 investigation_id TEXT NOT NULL REFERENCES investigations(id), screen_key TEXT NOT NULL,
 source_id TEXT REFERENCES sources(id) ON DELETE CASCADE,
 name TEXT NOT NULL, url TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL,
 observed_at TEXT, PRIMARY KEY(investigation_id,screen_key));
"""
STOP_WORDS = set('a o os as de da do das dos em no na nos nas para por com um uma que qual quais como onde quero ver saber sistema tela telas sobre me mostre posso consigo encontrar acompanhar'.split())


def terms(text):
    plain = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    return {word.removesuffix('s') for word in re.findall(r'[^\W_]{3,}', plain) if word not in STOP_WORDS}


class InvestigationService:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        with store.connect() as db:
            db.executescript(SCHEMA)

    def _text(self, value, maximum=2000, *, empty=False):
        if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
            raise PolicyError('Texto de investigação inválido.')
        reject_secrets(value)
        if self.settings.token in value or re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', value, re.I):
            raise PolicyError('Não inclua credenciais ou endereços pessoais na memória de telas.')
        return value.strip()

    def _url(self, url, origin):
        parsed = validate_url(url, [urlsplit(origin).hostname])
        if f'{parsed.scheme}://{parsed.netloc}' != origin:
            raise PolicyError('A tela deve pertencer à origem autorizada.')
        return url

    def create(self, project_id, name, origin):
        self.store.project(project_id)
        name = self._text(name, 120)
        if not isinstance(origin, str):
            raise PolicyError('Origem HTTPS inválida.')
        parsed = validate_url(origin, [urlsplit(origin).hostname or ''])
        if parsed.path not in {'', '/'} or parsed.query:
            raise PolicyError('Informe somente a origem HTTPS autorizada, sem caminho ou parâmetros.')
        origin = f'{parsed.scheme}://{parsed.netloc}'
        result = dict(id=uuid.uuid4().hex, project_id=project_id, name=name, origin=origin, created_at=utcnow())
        with self.store.connect() as db:
            if db.execute('SELECT count(*) FROM investigations WHERE project_id=?', (project_id,)).fetchone()[0] >= 50:
                raise PolicyError('Limite de investigações deste projeto atingido.')
            db.execute('INSERT INTO investigations VALUES(:id,:project_id,:name,:origin,:created_at)', result)
        self.store.audit('investigation.created', {'id': result['id'], 'project_id': project_id, 'origin': origin})
        return result

    def get(self, project_id, investigation_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM investigations WHERE id=? AND project_id=?', (investigation_id, project_id)).fetchone()
            if row is None:
                raise NotFoundError('Investigação não encontrada neste projeto.')
            screens = [dict(r) for r in db.execute('SELECT * FROM investigation_screens WHERE investigation_id=? ORDER BY name', (investigation_id,))]
        counts = {state: sum(s['state'] == state for s in screens) for state in ('observed', 'pending', 'blocked')}
        return {**dict(row), 'screens': screens, 'coverage': {**counts, 'discovered': len(screens),
                'all_system_screens_known': False}, 'credentials_stored': False, 'weights_updated': False,
                'observer_notice': 'Memória de observações fornecidas pelo navegador/operador; não prova navegação neural autônoma.'}

    def list(self, project_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM investigations WHERE project_id=? ORDER BY created_at DESC', (project_id,))]
        return [self.get(project_id, ident) for ident in ids]

    def observe(self, project_id, investigation_id, payload):
        investigation = self.get(project_id, investigation_id)
        allowed = {'name', 'url', 'notes', 'headings', 'buttons', 'fields', 'columns', 'tabs',
                   'observedAt', 'observer', 'snapshotHash', 'state', 'reason', 'mutationsPerformed'}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise PolicyError('Observação contém campos não permitidos. Não envie valores de formulários, cookies ou senhas.')
        name = self._text(payload.get('name'), 200)
        url = self._url(payload.get('url'), investigation['origin'])
        state = payload.get('state', 'pending')
        if state not in {'observed', 'pending', 'blocked'} or payload.get('mutationsPerformed', False) is not False:
            raise PolicyError('Somente investigação de leitura é aceita.')
        key = sha256((url + '\n' + name).encode())
        if len(investigation['screens']) >= 500 and not any(s['screen_key'] == key for s in investigation['screens']):
            raise PolicyError('Limite de telas atingido.')
        reason = self._text(payload.get('reason', ''), empty=state == 'observed')
        source = None
        observed_at = None
        if state == 'observed':
            observed_at = payload.get('observedAt')
            try:
                date = datetime.fromisoformat(observed_at)
                if date.tzinfo is None or (date - datetime.now(timezone.utc)).total_seconds() > 60:
                    raise ValueError()
            except (ValueError, TypeError):
                raise PolicyError('A observação precisa de data válida com fuso horário.')
            if not isinstance(payload.get('snapshotHash'), str) or not re.fullmatch('[a-f0-9]{64}', payload['snapshotHash']):
                raise PolicyError('A observação precisa do hash da captura que a originou.')
            evidence = {'name': name, 'url': url, 'notes': self._text(payload.get('notes')),
                        'observedAt': observed_at, 'observer': self._text(payload.get('observer'), 120),
                        'snapshotHash': payload['snapshotHash'], 'trusted_instructions': False,
                        'training_allowed': False}
            for field in ('headings', 'buttons', 'fields', 'columns', 'tabs'):
                values = payload.get(field, [])
                if not isinstance(values, list) or len(values) > 80:
                    raise PolicyError('Lista de controles inválida.')
                evidence[field] = [self._text(value, 240) for value in values]
            # Webpage instructions remain quoted data. No actions are inferred or executed.
            source = self.store.ingest(project_id, f'investigation:{investigation_id}:{key}',
                                       name, json.dumps(evidence, ensure_ascii=False, indent=2), kind='note', training_allowed=False)
        with self.store.connect() as db:
            db.execute('''INSERT INTO investigation_screens VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(investigation_id,screen_key) DO UPDATE SET source_id=excluded.source_id,
                state=excluded.state,reason=excluded.reason,observed_at=excluded.observed_at''',
                (investigation_id, key, source['id'] if source else None, name, url, state, reason, observed_at))
        return self.get(project_id, investigation_id)

    def answer(self, project_id, query):
        self._text(query, 1000)
        investigations = self.list(project_id)
        result = {'origin': 'investigation_memory', 'sources': [], 'history_used': False, 'weights_updated': False,
                  'notice': 'Leitura da memória de telas, com data e origem. Não navega agora, não executa ações e não altera pesos.'}
        if not investigations:
            return {**result, 'content': 'Este projeto ainda não tem um mapa de telas observado. Não posso afirmar como o sistema funciona sem evidência.'}
        current = investigations[0]
        tokens = terms(query)
        if tokens & {'mapa', 'cobertura', 'pendente', 'investigacao'}:
            counts = current['coverage']
            lines = [f"{current['name']}: {counts['observed']} telas observadas, {counts['pending']} pendentes e {counts['blocked']} bloqueadas.",
                     'Cobertura apenas das telas descobertas; não significa todas as telas possíveis.']
            lines += [f"• {s['name']} — {s['state']}" + (f": {s['reason']}" if s['reason'] else '') for s in current['screens']]
            return {**result, 'content': '\n'.join(lines)[:12000], 'coverage': counts}
        matches = []
        with self.store.connect() as db:
            rows = db.execute('''SELECT s.name,v.content FROM investigation_screens s JOIN sources src ON src.id=s.source_id
                JOIN versions v ON v.id=src.current_version WHERE s.investigation_id=? AND s.state='observed' ''', (current['id'],)).fetchall()
        for row in rows:
            data = json.loads(row['content'])
            title_tokens = terms(data['name'])
            body_tokens = terms(data['notes'] + ' ' + ' '.join(data['headings'] + data['buttons'] + data['fields'] + data['columns'] + data['tabs']))
            score = 5 * len(tokens & title_tokens) + len(tokens & body_tokens)
            if score:
                matches.append((score, data))
        matches.sort(key=lambda pair: (-pair[0], pair[1]['name']))
        if not matches:
            return {**result, 'content': 'Não encontrei evidência observada para esse pedido. Isso não prova que o recurso não existe. É necessário investigar essa tela.'}
        lines = []
        for _, data in matches[:3]:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['observedAt'])).total_seconds()
            lines += [data['name'], f"Observado em {data['observedAt']} por {data['observer']}.", data['notes']]
            for field, label in [('headings', 'Seções'), ('fields', 'Campos'), ('columns', 'Colunas'), ('tabs', 'Abas')]:
                if data[field]:
                    lines.append(label + ': ' + '; '.join(data[field]))
            if age > self.settings.cache_ttl_seconds:
                lines.append('Observação antiga: confira novamente antes de tratar como estado atual.')
            lines += ['Fonte: ' + data['url'], '']
            result['sources'].append({'title': data['name'], 'url': data['url']})
        return {**result, 'content': '\n'.join(lines)[:12000]}
