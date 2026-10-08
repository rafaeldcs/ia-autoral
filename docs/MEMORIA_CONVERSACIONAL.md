# Memória por conversas

A LocalAuthor usa as mensagens recentes da conversa como contexto. Para uma
preferência continuar disponível em novas conversas do mesmo projeto, envie:

```text
Lembre-se: Preserve as cores da marca e pergunte antes de mudar o estilo.
O que você lembra deste projeto?
Esqueça: Preserve as cores da marca e pergunte antes de mudar o estilo.
```

Cada comando e confirmação ficam no histórico de **Conversas** do projeto.
O esquecimento desativa a nota para uso futuro; não apaga mensagens antigas.
Respostas comuns antigas ainda podem conter essa preferência no contexto da
conversa atual. Inicie outra conversa para trabalhar sem esse histórico.
Para corrigir uma nota, esqueça o texto antigo e registre o novo. Uma correção
comum orienta a conversa atual, mas não é promovida automaticamente a memória.
Não guarde credenciais ou dados privados nas notas.

São até 20 notas ativas de 600 caracteres por projeto, com referência à mensagem
que as originou, persistidas no banco do servidor. Dispositivos conectados ao
mesmo servidor compartilham essa memória; projetos diferentes permanecem
isolados. Há também limite de 200 registros distintos por projeto e quota geral.

No modo **Conversar com a IA local**, as notas ativas são incluídas como dados
no contexto do modelo, com orçamento de tokens. A resposta mostra a quantidade
usada e omitida. Não há garantia de obediência ou acerto do modelo. As notas não
concedem ferramentas, autorização de publicação ou permissão para executar
código. Guias, consulta de documentos e geração de imagens mantêm seus fluxos.

Não se trata de treino de pesos. As conversas não são aprovadas para treinamento
automaticamente. A revisão de exemplos, direitos das fontes, treinamento e
avaliação continuam sendo processos separados.

O diagnóstico anterior de marketing continua na campanha em **Ferramentas e
configurações → Marketing**. Esta entrega não transforma campanhas existentes
em conversas nem transfere notas automaticamente para o perfil de campanha.
Preferências de campanha e aprovação de estilo continuam explícitas no fluxo
de marketing.

Arquitetura: uma tabela adicional em `memory.sqlite3`, criada na inicialização;
nenhuma nova dependência ou API externa. Os comandos são interpretados apenas
quando uma mensagem humana inteira tem o formato indicado; código, citações,
pesquisa e saída do modelo não criam memórias automaticamente.
