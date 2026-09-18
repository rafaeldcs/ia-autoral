"""Original fictional lessons about interface purposes, not real-site content.

Definitions are finite and authored. No brand, URL, private map or answer from
the real-site audit is present in the training loader.
"""
from localauthor.site_reader import PURPOSES

SCREEN_LESSONS = {
    'overview': (
        'Visão geral;Resumo do sistema;Painel inicial;Página inicial administrativa;Dashboard de operação;Acessos rápidos;Resumo da operação;Painel administrativo',
        'Visão geral da operação;Resumo administrativo', 'Painel de visão geral;Resumo inicial da operação'),
    'catalog': (
        'Catálogo de produtos;Categorias de produtos;Combos de itens;Produtos cadastrados;Novo produto;Coleções do catálogo;Grupos de produtos;Lista de mercadorias',
        'Catálogo de itens;Gerenciar categorias', 'Produtos e categorias;Conjuntos de produtos'),
    'pricing': (
        'Precificação;Regras de preços;Simulador de preço;Cálculo de preços;Preço protegido;Margem na precificação;Tabela de preços;Política de precificação',
        'Simulação de preços;Calcular preço de venda', 'Precificação de itens;Regras de preço protegido'),
    'import': (
        'Importação de arquivos;Importar catálogo;Importar produtos;Acompanhar importações;Arquivo de importação;Enviar planilha de importação;Histórico de importações;Modelo de arquivo para importar',
        'Importação de registros;Importar planilha', 'Importação de produtos;Acompanhamento de importações'),
    'inventory': (
        'Estoque disponível;Inventário de produtos;Quantidades reservadas;Estoque externo;Saldo do estoque;Disponibilidade de mercadorias;Movimentação de estoque;Inventário',
        'Controle de estoque;Consultar disponibilidade', 'Estoque e reservas;Inventário de mercadorias'),
    'suppliers': (
        'Fornecedores;Cadastro de fornecedores;Fornecedores de dropshipping;Catálogo de fornecedores;Abastecimento por fornecedor;Novo fornecedor;Buscar fornecedores;Parceiros de fornecimento',
        'Consultar fornecedores;Gerenciar fornecedores', 'Lista de fornecedores;Fornecedores para abastecimento'),
    'media_library': (
        'Galeria de imagens;Biblioteca de arquivos;Pastas de imagens;Enviar imagens;Arquivos de mídia;Nova pasta de mídia;Imagens enviadas;Acervo de imagens',
        'Gerenciar imagens;Biblioteca de imagens', 'Galeria de arquivos;Organizar pastas de imagens'),
    'shipping': (
        'Entregas;Fretes;Rotas de entrega;Rastreamento de envio;Gerenciar entregas;Custos de frete;Envio de encomendas;Transportadoras e entregas',
        'Fretes de encomendas;Consultar rotas', 'Fretes e entregas;Rotas para entrega'),
    'orders': (
        'Pedidos;Novo pedido;Registrar pedido;Status dos pedidos;Lista de pedidos;Consultar pedidos;Pedidos recebidos;Vendas por pedido',
        'Histórico de pedidos;Gerenciar pedidos', 'Cadastro de pedido;Acompanhar pedidos'),
    'refunds': (
        'Reembolsos;Solicitações de reembolso;Devoluções;Estorno de compra;Gerenciar reembolsos;Reembolso solicitado;Status da devolução;Pós-venda de reembolsos',
        'Consultar reembolsos;Acompanhar devoluções', 'Gerenciamento de reembolsos;Reembolsos de compras'),
    'finance': (
        'Financeiro;Extrato financeiro;Saques;Taxas de pagamento;Margem financeira;Saldo e movimentações;Conta financeira;Recebimentos e despesas',
        'Resumo financeiro;Taxas dos provedores de pagamento', 'Movimentações financeiras;Financeiro e taxas'),
    'people': (
        'Clientes;Funcionários;Usuários;Membros da equipe;Permissões de usuários;Cadastrar cliente;Contatos e opt-in;Perfis de acesso',
        'Usuários internos;Cadastro de pessoas', 'Gerenciamento de funcionários;Lista de clientes'),
    'marketing': (
        'Promoções;Cupons;Campanhas de marketing;Peças de divulgação;Campanhas automáticas;Criar promoção;Anúncios e campanhas;Publicidade da loja',
        'Central de marketing;Novo cupom de desconto', 'Gestão de promoções;Campanhas de divulgação'),
    'integrations': (
        'Integrações;Integradores;Canais de venda;Conectar serviço externo;API personalizada;Conexões externas;Configurar conector;Serviços integrados',
        'Gerenciar integrações;Conexão com canais', 'Integrações com serviços;Canais integrados de venda'),
    'support': (
        'Ajuda e suporte;Chamados;Atendimentos;Central de atendimento;Solicitação de ajuda;Novo chamado;Sugestões e chamados;Suporte ao usuário',
        'Gerenciar atendimentos;Ajuda ao usuário', 'Central de suporte;Solicitações de atendimento'),
    'analytics': (
        'Relatórios;Análise de resultados;Métricas de desempenho;Indicadores de vendas;Conversão por etapa;Comissões e metas;Relatório de feedback;Desempenho da equipe',
        'Relatórios de resultados;Métricas de conversão', 'Análise de desempenho;Relatório de indicadores'),
    'settings': (
        'Configurações;Preferências;Opções do sistema;Configuração da loja;Configurações da central;Ajustes do aplicativo;Salvar configurações;Preferências da conta',
        'Configurações gerais;Opções da conta', 'Configuração do sistema;Ajustes da central'),
    'messages': (
        'Mensagens;Conversas;Central de mensagens;Histórico de mensagens;Templates de mensagens;Modelos de comunicação;Selecionar conversa;Caixa de mensagens',
        'Consultar conversas;Modelos de mensagens', 'Conversas e mensagens;Templates de comunicação'),
    'monitoring': (
        'Telemetria;Monitoramento operacional;Alertas operacionais;Resiliência das integrações;Endpoints lentos;Fila de erros;Incidentes de operação;Saúde dos serviços',
        'Central operacional;Circuitos e limites', 'Monitoramento de incidentes;Telemetria de serviços'),
    'audit': (
        'Logs de alterações;Histórico de eventos;Registros de auditoria;Eventos do sistema;Histórico de configuração;Logs de configuração;Ações registradas;Trilha de auditoria',
        'Consultar logs;Auditoria de alterações', 'Registro de eventos;Histórico de alterações'),
    'forms': (
        'Editor de formulário;Campos do formulário;Configuração do formulário;Adicionar campo;Estrutura de formulário;Criar formulário;Personalizar formulário;Tipos de campos',
        'Montar formulário;Editar campos', 'Formulário e campos;Configurar campos do formulário'),
    'notifications': (
        'Notificações;Avisos recentes;Alertas de notificação;Entregas de notificações;Central de avisos;Preferências de notificações;Notificações recebidas;Eventos de notificação',
        'Consultar notificações;Avisos do sistema', 'Histórico de notificações;Central de notificações'),
    'crm': (
        'CRM;Leads comerciais;Oportunidades comerciais;Funil de relacionamento;Novo lead;Etapas de negociação;Contatos comerciais;Pipeline comercial',
        'Gestão de leads;Relacionamento comercial', 'CRM de oportunidades;Funil comercial'),
    'plans': (
        'Planos e recursos;Planos de serviço;Assinatura do serviço;Comparar planos;Recursos por plano;Limites da assinatura;Plano contratado;Pacotes de assinatura',
        'Gerenciar planos;Opções de assinatura', 'Recursos dos planos;Planos disponíveis'),
    'retention': (
        'Cancelamentos;Recuperação de clientes;Reativação de clientes;Clientes cancelados;Retenção de clientes;Motivos de cancelamento;Reconquistar clientes;Jornada de recuperação',
        'Cancelamentos recentes;Clientes em recuperação', 'Cancelamentos e recuperação;Reativação de contas'),
    'video_feed': (
        'Vídeos recomendados;Feed de vídeos;Descobrir vídeos;Vídeos em destaque;Vídeos curtos;Shorts;Conteúdo em vídeo para assistir;Recomendações de vídeos',
        'Explorar vídeos;Feed de conteúdo em vídeo', 'Vídeos para descobrir;Lista de vídeos recomendados'),
    'video_search': (
        'Pesquisar vídeos;Resultados da busca de vídeos;Busca por canais e vídeos;Filtros da pesquisa de vídeos;Encontrar vídeo;Pesquisa de vídeos;Buscar vídeos por assunto;Vídeos encontrados na busca',
        'Resultados de vídeos;Pesquisar canais e vídeos', 'Busca de vídeos;Pesquisar conteúdo em vídeo'),
    'video_playback': (
        'Reproduzir vídeo;Player de vídeo;Pausar vídeo;Controles de reprodução;Legendas do vídeo;Assistindo ao vídeo;Tela de reprodução de vídeo;Velocidade de reprodução',
        'Exibição do vídeo;Controle de volume do vídeo', 'Reprodução de vídeo;Pausa e reprodução do vídeo'),
    'subscriptions': (
        'Canais inscritos;Inscrições em canais;Vídeos dos canais seguidos;Acompanhar canais;Canais que sigo;Publicações dos canais inscritos;Feed de inscrições;Gerenciar inscrições em canais',
        'Canais acompanhados;Inscrições de canais', 'Vídeos de canais inscritos;Lista de canais seguidos'),
    'watch_history': (
        'Histórico de vídeos assistidos;Vídeos vistos recentemente;Histórico de exibição;Conteúdo assistido;Lista de vídeos vistos;Consultar vídeos assistidos;Histórico de reprodução;Assistidos recentemente',
        'Histórico de vídeos;Vídeos já assistidos', 'Vídeos do histórico de exibição;Lista do conteúdo assistido'),
    'playlists': (
        'Playlists;Assistir mais tarde;Vídeos salvos;Coleções de vídeos;Lista de reprodução;Vídeos favoritos;Organizar playlist;Vídeos marcados para depois',
        'Gerenciar playlists;Coleção de vídeos salvos', 'Playlists de vídeos;Lista para assistir mais tarde'),
    'video_publish': (
        'Enviar vídeo;Publicar vídeo;Criar transmissão ao vivo;Meus vídeos publicados;Upload de vídeos;Gerenciar vídeos enviados;Estúdio de criação de vídeo;Conteúdo do criador',
        'Envio de vídeos;Administrar vídeos publicados', 'Enviar novo vídeo;Gerenciar transmissões ao vivo'),
    'project_board': (
        'Quadro Kanban;Sprint de tarefas;Backlog de projetos;Tarefas por responsável;Etapas do projeto;Quadro de atividades;Planejamento Scrum;Histórias da sprint',
        'Tarefas do projeto;Planejar sprint', 'Quadro de tarefas;Backlog da equipe'),
    'lesson': (
        'Aula do curso;Atividade de aprendizagem;Exercícios da aula;Estudar lição;Módulo do curso;Material de estudo;Avaliação de aprendizagem;Conteúdo da aula',
        'Lição do curso;Exercícios de estudo', 'Aula e exercícios;Atividade do curso'),
    'article': (
        'Artigo de referência;Documentação técnica;Página de manual;Texto enciclopédico;Guia de referência;Artigo para leitura;Manual de uso;Documento informativo',
        'Ler documentação;Consultar manual', 'Artigo informativo;Documento de referência'),
    'discussion': (
        'Tópico do fórum;Discussão da comunidade;Respostas da comunidade;Publicações de participantes;Comentários do fórum;Debate entre membros;Novo tópico;Mensagens do fórum',
        'Tópicos da comunidade;Discussão entre participantes', 'Fórum de discussão;Respostas ao tópico'),
    'authentication': (
        'Fazer login;Entrar na conta;Autenticação;Senha de acesso;Identificação do usuário;Iniciar sessão;Login necessário;Acesso à conta',
        'Autenticar usuário;Login da conta', 'Entrar com credenciais;Iniciar sessão de usuário'),
    'unknown': (
        'Continuar;Operação;Página sem conteúdo;Conteúdo não identificado;Texto indisponível;Tela vazia;Informação insuficiente;Área desconhecida',
        'Sem informação;Painel sem identificação', 'Dados insuficientes;Área não identificada'),
}

SITE_LESSONS = {
    'commerce': (
        'Produtos estoque pedidos;Catálogo clientes vendas;Lojas fretes financeiro;Pedidos pagamentos entregas;Comércio catálogo fornecedores;Vendas cupons produtos;Inventário preços fornecedores;Operação de loja e canais de venda',
        'Produtos pedidos financeiro;Lojas catálogo estoque', 'Gestão de loja produtos pedidos;Comércio vendas estoque'),
    'video': (
        'Vídeos canais playlists;Assistir vídeos e canais;Feed de vídeos curtos;Pesquisar vídeos e assistir;Histórico de vídeos e inscrições;Vídeos salvos e recomendações;Conteúdo em vídeo e transmissões;Reprodução canais vídeos',
        'Canais vídeos e conteúdo;Vídeos e histórico de exibição', 'Vídeos canais e inscrições;Assistir conteúdo e playlists'),
    'projects': (
        'Projetos tarefas sprints;Quadros de trabalho Kanban;Backlog Scrum responsáveis;Equipe tarefas e prazos;Projetos etapas e entregas;Planejamento de sprint;Gestão de tarefas e trabalho;Histórias do projeto e responsáveis',
        'Tarefas projetos e backlog;Sprints da equipe', 'Quadros de projetos e tarefas;Gestão de trabalho e sprint'),
    'learning': (
        'Cursos aulas e exercícios;Estudar módulos e atividades;Aprendizagem lições avaliações;Aulas material de estudo;Cursos e progresso de estudo;Estudar conteúdo de aulas;Exercícios avaliações lições;Ambiente de aprendizagem e cursos',
        'Aulas lições e exercícios;Cursos e material de estudo', 'Aprendizagem com aulas e atividades;Estudar cursos e lições'),
    'reference': (
        'Artigos documentação referência;Enciclopédia e artigos;Manuais de consulta;Documentos informativos;Documentação e guias;Base de referência técnica;Artigos de leitura e consulta;Informações enciclopédicas',
        'Artigos de documentação;Manuais e referência', 'Consulta de artigos e documentos;Referência e documentação'),
    'community': (
        'Fórum tópicos e respostas;Comunidade de participantes;Publicações comentários membros;Discussões e debates;Participantes respondem tópicos;Rede de conversas e publicações;Mensagens entre membros da comunidade;Interação de participantes no fórum',
        'Comunidade de discussão;Fórum de participantes', 'Tópicos comentários e comunidade;Discussões entre membros'),
    'unknown': (
        'Conteúdo não identificado;Página vazia;Informação indisponível;Sem conteúdo legível;Tela sem identificação;Não há informações;Conteúdo insuficiente;Área desconhecida',
        'Sem dados disponíveis;Informação insuficiente', 'Dados não identificados;Página sem informações'),
}


CORRECTIVE_LESSONS = {
    'video_feed': 'Explorar conteúdo em vídeo;Explorar canais e vídeos;Descoberta de vídeos;Exploração de vídeos;Navegar por vídeos;Explorar recomendações de vídeo',
    'overview': 'Lojas disponíveis;Escolher loja;Página inicial da operação;Resumo inicial de loja;Painel de lojas;Início administrativo',
    'finance': 'Fluxo de caixa;Fechamento de caixa;Lançamentos do caixa;Conferência financeira;Abertura de caixa;Caixa e recebimentos',
    'analytics': 'Relatório de mercadorias;Relatório de clientes cadastrados;Relatório de estoque disponível;Visão geral dos relatórios;Relatórios de catálogo;Relatórios de atendimento',
    'messages': 'Histórico do mensageiro;Conversas por aplicativo;Mensagens de aplicativo;Comunicação por chat;Chat e conversas;Histórico de comunicação',
    'marketing': 'Cupom promocional;Cupons de desconto;Desconto promocional;Novo desconto;Código de cupom;Campanha de descontos',
    'notifications': 'Avisos da aplicação;Avisos operacionais;Avisos de atualização;Lista de avisos;Painel de avisos;Avisos recebidos',
    'people': 'Listagem de clientes;Cadastro da equipe;Cadastros de usuários;Cadastros de clientes;Relação de pessoas;Clientes cadastrados',
    'project_board': 'Backlog de tarefas;Backlog de trabalho;Backlog Scrum;Planejar backlog;Sprint da equipe;Tarefas pendentes do backlog',
    'authentication': 'Credenciais de acesso;Entrar com usuário;Entrar com senha;Usar credenciais;Autenticar com credenciais;Informe credenciais',
    'shipping': 'Rotas de transporte;Consultar fretes;Planejar rotas;Rotas disponíveis;Rotas de distribuição;Trajetos de entrega',
    'monitoring': 'Circuitos de serviços;Limites operacionais;Circuitos de proteção;Limites de requisições;Circuitos e falhas;Circuitos abertos',
    'unknown': 'Painel sem dados;Área sem identificação;Página sem identificação;Não há identificação;Página sem descrição;Painel desconhecido;Dados sem identificação;Conteúdo não reconhecido;Informações insuficientes para análise;Área não reconhecida',
}

# Context contrasts have no brand names, private records or real screen copies.
# A shared title can describe different functions; visible body evidence matters.
CONTEXT_LESSONS = [
    ('Administração — mensageiro: visão geral', ['Conversas recentes', 'Modelos de mensagens', 'Chat'], 'messages'),
    ('Gestor — resumo das mensagens', ['Canais de comunicação', 'Conversas', 'Templates'], 'messages'),
    ('Painel de comunicação — visão geral', ['Mensagens enviadas', 'Conversas recebidas'], 'messages'),
    ('Visão geral do chat', ['Mensagens', 'Campanhas de comunicação', 'Contatos'], 'messages'),
    ('Administração — estoque: visão geral', ['Quantidades', 'Disponibilidade', 'Reservas'], 'inventory'),
    ('Administração — relatórios: visão geral', ['Métricas', 'Análise por período'], 'analytics'),
    ('Administração — visão geral', ['Resumo da operação', 'Escolher loja', 'Acessos rápidos'], 'overview'),
    ('Recomendações de clientes', ['Comissão de indicação', 'Clientes indicados', 'Planos'], 'marketing'),
    ('Gestão — recomendações comerciais', ['Comissões', 'Indicações', 'Clientes'], 'marketing'),
    ('Painel de indicações', ['Recomendador', 'Contas indicadas', 'Comissão'], 'marketing'),
    ('Indicar e recomendar', ['Pessoas indicadas', 'Comissão', 'Planos'], 'marketing'),
    ('Painel de recomendações', ['Canais', 'Vídeos recomendados', 'Assistir'], 'video_feed'),
    ('Gestão — pessoas', ['Nome', 'Cadastro', 'Membros da equipe'], 'people'),
    ('Visão do mensageiro', ['Conversas', 'Templates', 'Campanhas', 'Contatos'], 'messages'),
    ('Mensageiro: contatos', ['Lista de pessoas', 'Origem', 'Aceite para contato'], 'people'),
    ('Indicações comerciais', ['Recomendador', 'Comissão', 'Clientes indicados'], 'marketing'),
    ('Recomendações comerciais', ['Pessoas indicadas', 'Comissões', 'Plano contratado'], 'marketing'),
    ('Histórico de opiniões', ['Nome', 'Tipo', 'Urgência', 'Solicitações de atendimento'], 'support'),
    ('Feedback recebido', ['Descrição', 'Urgência', 'Nome', 'Tipo'], 'support'),
    ('Eventos da operação', ['Pedido alterado', 'Pagamento atualizado', 'Auditoria de eventos'], 'audit'),
    ('Histórico operacional', ['Situação atualizada', 'Registro de alteração', 'Data do evento'], 'audit'),
    ('Ativação de contas', ['Funil de entrada', 'Conversão', 'Jornadas por etapa'], 'analytics'),
    ('Análise de ativação', ['Coortes', 'Linha do tempo', 'Conversão por estágio'], 'analytics'),
    ('Relatório de itens', ['Indicadores de vendas', 'Análise de produtos'], 'analytics'),
    ('Relatório de inventário', ['Quantidades por período', 'Métricas de estoque'], 'analytics'),
    ('Relatório de cadastros', ['Indicadores por período', 'Análise de pessoas'], 'analytics'),
    ('Resumo de relatórios', ['Visão geral', 'Análises de resultados'], 'analytics'),
    ('Visão geral', ['Vídeos recomendados', 'Conteúdo para assistir'], 'video_feed'),
    ('Página inicial', ['Feed de vídeos', 'Vídeos em destaque'], 'video_feed'),
    ('Início', ['Assista conteúdo', 'Vídeos recomendados', 'Pesquisar'], 'video_feed'),
    ('Pesquisar', ['Vídeos encontrados', 'Resultados da busca'], 'video_search'),
    ('Histórico', ['Conversas do chat', 'Mensagens recebidas'], 'messages'),
    ('Histórico', ['Ações registradas', 'Alterações de configuração'], 'audit'),
    ('Histórico', ['Vídeos vistos', 'Conteúdo assistido'], 'watch_history'),
    ('Visão geral', ['Mensagens', 'Modelos de comunicação'], 'messages'),
    ('Recomendações', ['Comissões por indicações', 'Indicar novos clientes'], 'marketing'),
    ('Recomendações', ['Vídeos curtos', 'Canais para assistir'], 'video_feed'),
    ('Suporte', ['Preferências da central', 'Salvar opções'], 'settings'),
    ('Suporte', ['Lista de chamados', 'Atendimentos pendentes'], 'support'),
    ('Equipe de suporte', ['Perfis de acesso', 'Cadastro de atendentes'], 'people'),
    ('Configuração de feedback', ['Editor de formulário', 'Adicionar campos'], 'forms'),
    ('Histórico de feedback', ['Solicitações de ajuda', 'Sugestões recebidas'], 'support'),
    ('Operação: conexões', ['Conectar serviços', 'Integrações externas'], 'integrations'),
    ('Operação: histórico', ['Registros de eventos', 'Auditoria'], 'audit'),
    ('Ativação', ['Conversão por etapa', 'Indicadores de entrada'], 'analytics'),
]


def make_splits(corrective=False):
    splits = {s: [] for s in ('train', 'validation', 'test')}
    seen = set()
    for kind, lessons in (('site', SITE_LESSONS), ('screen', SCREEN_LESSONS)):
        if set(lessons) != set(PURPOSES[kind]):
            raise ValueError('Every category needs an explicit lesson and held-out checks.')
        for label, groups in lessons.items():
            for split, phrases in zip(splits, groups):
                for i, phrase in enumerate(phrases.split(';')):
                    key = (kind, phrase.casefold())
                    if key in seen:
                        raise ValueError('Exact phrase leakage across splits.')
                    seen.add(key)
                    splits[split].append({'id': f'{kind}-{label}-{split}-{i}',
                        'kind': kind, 'label': label, 'title': phrase, 'elements': []})
    if corrective:
        for i, (title, elements, label) in enumerate(CONTEXT_LESSONS):
            splits['train'].append({'id': f'context-contrast-{i}', 'kind': 'screen',
                                    'label': label, 'title': title, 'elements': elements})
        for label, phrases in CORRECTIVE_LESSONS.items():
            for i, phrase in enumerate(phrases.split(';')):
                key = ('screen', phrase.casefold())
                if key in seen:
                    raise ValueError('Corrective phrase overlaps the course.')
                seen.add(key)
                splits['train'].append({'id': f'correction-{label}-{i}', 'kind': 'screen',
                                       'label': label, 'title': phrase, 'elements': []})
        # Learn to consult body regions when the heading is generic. These are
        # synthetic recombinations within each split, not untouched new sites.
        for label, groups in SCREEN_LESSONS.items():
            train = groups[0].split(';')
            splits['train'].append({'id': f'namespace-{label}', 'kind': 'screen',
                'label': label, 'title': 'Administração — ' + train[0], 'elements': train[1:4]})
            for i, heading in enumerate(('Painel', 'Página', 'Área', 'Início')):
                splits['train'].append({'id': f'regions-{label}-{i}', 'kind': 'screen',
                    'label': label, 'title': heading, 'elements': train[i:i+3]})
            for split, group in (('validation', groups[1]), ('test', groups[2])):
                splits[split].append({'id': f'regions-{label}-{split}', 'kind': 'screen',
                    'label': label, 'title': 'Área atual', 'elements': group.split(';')})
    return splits
