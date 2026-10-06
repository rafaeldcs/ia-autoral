# Orbit: hospedar código e verificar Git de verdade

## Corrigir o entendimento do produto

Uma conexão com GitHub não é hospedagem Git. Repositório próprio significa guardar
objetos, refs e histórico num diretório bare persistente, fornecer uma URL que um
cliente Git consegue clonar e aceitar push autenticado. O projeto Scrum/Kanban é
ligado ao repositório; commits com a chave da tarefa abrem a tarefa correspondente.

## Contratos e autorização

- Use o `git http-backend` oficial para o protocolo smart HTTP; não invente packs.
- Identifique diretórios pelo UUID do projeto, nunca por nome recebido do usuário.
- Tokens pessoais aleatórios só valem para um projeto, expiram em 30 dias, podem
  ser revogados e são guardados como hash. Não use a senha de login como token Git.
- Os papéis do Orbit são globais no workspace: administrador/gestor cria;
  colaborador pode enviar commits; leitor só lê. A escrita exige também token de
  escrita e conta ativa. Revalide papel e expiração em cada requisição Git.
- Não dê autenticação por cookie ao protocolo Git. Para o navegador, mantenha
  sessões, CSRF e proxy já existentes. Tokens pessoais só são mostrados uma vez,
  mascarados por padrão e sem persistência no navegador.
- Recuse caminhos/protocolos extras, redirects, hooks, push não fast-forward e
  exclusão de branches. Use executável e argumentos fixos, sem shell.
- Limite bytes, tempo, concorrência e armazenamento. Packs são binários; não os
  converta em texto. Ao processar CGI, espere a linha vazia completa, não a primeira
  quebra de linha, e encaminhe todos os bytes do corpo.
- Na prévia de arquivos, preserve indentação e quebras de linha. Escape o conteúdo
  como texto React, nunca HTML; não execute código recebido. Confira tipo e
  alcançabilidade do objeto antes de exibi-lo.

## Como pedir e revisar propostas locais

Separe os pedidos C# e TypeScript. Um preâmbulo que manda escrever C# contradiz uma
solicitação TSX, mesmo se o final diz para ignorá-lo. Declare assinaturas reais,
campos do banco e exemplos pequenos da API existente. `Store.Query` não é genérico;
os parâmetros Npgsql são `$1`, `$2`; `await` precisa ocorrer antes de usar o resultado.
`api<T>(path,method,body)` não tem métodos `get`/`post`. Não invente classes de apoio.

Preserve respostas originais, hashes, propostas rejeitadas e diferenças da revisão.
O rascunho que recebeu correções diretas do revisor foi preservado separadamente e
não deve ser publicado como implementação da IA local. Quando a autoria local é
requisito do usuário, o revisor descreve contratos, prepara testes, devolve falhas e
aplica respostas revisadas; ele não corrige a lógica do produto no lugar do modelo.
Patches locais só são aplicados quando o texto anterior corresponde exatamente à
fonte. Patches com JSON inválido, trechos inexistentes ou alterações sem efeito
voltam ao autor. Uma montagem mecânica de fragmentos deve ser declarada como tal,
com hashes de cada origem; não se atribui uma correção humana ao modelo.

Nesta investigação, instruções explícitas não impediram o Qwen3-8B de inventar
APIs, duplicar campos de classes parciais e repetir consultas incorretas. Pedidos
menores e a comparação privada de orçamento de raciocínio servem para avaliar a
resposta, não para dispensar validação. Propostas não equivalem a capacidade
autônoma. Nenhuma mudança desse perfil privado promove ou altera os pesos.

Falhas concretas encontradas e devolvidas nesta ampliação:

- Um método isolado não é um arquivo C# compilável; a classe parcial precisa
  envolver o método e usar o mesmo namespace das demais partes.
- Não transforme `!valid` em `valid` ao trocar uma propriedade por função:
  isso inverte o aceite. Teste um identificador válido e outro inválido.
- `info/refs` é endpoint; `receive-pack` é serviço. A permissão de escrita
  também se aplica ao anúncio usado pelo push, antes do envio dos objetos.
- `ContentLength` ausente não equivale a corpo inválido. Um POST acima do
  limite deve ser rejeitado antes de consumir seu corpo.
- Espere a transferência terminar antes de liberar a exclusão mútua;
  `WhenAny` com delay, sem esperar o trabalho cancelado, permite duas escritas.
- Um leitor pode criar seu token de leitura; bloquear todo o formulário por
  papel impede esse uso permitido. Bloqueie a opção de escrita e confira no backend.
- Importe os componentes de seus módulos reais, não invente um helper `api`
  duplicado. A resposta de lista é um array; a criação retorna `{id,token}`.
- Recarregue dados reais após criar/revogar; não invente datas de expiração.
  Associe labels aos inputs e ofereça erro, ação e resultado visíveis.
- Ao corrigir JSON de patches, preserve os espaços do trecho anterior e
  confira o texto após decodificar JSON. Não use `...`, trechos inexistentes
  ou substituições que não mudam nada. Não adivinhe o número de escapes.
- Para relacionar commits e tarefas, teste a expressão no navegador. Ao contar
  escapes em logs JSON, decodifique cada camada antes de alegar um defeito.
  Nesta revisão uma suspeita sobre a expressão foi erro do revisor; a fonte
  local original foi preservada e a tentativa de correção foi rejeitada.

Os testes são do revisor e o código é proposto pelo modelo. A aprovação do
produto com essa supervisão não comprova que o modelo produz a mesma solução
sem roteiro, diagnóstico e revisão. Registre esse limite na qualificação.

## Verificação funcional obrigatória

Execute no sandbox Linux verificado com PostgreSQL descartável e contas sintéticas:

1. Criação permitida/negada por papel, repetição, repositório vazio e reinício.
2. Tokens por projeto e usuário, segredo ausente em GET/banco/auditoria, revogação,
   expiração, conta desativada e papel alterado.
3. Cliente Git real: clone privado, commit, push, segundo clone, pull fast-forward
   e branch adicional. Compare os SHA e os arquivos, não só o HTTP 200.
4. Rejeição de escrita com token de leitura, force push e exclusão de branch.
5. Tipo/alcançabilidade de objetos, texto Unicode e indentação, arquivos grandes,
   CGI binário, cabeçalho incompleto e limites de entrada/saída.
6. Coloque um hook sintético no teste e confira que ele não foi executado.
7. Navegador real nos quatro papéis: arquivo, tarefa vinculada, token mascarado,
   descarte, revogação, erro visível e largura de celular. Nenhuma captura com token.
8. Na HML, repita Git por HTTPS através do gateway, verifique o SHA servido e
   confirme que os serviços ShopAir foram preservados.

Se o servidor recusar Content-Length antes de ler o corpo, um cliente que envia
tudo imediatamente pode obter BrokenPipe. Leia a resposta HTTP antecipada; não
relaxe o limite nem declare esse erro do cliente como falha da IA.

Para testar upload pendente, use `Expect: 100-continue` e espere a resposta
intermediária antes de verificar o bloqueio. Consultas GET disparadas cedo
podem adquirir o escritor antes do upload e causar HTTP 409 no próprio upload.
Essa corrida estava no teste do revisor, não no código local; o teste deve
sincronizar pelo protocolo sem mascarar falhas com espera arbitrária.

## Operação e limites

Atualizações preservam os diretórios e fazem backup Git com o único escritor
pausado, além do banco. Não siga symlinks para fora da raiz no snapshot. Restore é
operação do administrador, após conferir arquivo, espaço e histórico.

Hospedagem própria não configura automaticamente CI/deploy de qualquer código.
A receita atual do Orbit continua ligada ao GitHub e à branch revisada. Um push
apenas no repositório hospedado não publica uma aplicação. Para novos pipelines,
primeiro revise a receita e execute código apenas no sandbox; nunca monte o socket
Docker na API nem execute scripts de usuários no servidor HML.

Referência primária: https://git-scm.com/docs/git-http-backend

Material de consulta e revisão. Não autoriza treinamento ou promoção de pesos.
