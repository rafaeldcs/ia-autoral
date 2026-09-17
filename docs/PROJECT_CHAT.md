# Projetos, conversas e ensino de engenharia

Entrega local de 17/09/2026. A entrada `http://127.0.0.1:8765/` agora organiza pastas e conversas. A interface anterior permanece em `/advanced`. O Orbit continua independente, na porta 3100. O token local de acesso não mudou.

## Uso

1. Entre com o token local, mantido somente na memória da página.
2. Adicione uma pasta existente e selecione o projeto na lateral. Isso não indexa nem altera os arquivos.
3. Abra **Orientações do projeto** para escolher Scrum ou Kanban, registrar limite de WIP e definir o critério de pronto.
4. Inicie uma conversa. O histórico fica no SQLite privado, separado por projeto.
5. Escolha o modo de resposta conscientemente:

| Modo | O que realmente faz |
|---|---|
| Orientação do projeto | Guias determinísticos escritos pelo Codex, com referências oficiais e o critério de pronto configurado. Não é geração neural. |
| Consultar memória local | Recupera trechos indexados/importados apenas desse projeto. Não inclui fontes globais ou de outro projeto. |
| Modelo neural experimental | Executa inferência nos pesos próprios do candidato avaliado. Recebe somente a mensagem atual, com até 180 bytes; gera até 120 tokens. Não recebe arquivos ou histórico e não executa a resposta. |

As conversas persistem, mas não se tornam automaticamente contexto neural nem dados de treinamento. O modelo ainda não sustenta uma conversa geral como um modelo de fronteira. A escolha do candidato no chat é experimental e não promove sua qualificação como programador. A coleta de URLs permanece nas ferramentas avançadas, com cache, domínio permitido e respeito à configuração offline; a interface não afirma ter pesquisado quando usa um guia local.

As preferências Scrum/Kanban são orientações: este workspace não é um quadro com aplicação automática de limites de WIP. O Orbit continua sendo o aplicativo de gestão de tarefas e Sprints. Scrum e Kanban organizam trabalho; não substituem os critérios de qualidade do código.

## Princípios ensinados

Clareza de nomes, responsabilidade focada, simplicidade sem abstrações antecipadas, tratamento explícito de erros, autorização no servidor, testes efetivamente executados, revisão de diferenças e consulta à documentação da versão usada. Método e critérios são adaptáveis por projeto; não há regra de que toda equipe precise usar os dois métodos ao mesmo tempo.

Referências consultadas em 17/09/2026:

- [Convenções de C# — Microsoft](https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions): clareza, consistência e ferramentas de análise; as convenções devem ser adaptadas ao contexto.
- [Scrum Guide](https://scrumguides.org/scrum-guide.html): objetivos, inspeção e Definition of Done.
- [The Kanban Guide](https://kanbanguides.org/the-kanban-guide/): fluxo explícito, controle de WIP e métricas de fluxo.

Nenhum texto desses sites foi incorporado ao treino. O curso usa exercícios sintéticos originais, com origem e permissão registradas.

## Treinamento real desta rodada

Continuação do próprio Transformer de 132.992 parâmetros, sem API de IA, pesos externos ou alteração de arquitetura. Foram usados **192 exemplos novos** em oito temas, com **810 exemplos anteriores disponíveis para revisão**, 32 exemplos de validação e 32 de teste. O treino fez 1.500 passos, alternando os exercícios novos com os anteriores para reduzir esquecimento. A seleção do checkpoint usou somente geração livre na validação.

Resultado: **32/32 decisões guiadas aprovadas** no teste reservado. As frases pertencem às mesmas famílias vistas no treino e variam o identificador do exercício; isso é uma avaliação limitada de reprodução das decisões, não evidência de raciocínio amplo ou refatoração autônoma. Há casos positivos e negativos para evitar que uma resposta constante seja aprovada.

O candidato também reproduziu exatamente **36/36 respostas de código da bateria anterior**. Essa rodada de regressão comparou as gerações; não reexecutou os testes gerados. O relatório registra `executed=false` para evitar confusão com a execução anterior em Docker.

Evidências privadas em `%LOCALAPPDATA%\LocalAuthor`:

- `exports\engineering-report.json`: resumo atual, respostas originais, limitações e regressão.
- `exports\engineering-20260917T173320Z\report.json`: registro datado.
- `models\engineering-20260917T173320Z\best-validation.npz`: pesos próprios, com hash de integridade.
- `corpus\engineering-20260917T173320Z\manifest.json`: corpus sintético e partições.

O script desta rodada está no laboratório do Orbit: `C:\Users\rafae\OneDrive\Desktop\jira-local-experimental\scripts\train-engineering.py`. Ele usa o treinamento supervisionado próprio já testado nesse laboratório; não foi adicionado framework de IA. Pesos anteriores e resultados históricos foram preservados.

## Arquitetura e validação

Foram adicionados `ChatService`, guias de engenharia e três tabelas SQLite: preferências, conversas e mensagens. A migração é aditiva e idempotente, sem alterar as tabelas anteriores. Uma cópia SQLite anterior à atualização foi salva em `exports\before-chat-memory-*.sqlite3`. Não é um backup completo de todos os modelos e arquivos.

O chat usa a autenticação, verificação de origem e CSP existentes. Limites: 200 conversas por projeto, 200 mensagens por conversa, 8.000 caracteres por pedido e até 32 MB para conteúdo/metadados das mensagens, limitado também pela quota configurada. HTML é exibido como texto. Pedidos com possíveis segredos e o token local são bloqueados; o detector não é uma garantia de detectar todo segredo possível. Uma falha/cancelamento de geração não salva metade de uma troca.

Validação: 149 testes locais, com 146 aprovações e 3 casos de symlink não executados por falta de privilégio no Windows; 13 verificações reais em Edge, incluindo geração do modelo pelo chat, recarga e mobile; 10 fluxos da interface avançada preservados. Foram verificados isolamento, persistência, quota, cancelamento, origem das respostas, preservação do pedido e bloqueio de segredos. Resultados em `reports/chat-test-results.json`, `reports/chat-smoke.json` e `reports/advanced-ui-smoke.json`.

Próximos desafios de capacidade: variações linguísticas realmente inéditas, refatorações verificadas por testes, contexto entre arquivos e conversas, pesquisa com evidências verificáveis e criação de propostas revisáveis. A interface pronta não significa que esses desafios já foram resolvidos pelo modelo.
