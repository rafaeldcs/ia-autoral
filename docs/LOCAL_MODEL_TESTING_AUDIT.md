# Auditoria da capacidade de testar — 17/09/2026

> Registro da auditoria inicial, preservado. A correção de truncamento, o treinamento funcional e as novas execuções estão em [verificação posterior](FULL_VERIFICATION_20260917.md). O chat corrigido passou 36/36 casos antigos; os quatro pedidos livres continuam sem resposta utilizável. O novo laboratório cobre nove contratos explícitos do Orbit, sem qualificação geral.

O modelo local ainda não demonstrou capacidade de testar um sistema completo de forma autônoma. A aprovação de exercícios de laboratório não significa cobertura dos requisitos do Orbit ou do aplicativo LocalAuthor.

## Resultados desta execução

- Reexecução das respostas históricas sem alterações: **36/36** aprovadas na implementação correta e **36/36** com detecção do defeito controlado.
- Novas respostas pelo chat em execução: **24/36** aprovadas. Das 12 falhas, oito foram rejeitadas antes da execução por código incompleto e quatro entraram no runner, mas não produziram um teste aprovado. Todas as 12 respostas são prefixos de exatamente 120 caracteres dos códigos completos do diagnóstico, com a verificação final ausente ou cortada.
- Diagnóstico direto do checkpoint usado pelo chat, permitindo 220 tokens: **36/36** respostas idênticas ao código histórico validado. Essa chamada mediu geração; não foi uma alteração da configuração do chat nem outra execução dos trechos.
- Quatro desafios adicionais no chat (limites de senha, jornada completa, permissões por papel e concorrência WIP): **0/4 respostas utilizáveis**, por revisão explícita de Codex. Nenhuma implementou o contrato solicitado. Essas saídas não foram executadas; o resultado não é uma contagem de testes funcionais rodados e reprovados.
- Verificação da infraestrutura: **16 testes do laboratório** aprovados e **150 testes do núcleo** aprovados, com três testes de links simbólicos indisponíveis no Windows. Esses números são testes de Codex, não desempenho da IA.

| Família dos exercícios | Reexecução histórica | Chat atual |
| --- | ---: | ---: |
| Limite inclusivo | 4/4 | 4/4 |
| Exceção por texto vazio | 4/4 | 4/4 |
| Multiplicação | 4/4 | 4/4 |
| HTTP 401 | 4/4 | 4/4 |
| HTTP 403 | 4/4 | 4/4 |
| Conflito de versão | 4/4 | 0/4 |
| Contagem de itens no navegador | 4/4 | 0/4 |
| HTML como texto | 4/4 | 0/4 |
| Foco pelo teclado | 4/4 | 4/4 |

Evidências em `%LOCALAPPDATA%\LocalAuthor\exports\jira-experimental`:

- `testing-audit-historical-20260917T210634067160Z/report.json`: execução real das respostas originais e resultados normal/mutante por caso.
- `testing-audit-chat-20260917T210635928402Z/report.json`: pedidos novos ao servidor real, respostas brutas, identidade do modelo e resultados de execução.
- `testing-audit-chat-20260917T210635928402Z/review.json`: revisão dos quatro desafios adicionais e confirmação dos 12 cortes.
- `testing-audit-generation-20260917T210922Z.json`: diagnóstico direto com 220 tokens. Hash do checkpoint ativo: `3c4bb229e4358440e4808c35fc762ba1a64eb815db7744a1aa88f82d9fd1b391`.

## O que foi verificado

`scripts/audit-local-testing.py` separa a repetição das 36 respostas originais da avaliação de novas respostas solicitadas ao chat em execução. Confere os hashes do checkpoint histórico e dos casos congelados, a aprovação das referências na mesma imagem Docker imutável e os canários da sandbox. Cada resposta é preservada sem correção e recebe resultados separados para a implementação correta e o defeito controlado. Nenhum código gerado é executado no Windows ou aplicado aos projetos.

Os casos já foram observados em avaliações anteriores: esta auditoria é regressão, não uma avaliação inédita. O avaliador e os critérios são de autoria de Codex. Os trechos submetidos aos testes são produzidos pelo modelo local. O modelo não escolheu a bateria nem acionou o Docker por conta própria.

## Cobertura efetiva

| Necessidade | Evidência da IA | O que ainda falta demonstrar |
| --- | --- | --- |
| Regras unitárias | Limite inclusivo, exceção por texto vazio, multiplicação | Regras novas, combinações e casos extremos derivados de requisitos |
| Login | GET que retorna 401 em API de laboratório | Login real, sessão, expiração e persistência |
| Níveis de usuário | GET que retorna 403 em API de laboratório | Matriz de papéis e ações no backend real |
| Concorrência | Dois PUT sequenciais com versão repetida | Disputa simultânea por vaga WIP e consistência no PostgreSQL |
| Navegador | Adição de itens, HTML como texto e foco por Tab | Jornada entre telas, recarga e confirmação na API/banco |
| Scrum e Kanban | Nenhum fluxo completo na bateria de 36 casos | Criar/iniciar/encerrar sprint, backlog, limites e transições |
| Estatísticas | Multiplicação simples não valida relatórios | Eventos, burndown, velocidade, ciclo e dados ausentes |
| Usabilidade e responsividade | Um exercício de foco | Mensagens de erro compreensíveis, teclado completo, celular e avaliação com usuários |
| Desempenho e recuperação | Sem evidência de testes produzidos pela IA | Carga, interrupção de rede, reinício e recuperação de dados |

O laboratório HTTP usa regras pequenas embutidas. O laboratório de navegador usa `page.setContent`, sem navegação ao Orbit e sem PostgreSQL. O exercício denominado `xss` verifica a ausência de um elemento `li b`; não é uma auditoria completa de XSS. O teste de conflito verifica o segundo status 409, mas não afirma o primeiro status 200. Essas limitações impedem declarar cobertura completa mesmo com 36 aprovações.

As 55 verificações profissionais registradas no Orbit, os testes do instalador e os testes do núcleo LocalAuthor são referências implementadas por Codex. Não entram no placar de capacidade do modelo. Não foram repetidas as 55 verificações do Orbit nesta auditoria.

## Diferença entre laboratório e aplicativo

O histórico de 36/36 pertence a `generalization-20260917T171336Z`. O chat atual usa `engineering-20260917T173320Z`. Além da seleção de outro checkpoint, o chat permite somente 120 tokens de saída, enquanto a avaliação original permitia 220. Nos exercícios de conflito, contagem e HTML, a saída do chat termina no meio do código. Pedir para executar esse texto não produz um teste válido.

O modo padrão de orientação usa guias escritos, e o modo neural recebe apenas a mensagem curta (até 180 bytes), sem histórico ou arquivos. Não existe ligação autônoma entre essa geração e a execução de uma suíte funcional completa. Registrar feedback não altera os pesos: esta auditoria não realizou treinamento nem trocou o modelo ativo.

## Reprodução

Com o servidor LocalAuthor e o Docker disponíveis, a imagem local `localauthor-testing-lab:1` e o projeto Orbit existente:

```powershell
python scripts/audit-local-testing.py --orbit-root C:\caminho\jira-local-experimental --scope historical
python scripts/audit-local-testing.py --orbit-root C:\caminho\jira-local-experimental --scope chat
```

As saídas ficam em diretórios novos `testing-audit-*` sob `%LOCALAPPDATA%\LocalAuthor\exports\jira-experimental`, fora do Git. A avaliação do chat cria uma conversa identificada como auditoria no projeto Orbit. Nenhum relatório anterior é substituído. `state=completed` significa que a auditoria terminou; consulte `passed/total` para o resultado do candidato.

## Critério para o próximo marco

Corrigir e verificar o corte de saída do chat. Depois, em um ambiente descartável, exigir que o modelo produza um teste de fluxo completo a partir de um contrato novo, confirme persistência, passe na aplicação correta e detecte um defeito inserido. A resposta original deve ser executada sem reparos. Casos usados para ensinar devem sair da avaliação inédita. A aprovação desse marco ainda não substituirá a matriz de cobertura acima.
