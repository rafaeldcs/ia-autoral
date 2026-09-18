"""Original fictional UI examples. No customer/site data or external corpus.

Each line contains train / validation / audit phrases separated by |.
The held-out phrases are never used in feature fitting or gradient updates.
"""
COURSE = {
    'status': {
        'ready': (
            'Dados carregados com sucesso;Lista disponível;Consulta concluída;Tudo pronto para consulta;Nenhum erro encontrado;Sem falhas na consulta;Acesso autorizado;Não há problemas no carregamento;Carregamento concluído;Você pode consultar os dados;Registros disponíveis;Nenhuma falha encontrada;Sistema disponível;Dados atualizados;Operação concluída sem erros;Não houve erro;Os registros foram carregados;Consulta realizada com sucesso;A lista está pronta;Não ocorreu falha',
            'Carregamento realizado com sucesso;Não foram encontrados erros;Consulta pronta;Lista carregada sem falhas',
            'Dados disponíveis para consulta;Nenhum erro foi encontrado na consulta;Registros carregados com sucesso;A consulta foi concluída sem falhas'),
        'loading': (
            'Carregando dados;Aguarde o carregamento;Buscando registros;Consulta em andamento;Processando sua consulta;Aguarde enquanto buscamos os dados;Preparando a lista;Atualização em andamento;Ainda estamos carregando;Por favor aguarde;Estamos buscando resultados;A consulta ainda não terminou;Carregamento não concluído;Preparando resultados;Os dados estão sendo carregados;Buscando informações;Aguarde alguns instantes;Processamento em andamento;Carregamento em progresso;Aguarde enquanto a consulta é processada',
            'Buscando os dados solicitados;Ainda carregando a lista;Processando os registros;Aguarde a conclusão da consulta',
            'Carregando os registros da consulta;Aguarde enquanto buscamos resultados;A consulta continua em andamento;Preparando os dados para consulta'),
        'error': (
            'Erro ao carregar dados;Não foi possível carregar a lista;Falha na consulta;Ocorreu um erro;Servidor indisponível;Falha de conexão;Não conseguimos buscar os registros;Erro inesperado;A consulta falhou;Dados não carregados por uma falha;Não foi possível concluir a consulta;Não conseguimos carregar os dados;Falha ao buscar informações;Erro de comunicação;Problema ao carregar a página;Não houve sucesso na consulta;Os dados não estão disponíveis por erro;O carregamento falhou;Erro no servidor;Não foi possível estabelecer conexão',
            'Ocorreu uma falha ao consultar;Não foi possível carregar os registros;Falha inesperada na conexão;Erro durante o carregamento',
            'Erro ao buscar os dados da consulta;Não conseguimos carregar a lista de registros;Falha na comunicação com o servidor;Não foi possível concluir o carregamento'),
        'access_denied': (
            'Acesso negado;Você não tem permissão;Sem autorização para esta área;Permissão insuficiente;Acesso restrito;Usuário não autorizado;Você não pode acessar esta página;Entre em contato com o administrador para obter acesso;Sua conta não tem acesso;Acesso bloqueado;Você não está autorizado;Não há permissão para consultar;Esta área exige outra permissão;Acesso não permitido;Permissões insuficientes para esta consulta;Consulta não autorizada;Sem permissão de leitura;Sua conta está bloqueada para esta área;Você precisa de autorização;Acesso proibido',
            'Você não possui permissão de acesso;Área restrita para sua conta;Consulta bloqueada por falta de permissão;Usuário sem autorização',
            'Sua conta não tem permissão para esta consulta;Acesso negado para este usuário;Não autorizado a consultar esta área;Permissão de leitura insuficiente'),
        'unknown': (
            'Projetos e tarefas;Resumo mensal;Informações gerais;Nome e descrição;Página inicial;Relatório de vendas;Histórico de atividades;Configurações da equipe;Ajuda e suporte;Detalhes do projeto;Cadastro de produtos;Lista de clientes;Qual é a previsão para amanhã?;Texto sem contexto suficiente;Informações sobre o produto;Painel da equipe;Escolha um período;Data inicial e final;Quantidade de registros por página;Visão geral da empresa',
            'Resumo da equipe;Descrição do produto;Histórico mensal;Detalhes das atividades',
            'Nome do projeto;Relatório mensal da equipe;Informações gerais do produto;Configurações de período'),
    },
    'control': {
        'navigation': (
            'Ver detalhes;Abrir relatório;Consultar histórico;Exibir projetos;Visualizar tarefas;Voltar para a lista;Próxima página;Página anterior;Ir para início;Ver mais informações;Abrir painel;Consultar dados;Exibir relatório;Visualizar histórico;Voltar ao início;Ler detalhes;Ver lista de produtos;Abrir configurações;Visualizar erros;Ver falhas;Consultar permissões;Ver instruções de exclusão;Ver como excluir;Abrir ajuda;Ver resumo;Exibir atividades;Consultar projeto;Visualizar produto',
            'Consultar detalhes;Exibir histórico;Ver relatório mensal;Abrir lista de tarefas',
            'Visualizar relatório da equipe;Consultar histórico do projeto;Ver detalhes do produto;Voltar para a página inicial'),
        'mutation': (
            'Excluir projeto;Salvar alterações;Criar tarefa;Enviar mensagem;Confirmar pagamento;Remover usuário;Publicar atualização;Apagar registro;Adicionar produto;Editar cliente;Cancelar pedido;Inativar conta;Alterar permissões;Finalizar compra;Aplicar mudanças;Excluir relatório;Salvar relatório;Enviar relatório;Criar relatório;Excluir histórico;Confirmar exclusão;Não apenas visualizar: excluir;Modificar dados;Gravar alterações;Remover acesso;Atualizar cadastro;Efetuar pagamento;Salvar detalhes',
            'Remover produto;Criar projeto;Salvar configurações;Enviar convite',
            'Excluir detalhes do projeto;Salvar alterações do produto;Enviar relatório da equipe;Confirmar pagamento do pedido'),
        'authentication': (
            'Entrar;Fazer login;Acessar minha conta;Sair;Encerrar sessão;Redefinir senha;Recuperar senha;Autenticar;Entrar na conta;Login com senha;Fazer logout;Trocar senha;Confirmar código de acesso;Iniciar sessão;Conectar à conta;Desconectar;Entrar com credenciais;Sair da conta;Recuperar acesso;Validar autenticação;Entrar no sistema;Encerrar acesso;Continuar com login;Alterar senha',
            'Fazer login na conta;Sair do sistema;Redefinir minha senha;Iniciar sessão de acesso',
            'Entrar com minha conta;Encerrar minha sessão;Recuperar a senha de acesso;Autenticar no sistema'),
        'ambiguous': (
            'Continuar;Confirmar;OK;Sim;Não;Executar;Prosseguir;Iniciar;Avançar;Ação;Opções;Clique aqui;Mais;Concluir;Aplicar;Processar;Ir;Fechar;Começar;Escolher;Selecionar;Abrir;Cancelar;Repetir',
            'Continuar agora;Confirmar agora;Prosseguir agora;Executar agora',
            'OK, continuar;Sim, confirmar;Avançar agora;Mais opções'),
    },
}


CONTRAST_AUDIT = [
    ('status', 'Nenhum problema foi detectado ao carregar os registros.', 'ready'),
    ('status', 'A consulta não apresentou erro.', 'ready'),
    ('status', 'Aguarde: o resultado ainda está sendo preparado.', 'loading'),
    ('status', 'Os registros ainda não terminaram de carregar.', 'loading'),
    ('status', 'A página não carregou por erro de comunicação.', 'error'),
    ('status', 'Falha ao obter os registros solicitados.', 'error'),
    ('status', 'Sua permissão não permite a visualização desta página.', 'access_denied'),
    ('status', 'A leitura foi bloqueada: usuário não autorizado.', 'access_denied'),
    ('control', 'Ver instruções para excluir um projeto', 'navigation'),
    ('control', 'Consultar como remover um usuário', 'navigation'),
    ('control', 'Não excluir, apenas visualizar detalhes', 'navigation'),
    ('control', 'Não visualizar: excluir o projeto', 'mutation'),
    ('control', 'Salvar o relatório que estou visualizando', 'mutation'),
    ('control', 'Excluir o histórico de visualizações', 'mutation'),
    ('control', 'Encerrar sessão de usuário', 'authentication'),
    ('control', 'Continuar com a operação', 'ambiguous'),
]

CORRECTIONS = {
    'status': {
        'ready': 'A busca não apresentou falha;O relatório não apresentou erros;A página não apresentou problemas;A consulta não falhou;Não houve falhas na busca;A busca terminou sem erro;Não ocorreu erro ao obter resultados;A leitura dos registros não apresentou falhas;Nenhum problema detectado;Nenhuma falha foi detectada;Nenhum erro foi detectado ao buscar dados;Nenhum problema ao consultar informações;Não foi detectado problema;Nenhum erro ao carregar a lista;Nenhum problema ao obter os dados;Nenhuma falha detectada no carregamento',
        'error': 'Falha ao obter dados;Erro ao obter resultados;Falha ao obter uma lista;Não conseguimos obter o relatório;Falha ao obter informações;Problema ao obter a lista de clientes;Ocorreu erro ao obter registros;Falha ao consultar os dados solicitados',
    },
    'control': {
        'navigation': 'Não excluir, apenas consultar;Não salvar, apenas visualizar;Não enviar, apenas ver;Não apagar, apenas ler;Não modificar, apenas visualizar informações;Não remover, apenas consultar detalhes;Ver instruções para remover;Consultar instruções de exclusão;Visualizar detalhes sem excluir;Visualizar histórico sem apagar;Consultar relatório sem enviar;Ver informações sem salvar',
        'mutation': 'Excluir o histórico de consultas;Excluir registros visualizados;Excluir lista de visualizações;Excluir detalhes de visualização;Excluir os relatórios consultados;Remover o histórico visualizado;Não consultar: excluir dados;Não ler: remover registro;Não visualizar: apagar dados;Não ver: excluir relatório;Não consultar, apenas excluir;Não visualizar, apenas remover;Salvar opções;Salvar preferências;Salvar ajustes;Salvar mudanças;Salvar projeto;Salvar dados;Salvar página;Salvar informações;Aplicar configurações;Editar configurações;Alterar configurações;Atualizar configurações',
    },
}

FRESH_AUDIT = [
    ('status', 'O carregamento não apresentou erro.', 'ready'),
    ('status', 'A busca dos registros não apresentou falhas.', 'ready'),
    ('status', 'Falha ao obter os dados do projeto.', 'error'),
    ('status', 'Erro ao obter o relatório solicitado.', 'error'),
    ('status', 'Aguarde o processamento dos dados solicitados.', 'loading'),
    ('status', 'Usuário sem permissão para visualizar os dados.', 'access_denied'),
    ('control', 'Não excluir, apenas consultar os dados', 'navigation'),
    ('control', 'Não salvar, apenas visualizar o relatório', 'navigation'),
    ('control', 'Excluir o histórico de relatórios visualizados', 'mutation'),
    ('control', 'Não consultar: excluir o histórico', 'mutation'),
    ('control', 'Entrar na minha conta do sistema', 'authentication'),
    ('control', 'Confirmar a operação', 'ambiguous'),
]


def make_splits(corrective=False):
    result = {split: [] for split in ('train', 'validation', 'test')}
    seen = set()
    for kind, labels in COURSE.items():
        for label, groups in labels.items():
            for split, phrases in zip(result, groups):
                for i, text in enumerate(phrases.split(';')):
                    key = (kind, text.casefold())
                    if key in seen:
                        raise ValueError('Duplicate phrase across course splits.')
                    seen.add(key)
                    result[split].append({'id': f'{kind}-{label}-{split}-{i}',
                                          'kind': kind, 'label': label, 'text': text})
    if corrective:
        for kind, labels in CORRECTIONS.items():
            for label, phrases in labels.items():
                for i, text in enumerate(phrases.split(';')):
                    key = (kind, text.casefold())
                    if key in seen:
                        raise ValueError('Correction overlaps a frozen phrase.')
                    seen.add(key)
                    result['train'].append({'id': f'correction-{kind}-{label}-{i}',
                                            'kind': kind, 'label': label, 'text': text})
        for group, cases in (('contrast', CONTRAST_AUDIT), ('fresh', FRESH_AUDIT)):
            for i, (kind, text, label) in enumerate(cases):
                key = (kind, text.casefold())
                if key in seen:
                    raise ValueError('Audit overlaps training or another audit.')
                seen.add(key)
                result['test'].append({'id': f'{group}-{i}', 'kind': kind,
                                       'label': label, 'text': text})
    return result
