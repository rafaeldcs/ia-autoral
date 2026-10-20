# Perfis por nome na LocalAuthor

A LocalAuthor identifica o espaço de trabalho pelo nome escolhido. **Não há usuário ou senha para entrar no perfil.** Os modelos continuam no mesmo servidor da rede local, com pastas, projetos e conversas organizados por perfil.

Esta escolha serve para organização: **quem tem acesso ao aplicativo pareado pode selecionar o nome de outra pessoa e abrir aquele perfil**. Projetos separados não são uma garantia de sigilo entre integrantes da equipe. O pareamento do computador e a validação do certificado do servidor continuam obrigatórios para acessar o serviço pela rede.

## Primeiro acesso

1. Abra a LocalAuthor nesta máquina servidor. Se a janela ainda mostrar a versão anterior da tela, feche e abra novamente o aplicativo.
2. Em **Quem está usando a LocalAuthor?**, informe seu nome e clique em **Criar meu perfil**. Use nome e sobrenome para evitar confusão.
3. O primeiro perfil será administrador da organização e receberá os projetos e históricos existentes, sem mover ou apagar seus arquivos. Se houver tarefas na fila, aguarde sua conclusão e tente novamente.
4. Nos outros computadores, abra o aplicativo conectado à mesma rede e escolha um nome existente ou informe um novo. Um novo nome cria automaticamente um espaço de pessoa da equipe, sem senha.

Os perfis existentes são listados na entrada. Diferenças de maiúsculas e espaços repetidos não criam outra pessoa. Nomes com e sem acento podem ser diferentes; prefira escolher na lista quando o perfil já existir. Perfis desativados não são recriados automaticamente com o mesmo nome.

## Trocar e organizar perfis

Use **Meu perfil → Trocar perfil**, no rodapé da barra lateral. A sessão atual é encerrada e você escolhe outro nome. Outras abas da mesma instalação são recarregadas para não continuar mostrando a seleção anterior. Uma seleção pode durar até 12 horas; ao expirar, basta escolher o nome novamente.

**Meu perfil** mostra somente o nome em uso, **Trocar perfil** e, para administradores, **Gerenciar equipe**. Não carrega a lista de pessoas nem exibe formulários ao abrir. Em **Detalhes do perfil**, ficam a pasta no servidor e a explicação da identificação sem senha.

**Gerenciar equipe** abre uma tela separada. **Adicionar pessoa** expande o cadastro; selecionar o nome de uma pessoa abre somente seus campos de edição. É possível corrigir nomes, desativar perfis e organizar as funções de administrador/pessoa da equipe. **Voltar** retorna ao menu pessoal. Falhas ao carregar a lista aparecem nessa tela com **Tentar novamente**, sem bloquear o acesso ao próprio perfil. Também é possível criar um novo perfil apenas informando seu nome na entrada.

As funções administrativas organizam as opções disponíveis no perfil selecionado. Como qualquer pessoa pareada pode selecionar um perfil administrador, elas não substituem autenticação pessoal. Para corrigir nomes iguais de perfis antigos, um administrador deve diferenciá-los antes da seleção por nome.

## Projetos e conversas

**Adicionar projeto → Criar uma nova pasta no servidor** cria uma pasta dentro do espaço daquele perfil. **Vincular uma pasta existente** registra uma pasta própria; pessoas da equipe só vinculam pastas no próprio espaço. Administradores podem vincular outras pastas do servidor, respeitando a separação de espaços e o bloqueio de pastas sobrepostas a projetos existentes.

Projetos novos aparecem inicialmente apenas no perfil que os criou. Para trabalhar juntos, o proprietário abre **Orientações do projeto → Gerenciar compartilhamento**, escolhe outro perfil e define:

| Acesso no perfil selecionado | O que permite |
|---|---|
| Somente leitura | Consultar o projeto, suas fontes, conversas e resultados |
| Pode editar | Consultar, conversar, solicitar tarefas e alterar conteúdo |
| Proprietário | As ações anteriores e gerenciar o compartilhamento |

O compartilhamento inclui **todo o histórico e as fontes do projeto**. O filtro **Minhas conversas** organiza quem iniciou a conversa, sem ocultá-la de outros perfis que compartilham o projeto. Mensagens antigas ficam identificadas como histórico anterior aos perfis.

Remover acesso impede novas operações naquele perfil. As permissões dos jobs são verificadas novamente quando começam; uma execução já iniciada não é cancelada automaticamente. Isso não impede selecionar o nome do proprietário, pois a identificação por nome foi escolhida sem senha.

## Rede, atualizações e dados

O aplicativo Windows 0.3.8 continua procurando o servidor na rede, validando seu certificado e recebendo atualizações. A sessão de perfil e as listas de projetos ficam no servidor; não é preciso instalar ou ensinar de novo os modelos em cada computador.

**A senha de publicação de atualizações é separada e permanece exigida para publicar uma versão.** Ela não é uma senha para usar um perfil. O aplicativo pareado também continua usando sua credencial de dispositivo automaticamente, sem pedir um arquivo de conexão no uso normal.

Atualizar o GitHub não reinicia sozinho o servidor. Siga o [passo a passo da rede local](PASSO_A_PASSO_REDE_LOCAL.md) para aplicar código e distribuir clientes. A atualização espera o chat ficar livre e preserva rascunhos do perfil correspondente. Backups incluem dados privados; mantenha-os fora do Git. Restaurar um backup preserva perfis e projetos, mas descarta sessões recuperadas, exigindo escolher o nome novamente.

Perfis antigos que tinham senha podem ser escolhidos pelo nome com os mesmos projetos e identificadores. As funções antigas de senha permanecem para compatibilidade de dados e integrações; elas não restringem a seleção por nome e não são exibidas na interface. Não use nomes como autorização para dados que precisem de sigilo pessoal.

## Validação

A implementação verifica a organização por perfil na API, não apenas na barra lateral. Testes usam bancos reais, identidades descartáveis, navegadores separados e gateway HTTPS real. O ensaio de dois dispositivos foi feito nesta máquina; um segundo computador físico não foi testado. Nada nesta mudança treina novamente os pesos dos modelos ou introduz um serviço remoto de IA.
