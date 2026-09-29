# Investigação de código a partir do relato — laboratório restrito

Rodada de 29/09/2026. O objetivo desta etapa é retirar a indicação do arquivo e da função durante a execução. Não é qualificação de programação geral, investigação de qualquer defeito ou compreensão arbitrária de português.

## Resultado final executado

O quinto candidato recebeu qualificação restrita após **112/112 episódios**: 28 snapshots reservados e 84 regressões dos ensaios anteriores. Os cenários incluem 48 correções, 16 projetos sem o defeito, 16 pedidos fora do escopo, 16 erros de execução e 16 projetos com outro teste reprovado. Os dois últimos grupos devem pedir ajuda. O avaliador exige que a própria política escolha a resposta correta; uma proteção determinística bloqueando uma ação errada não conta como acerto neural.

Passaram também **244 testes do LocalAuthor**, sem pulos. No replay histórico do saravaAPP, a política completou **12 ações**, encontrou `app/src/lib/presentation.mjs`, reproduziu a data indevida, solicitou a guarda e a asserção ao modelo de código, executou vermelho/verde, verificações independentes e os **195 testes JavaScript existentes naquela revisão**. Três módulos foram descartados pela ferramenta por não corresponderem ao padrão suportado; não se alega compreensão desses módulos.

O script público `Invoke-InvestigationAgent.ps1` foi executado no Windows e reproduziu esse resultado usando apenas Docker para executar código do projeto. O checkout atual do saravaAPP ficou intacto. O certificado foi ativado para esse script no servidor; a capacidade não foi apresentada como modo livre do chat.

O controlador tem 116.224 parâmetros, 503 demonstrações de treino e 37 de validação. Foram 1.500 passos, com seleção por validação e checagem de retenção em exemplos de treino. O checkpoint é `investigation-agent-v5-20260929/best-validation.npz`, SHA-256 `a94d64db5affd2d811e6a749e994ea9657e28d6d2baaf7eded37884a7fe86ad0`. O gerador de código continua sendo o especialista separado de datas; ambos usam pesos originais locais.

Evidência privada: `reports/investigation-agent-evaluation-v5/`, incluindo `episodes.json`, `qualification.json`, `sarava-replay/journal.json`, `proposal.diff`, `proposal.json` e recibos de Node. O diário contém cada observação e a resposta original dos pesos. `reports/investigation-agent-unit-tests-v5.json` registra os testes da plataforma; `reports/investigation-agent-launcher.log` registra a execução pelo comando público. Tentativas anteriores e a auditoria de contaminação permanecem preservadas.

## Como funciona

O executor recebe um snapshot Git e apenas um relato. O modelo de política escolhe ações de um catálogo fechado: buscar `new Date`, ler o próximo candidato, executar uma prova com `null`, solicitar a correção, executar testes, entregar para revisão, registrar que não reproduziu ou pedir ajuda. Não há comando shell livre.

A busca considera até cinco módulos `.mjs` em `app/src/lib`. Nomes de arquivos são referências opacas: o mapa aparece no diário, mas não pode induzir o modelo a escolher um arquivo por seu nome. A busca é sequencial. Uma ferramenta determinística extrai somente funções compatíveis com o especialista de datas, incluindo identificador, parâmetro e mensagem de ausência. Isso foi escrito por Codex; não é análise livre de código feita pelo modelo.

A política decide o próximo passo usando a observação da ferramenta. A prova executa Node real em Docker. Após reproduzir uma divergência, o especialista de datas já qualificado gera a guarda e a asserção. A regressão deve falhar no original e passar na cópia corrigida. Verificações independentes e os testes existentes também precisam passar. Uma falha deve levar a um pedido de ajuda, não a uma declaração de sucesso.

Nenhum arquivo do checkout original é alterado. O resultado é uma proposta com hashes, diff, asserção, diário e recibos. Mesmo aprovada pelos testes, ela continua aguardando revisão. Propostas com testes reprovados são marcadas como rejeitadas.

## O que foi ensinado nas tentativas

1. O modelo geral anterior respondeu com texto inválido ao primeiro pedido de investigação. Essa resposta foi preservada.
2. O primeiro controlador passou 27 de 28 episódios, mas investigou datas quando o relato pedia alteração de senha. No snapshot real do saravaAPP, produziu uma ação inválida ao receber nomes longos de arquivos. Foi reprovado.
3. A segunda tentativa passou 18 de 28 episódios novos e 27 de 28 regressões. Já completou o replay histórico do saravaAPP, com 195 testes existentes aprovados, mas não compreendeu uma variação do relato. Foi reprovada.
4. A terceira tentativa recebeu mais exemplos de linguagem e passou a validação, mas somente 24 de 84 episódios completos passaram. O treinamento desequilibrado produziu ações inválidas nas etapas menos frequentes. Validação textual agregada não demonstrava manutenção de cada habilidade.
5. O treino seguinte sorteia primeiro a ação, depois um exemplo daquela ação, e exige também a reprodução de exemplos de treino de todas as ações antes de parar. Essa tentativa passou 111 de 112 episódios, ainda sem aprovação. Um teste unitário adicional detectou uma frase reservada duplicada em uma demonstração manual; o candidato também foi invalidado por essa sobreposição.
6. A partição reservada passou a ter prioridade sobre todas as fontes de exemplos, inclusive as demonstrações manuais. Treino e avaliador agora verificam a separação antes de iniciar. Um novo treino parte do zero; não se reutiliza o checkpoint contaminado. As evidências reprovadas permanecem preservadas.

Casos usados para ensinar uma falha passam a ser regressões. Os snapshots reservados têm nomes e posições distintos dos primeiros ensaios, mas também foram executados em tentativas posteriores; os relatos já foram avaliados anteriormente. Não contam como prova independente, feita uma única vez, de generalização de linguagem. Após a correção da partição, os relatos reservados ficam fora dos exemplos usados para ajustar os pesos, porém já influenciaram o desenvolvimento do experimento. Essa diferença importa.

O campo legado `episodesUsedForTraining=false` no checkpoint desta rodada refere-se a trajetórias completas, não à ausência de ensino com relatos de falhas anteriores. Relatos antigos foram usados como explicado acima. O script agora separa explicitamente esses campos de proveniência; a anotação esclarecedora acompanha o checkpoint sem reescrever seus bytes ou seu hash.

## Limites e autoria

- Codex escreveu currículo, ferramentas, parser de contexto, contratos de aceitação, invólucros de teste e avaliador. O modelo de política escolhe as ações; o especialista neural de datas gera a correção e a asserção.
- Cada episódio começa sem o caminho e sem a função defeituosa. O avaliador conhece a resposta para conferir o resultado, mas não a fornece ao controlador. Não há ajuda humana durante os episódios.
- A causa é escolhida dentro de uma família ensinada: conversão de ausência de data para epoch. Não há descoberta de classes de defeitos desconhecidas.
- O agente sabe interromper a tentativa diante de uma falha; ainda não interpreta e corrige um problema de negócio diferente nem escreve uma estratégia completa de testes sozinho.
- O replay do saravaAPP usa a revisão histórica `15665ba523a6955f8c6044adb7fb463c0cb843ee`, já utilizada antes. Não é um defeito inédito. O checkout atual já contém a correção anterior e permanece intacto nesta rodada.
- Não foram introduzidos pesos pré-treinados, APIs de IA, pacotes adicionais ou acesso de rede durante treino e avaliação. A infraestrutura é a imagem local revisada `localauthor-code-repair-lab:1`, com NumPy e Node.

## Reutilização

`scripts/Invoke-InvestigationAgent.ps1` recebe `-Project`, `-Report` e opcionalmente `-Revision`. Exige certificado ativo aprovado, cria um snapshot Git, verifica isolamento Docker e salva a proposta em uma pasta inédita de `reports/`. O argumento `-Report` aceita somente o sintoma, não um gabarito. Ausência de Docker, certificado inválido ou ação fora do catálogo impedem a execução; não há fallback de código de projeto para Windows.

Exemplo de reprodução histórica, executado na pasta do LocalAuthor:

```powershell
./scripts/Invoke-InvestigationAgent.ps1 `
  -Project C:/Users/rafae/OneDrive/Desktop/meuterreiro `
  -Revision 15665ba523a6955f8c6044adb7fb463c0cb843ee `
  -Report 'Uma tela mostra 1969 quando a data não foi informada.'
```

Essa revisão contém o defeito antigo. A revisão atual já está corrigida e não deve ser modificada para fabricar novamente o problema. O laboratório não publica alterações nem muda dados do banco.

O modo de investigação de código é um laboratório acionado pelo script no servidor. **Ele ainda não está integrado como modo livre de investigação no chat.** As funções e os modelos anteriores do chat continuam separados. O campo global `model_qualified` continua falso.

Pesos e corpus ficam em `%LOCALAPPDATA%/LocalAuthor/models`, certificados em `exports`, ambos fora do Git. Atualizar o repositório não transporta os pesos. Importar este documento permite consultar as lições; não altera pesos automaticamente.

O próximo passo após esta qualificação restrita é investigar outra família de defeitos com menos contexto estruturado e criar testes completos, preservando estas habilidades. Uma avaliação precisa medir isso explicitamente antes de conceder mais autonomia.
