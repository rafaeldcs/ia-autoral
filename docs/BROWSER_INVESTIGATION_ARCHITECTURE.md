# Passagem do laboratório para páginas reais

## Estado atual

O classificador 18–64–12 foi aprovado apenas com observações booleanas fornecidas
pelo laboratório. Ele não lê HTML, DOM, imagens ou linguagem arbitrária. O
Transformer autoral, por sua vez, tem contexto de 256 tokens e falhou no teste
anterior de investigação em linguagem livre. Acertos do classificador não
substituem essas capacidades.

Em 18/09/2026, uma leitura real da interface LocalAuthor pelo navegador produziu
4.448 bytes de snapshot acessível. Só títulos e nomes dos 15 controles visíveis
somaram 363 bytes. O tokenizador autoral é por byte, e ainda seriam necessários
o objetivo, histórico e protocolo de ações. O conteúdo da conversa não foi
persistido nessa medição. A navegação foi de Codex, não do modelo.

## Infraestrutura preparada

`browser_investigation.py` define uma sessão independente do backend de modelo:

1. O adaptador confiável observa URL, título, texto visível e controles com IDs.
2. O modelo recebe objetivo, observação, visitas anteriores e pendências.
3. O modelo propõe JSON com ação, hash da observação, alvo, citação e motivo.
4. O adaptador coleta novamente antes de executar; um hash divergente invalida
   o clique. Não se usam IDs de uma tela antiga.
5. O protocolo valida origem, alvo observado e escopo de leitura. Alterações,
   mensagens, pagamentos e destinos externos não são ações deste fluxo.
6. O adaptador devolve um comprovante de execução ou falha. Uma proposta não é
   contada como ação realizada. Citações precisam existir na observação; a
   interpretação do modelo continua identificada como não verificada.
7. Ao encerrar, controles descobertos e não visitados continuam como pendências.
   Encerramento não é sinônimo de cobertura total.

Não há executor de navegador instalado, conexão nova com serviço de IA ou modelo
externo adicionado nesta etapa. O protocolo não interpreta uma anotação da página
como autorização. A identificação de controles de navegação é responsabilidade
do adaptador confiável, não uma declaração livre do modelo ou do site.

O caminho do modelo autoral recusa entradas acima do contexto, JSON inválido e
saída truncada. Não corta a página silenciosamente, não troca a resposta pelo
gabarito e não executa código gerado. O observador deve excluir valores de
formulários, cookies e credenciais antes da entrada; a detecção textual de
segredos é complementar e não universal.

## Decisão necessária para ampliar a compreensão

O AGENTS.md proíbe pesos pré-treinados e APIs de IA. Com essa regra, a evolução
continua sendo pesquisa do modelo autoral: arquitetura/contexto, corpus de
linguagem e programação autorizado, treinamento e avaliações novas. Não existe
uma alteração pequena que transforme o candidato atual em um investigador geral.

Outra opção, dependente de escolha explícita do usuário, é um modelo pré-treinado
executado localmente, preservando os dados no servidor e mantendo o núcleo
autoral como laboratório separado. Isso também exigiria validação: nenhum
modelo garante investigar todo sistema, compreender qualquer tela ou acertar
todos os casos possíveis.

O próximo marco de aprovação deve exigir uma investigação em navegador de um
sistema não usado no treino: seleção correta de controles, observação posterior,
evidências rastreáveis, recuperação de erros, proteção de dados, pendências
honestas e nenhum efeito fora do escopo. Preparar o protocolo não aprova esse
marco; a escolha da arquitetura de linguagem permanece pendente.
