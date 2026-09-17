# Continuação no notebook — 17/09/2026

Trabalho realizado em `C:\Users\rafae\OneDrive\Desktop\ia-autoral`.
Os relatórios originais descrevem a entrega inicial. As alterações desta continuação
estão locais, sem commit/push. Documentos não foram tratados como autorização para
publicar, mudar a visibilidade do GitHub ou treinar com dados privados.

## Evidências atuais

| Verificação | Resultado |
|---|---|
| Python | **137 testes: 134 aprovados, 0 falhas, 0 erros, 3 ignorados**; `reports/test-results-windows.json` |
| Cobertura incompleta | Três casos de symlink sem privilégio Windows. Exceção explícita por ID; `complete=false`. Testes reais de junction/hardlink executaram. |
| Navegador | Playwright/Edge: dez verificações de fluxo, sem erro JavaScript; `reports/ui-smoke-windows.json`, `ui-desktop.png`, `ui-mobile.png` |
| .NET | SDK 10.0.301; host e laboratório compilados em Release sem avisos/erros; onze verificações HTTP aprovadas; `reports/dotnet-smoke-windows.json` |
| Recuperação | Round-trip, streaming, corrupção, falha de escrita, quotas, hardlinks, junctions e caminhos perigosos testados com dados temporários |
| Serviço já aberto | `/api/health` autenticado: OK, offline, runner desativado e modelo não qualificado. Nenhum dado dessa instância foi alterado. |
| Motor CPU | 3.016 parâmetros, 90 passos, 720 tokens processados; perda 5,5471 → 0,01704 em padrão repetido; `reports/neural-smoke-windows.json` |
| Hardware | Windows 11, Python 3.14.7, NumPy 2.3.5, aproximadamente 16 GiB RAM, RTX 2060 com 6 GiB VRAM; `reports/hardware-windows.json` |
| Disco | Volume de aproximadamente 476 GiB, com 225 GiB livres na medição; diferente da estimativa antiga de 256 GB |
| Docker | CLI instalada; daemon `dockerDesktopLinuxEngine` indisponível. Isolamento real não auditado. |
| GitHub | `rafaeldcs/ia-autoral`, **público**, HEAD `ebe37ff86a7bdc0939a55de4795528391376643e`; diverge do plano privado |
| CI anterior | [Execução 35221366039](https://github.com/rafaeldcs/ia-autoral/actions/runs/35221366039): Linux e .NET aprovados, Windows falhou. Não é validação das alterações atuais. |

O teste neural mede memorização numérica, não competência de programação. Nenhum
corpus real foi usado e nenhum peso foi exportado. A validação offline por configuração
e testes simulados não substitui teste com saída de rede bloqueada pelo sistema operacional.

## Implementação e correções

- **SQLite:** fechamento explícito da conexão de backup. O contexto transacional de
  SQLite não fechava a conexão, deixando o snapshot bloqueado no Windows (`WinError 32`).
  Um teste de regressão verifica que as duas conexões são fechadas.
- **Backup/restauração em streaming:** cópia/hash em blocos de 1 MiB. O ZIP só substitui
  o anterior após escrita e `fsync`; erros preservam o backup anterior. A restauração
  valida hashes, banco e configurações em pasta temporária antes de publicar o destino.
  Mantidos limites de 512 MB de conteúdo e 20.000 entradas, rotação de token, offline
  e runner desabilitado. Ainda não é backup incremental, criptografado ou em outro disco.
- **Caminhos:** rejeição de nomes reservados Windows, colisões de nomes por caixa,
  conflitos arquivo/diretório, junctions, links e importação de credenciais/locks.
- **Relatório de testes:** falhas de subtestes registradas; descoberta vazia/reduzida,
  dependência ausente, falha esperada e skip não autorizado impedem aprovação. Exceção
  dos três testes de symlink é opcional e mantém cobertura incompleta. CI permanece estrito.
- **Rollback no CI Windows:** o TEMP remoto usava caminho curto 8.3, enquanto o código
  usa caminho canônico. A comparação do teste impedia a injeção da falha. Agora usa
  caminhos resolvidos e exige que a primeira escrita ocorra e a segunda realmente falhe.
- **Navegador:** substituídas esperas incompatíveis com CSP por assertions de elementos,
  sem afrouxar CSP. Testados token inválido, consulta, conteúdo malicioso inerte,
  proposta/revisão/aplicação, teclado e seis seções sem overflow horizontal a 390 px.
- **.NET/CI:** teste HTTP do host cobre autenticação, origem/Host, proxy JSON, consulta
  e indisponibilidade do backend. Workflow ampliado para Python 3.13/3.14 em Windows/Linux,
  .NET nos dois sistemas e Chromium no Linux. Novo workflow ainda não executado remotamente.

## Reproduzir e carregar as correções

Na raiz, com Edge e SDK .NET instalados:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt -r requirements-dev.txt
.\scripts\validate-windows.ps1 -AllowUnavailableSymlinks
```

Retire `-AllowUnavailableSymlinks` para exigir todos os testes. Sem privilégio de symlink,
a validação estrita termina com erro e lista os casos não executados. Nenhuma política
do Windows foi alterada. Playwright é dependência de desenvolvimento, não do runtime.
O teste .NET requer porta 5080 livre e não para serviços existentes. Relatório geral:
`reports/windows-validation.json`.

O servidor aberto antes das alterações pode ter módulos antigos em memória. Encerre-o
com **Ctrl+C** no terminal original e execute `.\scripts\start.ps1` novamente. Não remova
o lock de uma instância ativa. Os testes desta continuação usaram dados temporários.

## Os 22 itens após esta continuação

| Item | Situação |
|---|---|
| REM-001 | Parcial: remoto/CI anterior verificados; visibilidade privada e CI das alterações atuais pendentes. |
| REM-002 | Parcial: notebook/UI/testes/recuperação validados; faltam symlinks e bloqueio de saída de rede no SO. |
| REM-003 | Pendente: Docker ativo e imagem confiável auditada. |
| REM-004 | Pendente: fontes reais e autorização do corpus. Nenhuma pasta empresarial foi usada. |
| REM-005 | Pendente: avaliador independente e tarefas inéditas de programação. |
| REM-006 | Pendente: modelo qualificado; treino numérico não atende o aceite. |
| REM-007 | Pendente: integração generativa de modelo qualificado. |
| REM-008 | Pendente: CUDA; somente hardware identificado. |
| REM-009 | Parcial: host C# compilado/exercitado; domínio/infraestrutura continuam Python. |
| REM-010 | Pendente: Roslyn semântico. |
| REM-011 | Pendente: instalador e runtimes/dependências offline. |
| REM-012 | Parcial: junction/hardlink testados; faltam ACLs, usuário isolado, symlinks e auditoria de corridas. |
| REM-013 | Pendente: pesquisa live e regras semânticas de versão; instância mantida offline. |
| REM-014 | Pendente: relevância e expansão de conceitos. |
| REM-015 | Parcial: fluxos centrais/teclado/mobile/erros/conteúdo inerte; auditoria completa de acessibilidade e fluxos secundários pendentes. |
| REM-016 | Pendente: loader/treino em escala. Streaming de backup não é loader de treino. |
| REM-017 | Pendente: promoção/rollback de modelo. |
| REM-018 | Parcial: limites de backup testados; quotas globais e retenção pendentes. |
| REM-019 | Parcial: streaming e falhas simuladas; faltam cópia externa e interrupção abrupta/queda física. |
| REM-020 | Parcial: evidência da suíte mais rigorosa; avaliador de projetos independente pendente. |
| REM-021 | Parcial: diagnóstico/relatórios reproduzíveis; migrações e manual de incidentes completo pendentes. |
| REM-022 | Pendente: expansão após avaliação separada. |

Próximo marco de capacidade: corpus autorizado, avaliador independente e executor
auditado. A plataforma continua sendo um protótipo com laboratório CPU.
