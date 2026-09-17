# Verificação de 17/09/2026

O defeito que cortava respostas do chat em 120 tokens foi corrigido para o limite de 220 utilizado na avaliação. O treinamento funcional alterou os pesos locais e produziu 36 trechos aprovados contra o Orbit real, com 36 defeitos controlados detectados. “100% aprovado” abaixo se refere exclusivamente à bateria enumerada, não a todos os comportamentos possíveis do sistema.

## Resultados executados

| Bateria | Resultado | Autoria e alcance |
| --- | ---: | --- |
| Testes funcionais novos | 36/36 + 36/36 defeitos detectados | Código original do modelo; Orbit com API .NET, Next.js, Playwright e PostgreSQL descartável |
| Chat após ativar a habilidade | 36/36 respostas idênticas | Comparação byte a byte com os testes já executados; não conta como mais 36 execuções |
| Referências do laboratório funcional | 9/9 + 9/9 defeitos detectados | Codex; valida o runner antes do modelo |
| Regressão de testes pelo chat corrigido | 36/36 + 36/36 defeitos detectados | Modelo anterior; pequenos exercícios do laboratório original |
| Núcleo LocalAuthor no Linux | 161/161, nenhum ignorado | Codex; inclui os controles de aprovação e os testes de links simbólicos |
| Núcleo LocalAuthor no Windows | 158 aprovados, 3 ignorados | Mesma suíte; três testes de links simbólicos exigem privilégio indisponível. Não são classificados como aprovados no Windows |
| Simulação profissional Orbit | 55/55 | Codex; fluxo real, papéis, Scrum/Kanban, dados sintéticos e banco PostgreSQL 18 descartável |
| Testes .NET do Orbit | 20/20 | Suíte existente de referência, nenhum ignorado |
| Interface do chat LocalAuthor | 27/27 | Codex; navegador, segurança de texto, teclado, persistência e experiência básica |
| Rede e aplicativo instalado | 23/23 | Codex; HTTPS real, autenticação, certificado, revogação, instalador e cliente nativo |

Na simulação profissional, 30 amostras da consulta de fluxo resultaram em p50 de 56,15 ms e p95 de 65,32 ms. O quadro ficou pronto em 449,61 ms, com 191 tarefas. Houve disputa entre oito gravações por duas vagas. São medidas desta máquina em loopback, com um navegador; não comprovam desempenho em qualquer rede ou volume.

## Aprendizado preservado e limites

O novo candidato acertou 36/36 exemplos funcionais reservados, mas 34/36 exemplos antigos na regressão de geração. Ele foi qualificado somente para mensagens `Teste JS h:`; o modelo anterior continua atendendo os demais pedidos. A certificação verifica fonte, casos únicos, resultados normais, falhas por asserção, identidade da imagem e hash dos pesos. A atualização do servidor preserva banco, conversas e modelo anterior.

Após reiniciar o servidor ocioso com backup, o chat entregou 36/36 respostas funcionais idênticas às executadas. Os dois casos antigos que o candidato novo errava também foram pedidos ao servidor atualizado: ambos usaram o modelo anterior e reproduziram as respostas corretas já validadas (2/2). O arquivo `old-skill-routing.json` conserva essa verificação.

Os quatro pedidos livres da auditoria inicial continuam com **0/4 respostas utilizáveis**, por revisão de Codex. Nenhuma dessas respostas foi executada. Esse resultado permanece reprovado e não é substituído pelo placar dos contratos novos. A IA ainda não demonstrou que consegue planejar e testar um sistema inteiro autonomamente.

Os testes novos cobrem nove famílias com auxiliares de ações fornecidos pelo laboratório. A IA escreve os trechos e as asserções; Codex definiu o plano, implementou auxiliares e executou a infraestrutura. As variantes reservadas não são famílias inéditas. Leia os contratos e limites em [laboratório funcional](FUNCTIONAL_TESTING_LAB.md).

Não foram comprovados todos os navegadores, usuários simultâneos em outras máquinas, falhas reais de rede, recuperação de desastre, matriz completa de permissões, todas as estatísticas ou acessibilidade integral. Uma bateria finita verde não autoriza afirmar ausência de qualquer erro.

## Evidências preservadas

Os relatórios brutos, corpus e checkpoints ficam fora do Git. Nenhum segredo ou senha de usuário faz parte do treinamento.

- `%LOCALAPPDATA%\LocalAuthor\exports\functional-tests-20260917T212312Z\report.json`: treino, seleção por validação, respostas finais e regressão.
- Mesmo diretório: `frozen-test-cases.json`, `functional-references.json`, `functional-execution.json` e arquivos `chat-verification-*`.
- `%LOCALAPPDATA%\LocalAuthor\exports\functional-testing-report.json`: certificação da habilidade, hashes das evidências e identidade do checkpoint.
- `%LOCALAPPDATA%\LocalAuthor\exports\jira-experimental\testing-audit-chat-20260917T213740466666Z\report.json`: 36 testes pelo chat corrigido e os quatro pedidos livres reprovados.
- `reports/full-core-linux.final.log`, `reports/full-verification-windows.json`, `reports/chat-smoke.json`, `reports/lan-smoke.json`: núcleo, interface e rede.
- No projeto Orbit, `artifacts/professional/results.json`, `performance.json` e `full-verification.trx`: referência profissional e .NET.
- Backups anteriores aos reinícios: diretórios `before-chat-output-fix-*` e `before-functional-skill-*` sob `%LOCALAPPDATA%\LocalAuthor\exports`.

As evidências anteriores foram preservadas, incluindo a primeira falha de infraestrutura do laboratório e a auditoria em que o chat aprovou apenas 24/36 casos. Os resultados desta página não apagam essas falhas nem as reclassificam retroativamente.
