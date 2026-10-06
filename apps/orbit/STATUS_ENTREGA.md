# Orbit — integração de projetos, Git e homologação

## Estado da entrega

Integração GitHub anterior validada no laboratório Linux: 73 testes unitários,
9 cenários de API com PostgreSQL, retomada após reinício, bloqueio de setup,
7 testes da política de pacotes e navegador real nos quatro papéis, desktop e
celular. Compilações .NET Release e Next.js/TypeScript aprovadas.
Também houve login, pull e push autenticado reais na HML, na revisão
`42da83eef6accc4bb610cf3fabd26f96f967a25e`. O push confirmou sincronização de uma
árvore limpa; não criou mudança remota artificial. A credencial temporária foi
removida antes da próxima publicação e não permanece configurada para uso diário.

O endereço HTTPS respondeu saudável nessa revisão. As primeiras duas tentativas
do CI validaram o produto, mas falharam na preparação Docker. Dependências ausentes,
opções tmpfs no YAML e capability necessária ao executável oficial Caddy foram
corrigidas na infraestrutura do Codex. O controlador agora interpreta Compose
com o CLI real antes do laboratório. Não se atribuem esses erros ao modelo local.

O resultado definitivo de **cada publicação** é o job Orbit HML no GitHub Actions,
mais o SHA retornado por `/api/health`; este documento não substitui o recibo de CI.

Infraestrutura isolada ativa em HML: configuração privada, chave CI restrita,
volume Git de 512 MiB, rota HTTPS própria, banco e chaves persistentes.

## Hospedagem Git própria — autoria e aceite

Resultado do laboratório em 06/10/2026: **96 testes unitários, 21 cenários de
API (12 de hospedagem nativa), 11 verificações da infraestrutura, navegador nos
quatro papéis e tela de 390 px aprovados**. .NET Release e Next.js/TypeScript
compilaram. As 48 fontes/alterações de produto têm hashes e origens locais no
recibo. A suíte geral LocalAuthor teve 415 aprovações e três testes de symlink
indisponíveis no Windows; o CI Linux executa a suíte geral separadamente.

A ampliação oferece um repositório bare privado por projeto, URL para clone e
push por HTTPS, arquivos, branches e commits vinculados às tarefas. Tokens
pessoais expiram em 30 dias, são revogáveis e limitados a um projeto. O papel
atual da conta e a permissão do token são verificados em cada operação.

O requisito do usuário é que o **LocalAuthor escreva a implementação**. Um
rascunho que recebeu reparos diretos do Codex foi separado e não compõe essa
entrega. As novas fontes são respostas locais e patches locais aplicados
literalmente depois da revisão. O Codex especifica contratos, devolve erros,
prepara testes e opera a infraestrutura. O recibo específico dessa ampliação é
`LOCAL_AI_HOSTING_PROVENANCE.json`; ele não altera a autoria da versão original.

O aceite exige compilação .NET/TypeScript, testes de política e CGI, PostgreSQL
descartável, clientes Git reais e navegador nos quatro papéis. Inclui entrada
fragmentada, cancelamento com liberação do escritor, token de leitura emitido
por colaborador, revogação, alteração de papel, limite de bytes e hooks
desativados. Resultados definitivos constam do recibo, CI e SHA de saúde.

O código rastreado de `apps/orbit` é importado como repositório independente no
projeto ORB, com a revisão GitHub de origem registrada no commit e no recibo
privado. Seu SHA Git pode diferir do SHA do monorepositório servido pela API.
Isso permite navegar pelo próprio código do Orbit sem carregar toda a história
do LocalAuthor. A importação inicial não substitui histórico existente.

Limites: 20 MiB por requisição de push, volume de 512 MiB compartilhado com a
integração GitHub, prévia de arquivo até 16.000 bytes e orçamento de 32 KiB para
metadados. Histórias grandes podem exigir clone para leitura. Os papéis são
globais no workspace; não há ACL independente por projeto. Não há LFS, SSH,
pull requests nem editor de código nesta ampliação. Push no repositório nativo
armazena código; deploy continua pela receita GitHub revisada do Orbit.

A lição durável usa o mecanismo de consulta do LocalAuthor, com hash e versão.
Esse registro e a orientação nas tentativas não são treinamento dos pesos nem
prova de autonomia geral.

O Orbit original foi preservado em `apps/orbit`, no repositório `ia-autoral`,
para manter o histórico sem alterar a pasta original do experimento.

## Autoria e verificação

O código original de setembro foi escrito majoritariamente pelo Codex. Os novos
módulos de Git, fila, entrega, proxy e interface foram propostos pelo Qwen3-8B
local, com revisão do Codex. Métodos/cabeçalhos de respostas locais foram montados
quando o arquivo completo falhou. Testes, controladores e infraestrutura são do
Codex. Hashes UTF-8/LF e tentativas estão em `LOCAL_AI_PROVENANCE.json`; respostas
originais permanecem privadas. Não houve treino de pesos ou qualificação universal.

As primeiras propostas falharam em compilação, APIs, permissões e regras de Git.
Foram preservadas em evidências privadas e não publicadas como implementação.
A divisão em módulos menores e os resultados dos testes foram devolvidos ao
modelo. Registrar essas experiências não significa que os pesos foram treinados.

O laboratório verificou a identidade da imagem Docker, usuário sem privilégios,
sistema de arquivos somente leitura, código montado somente para leitura, ausência
de rede/portas/socket Docker, limites de memória/CPU/processos e área temporária.
Código gerado não foi executado diretamente no Windows.

## Comportamento implementado

- Projeto Scrum/Kanban ligado a um repositório GitHub e branch explícita.
- Administradores configuram conexão; administradores/gestores executam operações.
- Pull exige árvore limpa e avanço direto; push não usa força e confirma a revisão.
- Commits relacionados às tarefas, fila persistente, auditoria e erros visíveis.
- Deploy separado no servidor HML da ShopAir, por revisão imutável, com testes,
  verificação de saúde e recuperação da versão anterior.

`https://orbit.hml-app.shopair.com.br` usa o servidor HML e o certificado existente.
Os demais sites, bancos e containers são preservados. A cópia original do Orbit
na área de trabalho não foi migrada nem teve seu banco alterado: o workspace HML
é separado, com os exemplos originais identificados e sua própria conta.

A credencial administradora do Orbit fica privada, protegida por DPAPI no Windows,
com auxiliar de acesso na pasta privada da entrega; não é a conta Super ShopAir.
Configure um token GitHub restrito ao repositório para usar escrita/publicação
pela interface. Sem token, ela informa a necessidade e desabilita os botões de
escrita, mantendo pull público disponível. O pipeline do push feito por Git no
computador de trabalho funciona com sua chave CI própria.

Referências: [Git pull](https://git-scm.com/docs/git-pull),
[controle de deploys no GitHub](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
e [Next.js em servidor próprio](https://nextjs.org/docs/app/guides/self-hosting).
