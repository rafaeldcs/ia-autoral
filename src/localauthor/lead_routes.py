"""Authenticated UI/integration routes; no anonymous public intake on the LAN app."""
from .errors import PolicyError, NotFoundError


def route(app, method, path, query, body):
    fields = query if method == 'GET' else body
    if not isinstance(fields.get('project_id'), str) or not 1 <= len(fields['project_id']) <= 120:
        raise PolicyError('Selecione um projeto válido.')
    if 'id' in fields and (not isinstance(fields['id'], str) or not 1 <= len(fields['id']) <= 80):
        raise PolicyError('Selecione um lead válido.')
    if method == 'GET':
        keys = {'project_id', 'id'} if path == '/api/leads/item' else {'project_id'}
        if set(query) != keys:raise PolicyError('Selecione projeto e lead quando necessário.')
        if path == '/api/leads/context':return app.leads.context(query['project_id'])
        if path == '/api/leads/relay':return app.lead_connections.get(query['project_id'])
        if path == '/api/leads':return app.leads.list(query['project_id'])
        if path == '/api/leads/item':return app.leads.get(query['project_id'], query['id'])
    elif method == 'POST':
        expected = {
            '/api/leads/context': {'project_id', 'expected', 'context'},
            '/api/leads/ingest': {'project_id', 'event'},
            '/api/leads/qualify': {'project_id', 'id', 'version', 'context_digest'},
            '/api/leads/review': {'project_id', 'id', 'version', 'context_digest', 'analysis_digest', 'reviewed'},
            '/api/leads/move': {'project_id', 'id', 'version', 'stage', 'note'},
            '/api/leads/reject': {'project_id', 'id', 'version', 'note'},
            '/api/leads/relay': {'project_id', 'url', 'queue_id', 'read_key', 'enabled'},
            '/api/leads/relay/disable': {'project_id'},
        }
        if path not in expected:raise NotFoundError('Rota de leads não encontrada.')
        if set(body) != expected[path]:raise PolicyError('Campos inválidos. Não envie credenciais no conteúdo.')
        project = body['project_id']
        if path == '/api/leads/relay':return app.lead_connections.save(project, body['url'], body['queue_id'], body['read_key'], body['enabled'])
        if path == '/api/leads/relay/disable':return app.lead_connections.disable(project)
        if path.endswith('/context'):return app.leads.save_context(project, body['expected'], body['context'])
        if path.endswith('/ingest'):return app.leads.ingest(project, body['event'])
        if path.endswith('/reject'):return app.leads.reject(project, body['id'], body['version'], body['note'])
        if path.endswith('/qualify'):
            item, _ = app.leads._snapshot(project, body['id'], body['version'], body['context_digest'])
            if item['stage'] == 'do_not_contact':raise PolicyError('Contato bloqueado; análise não agendada.')
            return {'job': app.jobs.submit('lead-qualify', body)}
        if path.endswith('/review'):return app.leads.review(project, body['id'], body['version'], body['context_digest'], body['analysis_digest'], body['reviewed'])
        if path.endswith('/move'):return app.leads.move(project, body['id'], body['version'], body['stage'], body['note'])
    raise NotFoundError('Rota de leads não encontrada.')
