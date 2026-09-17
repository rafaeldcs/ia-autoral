# Relatório de entrega — LocalAuthor 0.1.0

**Data:** 17/09/2026. **Formato:** projeto-fonte executável, testes e documentação. **Status:** protótipo de plataforma + laboratório de modelo CPU; não é a IA programadora completa do planejamento.

## 1. Resultado da solicitação GitHub

A conta `rafaeldcs` foi lida com sucesso pelo conector. As ações disponíveis nesta conversa eram somente de leitura. Também foi verificada a integração instalada; não apareceu uma ação de criação/push utilizável. Não havia CLI autenticado disponível neste ambiente. **Não foi criado repositório remoto, feito push ou iniciado workflow.**

O projeto foi implementado no ambiente local da conversa, com scripts de publicação privada para `rafaeldcs/ia-local-autoral`. Esse é um destino proposto, não uma URL confirmada. O usuário conclui a autenticação e executa o script no seu computador. Nenhum token precisa ser compartilhado.

## 2. Código efetivamente implementado

Memória SQLite/FTS5 com escopos, versões, hashes, linhas e relações; importação/indexação; pesquisa HTTPS opt-in com robots, cache e bloqueio de destinos privados; API local autenticada; interface PT-BR; fila persistente; diagnóstico; propostas manuais/importadas com snapshot/diff/revisão/aplicação por pré-condições; recuperação por journal; experiências; backup/restauração; executor Docker opt-in com comandos fixos.

No laboratório neural: tokenizadores byte/BPE, diferenciação reversa, Transformer causal, camada de atenção/MLP, perda de entropia cruzada, AdamW, checkpoints com estado do otimizador e RNG, validação de corpus e partições, treinamento, retomada e geração experimental. NumPy fornece apenas arrays/matemática; nenhum framework de IA ou peso pronto participa.

**Não foram treinados e distribuídos pesos de um modelo de programação.** Os experimentos numéricos em padrões minúsculos verificam o motor, não competência em C#.

## 3. Diferença em relação à arquitetura planejada

O núcleo funcional é **Python**. O plano original previa C#/.NET predominante. A entrega inclui um host ASP.NET Core que encaminha para esse núcleo local, mas ele **não foi compilado**: o SDK não estava disponível e a obtenção pela rede falhou.

Não há Roslyn funcional, backend C++/CUDA ou modelo de 34 milhões de parâmetros. Esses itens estão explicitamente pendentes. O arquivo `native/README.md` é documentação da ausência do backend, não código GPU.

## 4. Evidência real de validação

| Verificação | Resultado |
|---|---|
| Bateria automatizada Python | **119 testes, 0 falhas, 0 erros, 0 ignorados**, em Linux |
| Ambiente de testes | Python 3.13.5, NumPy 2.3.5; não é o notebook do usuário |
| Sintaxe Python | `compileall` executado sem erro |
| Sintaxe JavaScript | `node --check ui/app.js` executado sem erro |
| Sintaxe scripts shell | `bash -n` executado sem erro |
| Publicação shell dry-run | Executado; não cria repositório |
| Navegação Chromium/Playwright | **Bloqueada** por política administrativa (`ERR_BLOCKED_BY_ADMINISTRATOR`) |
| HTTP/API | Exercitados pela bateria; autenticação, origem, memória e fluxo de revisão |
| Coleta de sites reais | Não executada; transportes simulados nos testes |
| .NET build/runtime | Não executados |
| Windows/PowerShell | Não executados neste ambiente |
| Docker real/isolation | Não executado; construção do comando e recusas testadas |
| CUDA/RTX 2060 | Não implementada/não testada |
| GitHub Actions | Workflow escrito; não executado remotamente |

O relatório JSON contém casos individuais e tempos. Esses tempos medem o container da implementação, **não o notebook**. A bateria não tem 119 desafios de programação nem prova “119 tarefas de IA resolvidas”.

Os testes incluem derivadas por diferenças finitas, atenção causal, estado do otimizador após checkpoint, queda de loss em padrão numérico, escopo e versões da busca, deduplicação, conflitos de arquivo, rollback/recovery, segredo/caminho/link, robots/cache/SSRF simulados, fila/cancelamento, validação de corpus e backup.

O experimento numérico adicional (`reports/neural-smoke.json`) usou 3.016 parâmetros e 90 passos em um padrão de inteiros. A perda caiu de aproximadamente 5,5471 para 0,01704. Como a medição usa o mesmo padrão ajustado, isso é **overfit deliberado de verificação do motor, não generalização nem aprendizado de programação**. Não foram exportados pesos.

A falha do teste visual não foi convertida em aprovação. O relatório `reports/ui-smoke.json` a preserva e a distingue dos testes HTTP.

## 5. Limites funcionais atuais

- Consulta retorna trechos e fontes; não produz síntese de modelo competente.
- Relações são registradas com evidência, mas não há um agente que “entenda tudo” e construa sozinho um grafo confiável.
- A pesquisa aceita URLs autorizadas e reutiliza cache. Não é um buscador geral, nem um pesquisador autônomo com avaliação semântica de lacunas.
- O operador prepara/importa as propostas de alteração. O modelo experimental não gera patches autorizados nem se autocorrige em projetos.
- O runner precisa de imagem local confiável configurada; vem desligado. Não há dependência de execução arbitrária no host para fingir testes.
- Aplicar sem teste é uma escolha explícita de laboratório, não validação da alteração. Exit code zero, mesmo em testes, tem alcance limitado.
- O motor é CPU float64 e limitado a configurações pequenas; o notebook não usará a RTX por meio desse código atual.
- O corpus de referência é limitado e carregado em memória; checkpoints e backups precisam de limites/retenção mais robustos para escala.
- O ZIP é fonte, não instalador offline. Runtimes e dependências precisam ser disponibilizados separadamente.

## 6. O que falta para chamar de IA programadora pronta

O caminho crítico é: validar Windows/notebook e isolamento; reunir corpus com permissão real; criar avaliador independente e desafios inéditos; desenvolver GPU/escala quando demonstrado necessário; treinar e avaliar um modelo próprio; integrar sua geração ao fluxo validado; medir regressões; fechar migração .NET/Roslyn e empacotamento.

O backlog detalhado (`BACKLOG.md`) contém 22 itens com prioridade e aceite. O projeto não deve ser liberado para atuar autonomamente em ShopAir ou outro sistema real com base apenas no sucesso dos testes de infraestrutura.

## 7. Critério prático de aceite desta entrega

O usuário consegue baixar o código, iniciar a plataforma local, cadastrar o laboratório, importar e consultar uma fonte, preparar/revisar uma alteração e executar os testes. Isso é verificável sem assinatura de IA. O laboratório consegue treinar um modelo minúsculo a partir de pesos aleatórios quando recebe dados compatíveis/autorizados.

**O critério final do planejamento — resolver autonomamente uma tarefa inédita usando um modelo próprio qualificado — ainda não foi alcançado.** A entrega separa o que já existe dessa etapa científica/de engenharia, em vez de apresentar interface e código de treinamento como inteligência pronta.
