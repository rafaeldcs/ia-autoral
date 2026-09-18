"""Experimental learned purpose classification, with explicit authored decoding.

These are finite categories, NOT a generative language model or universal site
understanding. Site names/URLs are provenance and never classifier inputs.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from .investigation_text import encode, FEATURES
from .nn.tensor import Tensor, gelu, no_grad

PURPOSES = {
    'site': {
        'commerce': 'Sistema de gestão de comércio e operações de lojas.',
        'video': 'Plataforma para descobrir, assistir e organizar conteúdo em vídeo.',
        'projects': 'Sistema para organizar projetos, tarefas e trabalho de equipes.',
        'learning': 'Ambiente para estudar cursos, aulas e atividades de aprendizagem.',
        'reference': 'Site para consultar artigos, documentação e informações de referência.',
        'community': 'Espaço para conversas, publicações e interação entre participantes.',
        'unknown': 'Não tenho evidência suficiente para identificar a finalidade deste site.',
    },
    'screen': {
        'overview': 'Apresenta uma visão geral, resumos e acessos às áreas do sistema.',
        'catalog': 'Organiza produtos, categorias ou conjuntos de itens do catálogo.',
        'pricing': 'Trata de preços, regras de precificação e simulações de valores.',
        'import': 'Recebe arquivos ou acompanha a importação de dados.',
        'inventory': 'Acompanha quantidades, disponibilidade e reservas de estoque.',
        'suppliers': 'Reúne fornecedores e opções de abastecimento.',
        'media_library': 'Organiza arquivos de mídia, imagens e pastas.',
        'shipping': 'Acompanha entregas, fretes ou rotas de envio.',
        'orders': 'Consulta ou registra pedidos e acompanha suas situações.',
        'refunds': 'Acompanha solicitações de reembolso e devoluções.',
        'finance': 'Apresenta informações financeiras, movimentações, taxas ou saldos.',
        'people': 'Organiza cadastros de pessoas, clientes, usuários ou membros da equipe.',
        'marketing': 'Organiza promoções, campanhas e ações de divulgação.',
        'integrations': 'Reúne conexões com serviços, canais ou sistemas externos.',
        'support': 'Organiza ajuda, solicitações de suporte e atendimentos.',
        'analytics': 'Apresenta relatórios, métricas e análises de resultados.',
        'settings': 'Reúne opções de configuração e preferências do sistema.',
        'messages': 'Exibe conversas, mensagens ou modelos de comunicação.',
        'monitoring': 'Acompanha saúde operacional, incidentes, erros e desempenho técnico.',
        'audit': 'Mostra registros históricos de eventos ou alterações.',
        'forms': 'Permite estruturar formulários e seus campos.',
        'notifications': 'Exibe avisos e informações sobre notificações.',
        'crm': 'Organiza contatos comerciais, oportunidades e etapas de relacionamento.',
        'plans': 'Apresenta planos de serviço e os recursos de cada opção.',
        'retention': 'Acompanha cancelamentos ou ações de recuperação de clientes.',
        'video_feed': 'Apresenta conteúdo em vídeo para descoberta e navegação.',
        'video_search': 'Busca vídeos e permite explorar os resultados encontrados.',
        'video_playback': 'Reproduz um vídeo e apresenta controles de exibição.',
        'subscriptions': 'Reúne canais acompanhados e publicações relacionadas a eles.',
        'watch_history': 'Mostra o histórico de vídeos assistidos.',
        'playlists': 'Organiza coleções de vídeos salvos para assistir.',
        'video_publish': 'Permite enviar ou administrar vídeos e transmissões.',
        'project_board': 'Organiza tarefas por etapa, responsável ou sprint.',
        'lesson': 'Apresenta uma aula ou atividade de estudo.',
        'article': 'Apresenta um artigo ou documento para leitura.',
        'discussion': 'Apresenta tópicos, publicações e respostas de uma comunidade.',
        'authentication': 'Solicita identificação ou acesso à conta.',
        'unknown': 'Não consegui determinar a função desta tela com segurança.',
    },
}


def features(title, elements, encoder=2):
    if not isinstance(title, str) or not title.strip() or len(title) > 600:
        raise ValueError('Use a nonempty title of at most 600 characters.')
    if not isinstance(elements, list) or len(elements) > 100:
        raise ValueError('Split observations with more than 100 visible elements explicitly.')
    # Separate regions, no silent truncation. This pooling loses element order
    # and relationships; the model is not an HTML/visual-layout reasoner.
    body = np.mean([encode(text) for text in elements], axis=0) if elements else np.zeros(FEATURES)
    if encoder == 1:
        vector = 2 * encode(title) + body
    elif encoder == 2:
        # Distinct title/body channels let the learned layer consider context.
        vector = np.concatenate((encode(title), body))
    else:
        raise ValueError('Unsupported encoder.')
    return vector / max(float(np.linalg.norm(vector)), 1)


class SiteReader:
    def __init__(self, kind, seed=92126, encoder=2):
        if kind not in PURPOSES:
            raise ValueError('Unsupported purpose head.')
        if encoder not in (1, 2): raise ValueError('Unsupported encoder.')
        self.kind, self.labels, self.encoder = kind, tuple(PURPOSES[kind]), encoder
        rng = np.random.default_rng(seed)
        self.parameters = {
            'w1': Tensor(rng.normal(0, .05, (FEATURES * encoder, 64)), requires_grad=True),
            'b1': Tensor(np.zeros(64), requires_grad=True),
            'w2': Tensor(rng.normal(0, .1, (64, len(self.labels))), requires_grad=True),
            'b2': Tensor(np.zeros(len(self.labels)), requires_grad=True),
        }

    def forward(self, x):
        p = self.parameters
        return gelu(Tensor(x) @ p['w1'] + p['b1']) @ p['w2'] + p['b2']

    def predict(self, title, elements):
        with no_grad():
            logits = self.forward(features(title, elements, self.encoder)[None, :]).data[0]
        if not np.isfinite(logits).all():
            raise ValueError('Invalid weights: no interpretation available.')
        scores = np.exp(logits - logits.max())
        scores /= scores.sum()
        index = int(np.argmax(scores))
        label = self.labels[index]
        return {'label': label, 'score': float(scores[index]), 'calibrated': False,
                'description': PURPOSES[self.kind][label],
                'descriptionOrigin': 'authored_category_description',
                'classificationOrigin': 'own_neural_weights', 'authorizesAction': False}

    def metadata(self):
        return {'schema': 1, 'kind': self.kind, 'labels': list(self.labels),
                'encoder': ('investigation-text-v1-region-pooling-title2-v1' if self.encoder == 1
                            else 'investigation-text-v1-separate-title-body-v2'),
                'descriptionsHash': hashlib.sha256(json.dumps(PURPOSES[self.kind],
                    ensure_ascii=False, sort_keys=True).encode()).hexdigest()}

    def save(self, path):
        np.savez_compressed(path, metadata=np.array(json.dumps(self.metadata())),
                            **{k: p.data for k, p in self.parameters.items()})

    @classmethod
    def load(cls, path, kind):
        if Path(path).stat().st_size > 3_000_000:
            raise ValueError('Checkpoint exceeds budget.')
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data['metadata']))
            encoder = {'investigation-text-v1-region-pooling-title2-v1': 1,
                       'investigation-text-v1-separate-title-body-v2': 2}.get(meta.get('encoder'))
            result = cls(kind, encoder=encoder)
            if set(data.files) != set(result.parameters) | {'metadata'}:
                raise ValueError('Invalid checkpoint fields.')
            if json.loads(str(data['metadata'])) != result.metadata():
                raise ValueError('Checkpoint category/encoder mismatch.')
            for key, p in result.parameters.items():
                value = data[key]
                if value.shape != p.data.shape or not np.isfinite(value).all():
                    raise ValueError('Invalid checkpoint weights.')
                p.data[:] = value
        return result


def describe_site(bundle, site_model, screen_model):
    """Classify every supplied screen; unavailable screens stay unavailable.

    Caller supplies reviewed structural evidence, not credentials or row values.
    No LLM-generated prose or URL-specific answer substitution occurs here.
    """
    if site_model.kind != 'site' or screen_model.kind != 'screen':
        raise ValueError('Incorrect classifier roles.')
    if not isinstance(bundle, dict) or set(bundle) != {'name', 'screens'}:
        raise ValueError('Expected site name and structural screens only.')
    if not isinstance(bundle['name'], str) or not 1 <= len(bundle['name']) <= 200:
        raise ValueError('Invalid site name.')
    screens = bundle['screens']
    if not isinstance(screens, list) or not 1 <= len(screens) <= 500:
        raise ValueError('Supply 1..500 screens; no implicit truncation.')
    answers, vectors = [], []
    for screen in screens:
        required = {'id', 'name', 'url', 'state', 'observedAt', 'sourceKind', 'elements', 'reason'}
        if not isinstance(screen, dict) or set(screen) != required:
            raise ValueError('Only reviewed structural evidence fields are accepted.')
        if screen['state'] not in ('observed', 'blocked', 'pending'):
            raise ValueError('Unsupported observation state.')
        answer = {k: screen[k] for k in required - {'elements'}}
        if screen['state'] != 'observed':
            answer['prediction'] = None
            answer['response'] = 'Não verificada: ' + screen['reason']
        else:
            prediction = screen_model.predict(screen['name'], screen['elements'])
            vectors.append(features(screen['name'], screen['elements'], site_model.encoder))
            answer['prediction'] = prediction
            answer['response'] = prediction['description']
            answer['evidence'] = {'title': screen['name'], 'elements': list(screen['elements'])}
            answer['evidenceHash'] = hashlib.sha256(json.dumps(screen, ensure_ascii=False,
                sort_keys=True).encode()).hexdigest()
        answers.append(answer)
    if vectors:
        # Infer the site's purpose from the aggregate screen evidence, never its
        # brand or domain. Reuse the same learned head and normalized encoding.
        vector = np.mean(vectors, axis=0)
        vector /= max(float(np.linalg.norm(vector)), 1)
        with no_grad():
            logits = site_model.forward(vector[None, :]).data[0]
        if not np.isfinite(logits).all():
            raise ValueError('Invalid site prediction.')
        scores = np.exp(logits - logits.max()); scores /= scores.sum()
        label = site_model.labels[int(np.argmax(scores))]
        purpose = {'label': label, 'description': PURPOSES['site'][label],
                   'score': float(scores.max()), 'calibrated': False}
    else:
        purpose = {'label': 'unknown', 'description': PURPOSES['site']['unknown'],
                   'score': None, 'calibrated': False}
    return {'site': bundle['name'], 'purpose': purpose, 'screens': answers,
            'coverage': {state: sum(s['state'] == state for s in screens)
                         for state in ('observed', 'pending', 'blocked')},
            'allPossibleScreensKnown': False, 'allSitesQualified': False,
            'browserExecutedByModel': False, 'authoredDescriptions': True,
            'modelDecision': 'finite-category classification; not free-form understanding',
            'notice': 'Hipóteses experimentais. Descrições fixas escolhidas pelos pesos; '
                      'controles, resultados de ações e regras de negócio não foram comprovados.'}
