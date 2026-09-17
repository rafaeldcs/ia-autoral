# Histórico

## Não publicado — continuação Windows de 2026-09-17

Corrigidos bloqueio SQLite no backup Windows e teste de rollback com caminhos 8.3.
Backup/restauração em streaming com validação prévia à publicação, proteção de caminhos
Windows e preservação do backup anterior em falhas. Relatórios de testes rejeitam
cobertura incompleta silenciosa. Adicionados teste HTTP do host .NET, validação
PowerShell integrada, fluxos de navegador e matriz CI ampliada.

Notebook: 137 testes, 134 aprovados, três ignorados por privilégio de symlink e nenhuma
falha/erro; navegador e onze verificações do host aprovados. Evidência e pendências
em `docs/PROGRESS_WINDOWS.md`. Sem corpus/modelo qualificado/CUDA ou auditoria Docker.

## 0.1.0 — 2026-09-17

Primeira implementação-fonte: núcleo local Python, interface web, memória SQLite/FTS5, coleta HTTPS opcional com cache, revisão manual/importada de alterações com hashes e recuperação, fila de tarefas, backup e laboratório neural CPU próprio. Inclui host .NET opcional, scripts de inicialização/publicação e workflow CI.

Validação: 119 testes aprovados em Linux/Python 3.13.5/NumPy 2.3.5. Navegação Playwright bloqueada pela política administrativa do ambiente. Não há validação de GPU, Docker real, .NET ou Windows.

O repositório remoto não foi criado; o conector autenticado ofereceu somente operações de leitura. A versão não contém modelo qualificado, geração autônoma de patches, Roslyn, CUDA, corpus de programação aprovado ou pacote binário offline.
