# Orbit — Jira experimental local

**Rodada mais recente — Scrum/Kanban e gráficos:** veja [experiments/PROFISSIONAL.md](experiments/PROFISSIONAL.md). Dois projetos de demonstração identificados, limites de fluxo concorrente no servidor, métricas de ciclo/idade e teste em banco isolado. O modelo local falhou nos quatro pedidos inéditos desta rodada; as melhorias funcionais são uma referência de autoria de Codex. O candidato treinado novamente não foi ativado.

Protótipo funcional de gestão de projetos e tarefas inspirado nos fluxos de quadros e backlog do Jira, com identidade visual própria. Feito para o experimento solicitado por Rafael, em C#/.NET, Next.js e PostgreSQL. Interface em português, dados de demonstração, contas locais e níveis de acesso por workspace.

**Abrir:** http://127.0.0.1:3100

Na primeira abertura, crie sua conta administradora. Não há senha padrão. Depois, use **Equipe e acesso** para adicionar contas de gestores, colaboradores e leitores.

## Iniciar e parar

Pré-requisitos usados nesta máquina: Windows, Docker Desktop com engine Linux, .NET SDK 10.0.301, Node.js 24.11.1 e npm 11.6.2. O primeiro build precisa de internet para baixar pacotes NuGet/npm e a imagem PostgreSQL; a aplicação e o modelo não usam APIs de IA externas.

No PowerShell, dentro desta pasta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Orbit.ps1
```

O comando inicia o banco e os servidores ocultos, compila quando os artefatos estão ausentes e informa a URL. Executá-lo novamente com o sistema saudável apenas mostra o endereço. Não modifica a política permanente do PowerShell. Abra o Docker Desktop antes de iniciar.

```powershell
# Parar a aplicação mantendo o banco ligado:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Orbit.ps1
# Parar também o banco, sem apagar dados:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Orbit.ps1 -StopDatabase
# Após editar o código, pare a aplicação e recompile:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Orbit.ps1 -Rebuild
```

O encerramento só interrompe PIDs registrados cujo comando corresponda aos arquivos desta pasta. Portas ocupadas por uma instância não registrada devem ser liberadas pelo processo que a iniciou.

## Fluxos disponíveis

- Criar e alternar projetos, com chave própria e numeração de tarefas por projeto.
- Quadro com A fazer, Em andamento, Em revisão e Concluído; mover por arrastar ou pelo campo Status.
- Backlog separado e promoção de ideias para o quadro.
- Criar e editar tarefas, histórias e bugs; prioridade, responsável, etiquetas, data de entrega e pontos de esforço.
- Buscar por título, chave e etiquetas; filtrar prioridade, tipo e tarefas de Rafael.
- Comentários persistentes e histórico de criação/atualização.
- Controle de versão: uma edição desatualizada recebe conflito, preservando a mudança mais recente.
- Layout para desktop e celular, menu móvel, diálogos com Escape e foco contido.
- Aba **Experimento com IA**, com saída real, referência esperada e resultado da avaliação.

A versão atual acrescenta:

- **Sprints:** criar com meta e período, associar tarefas, iniciar e encerrar; uma sprint ativa por projeto. Pendências voltam ao backlog. Pontos planejados e entregues são preservados.
- **Relatórios:** distribuição por status, carga por responsável, atrasos, entregas em 30 dias, fluxo diário em 14 dias, velocidade por sprint e burndown com histórico real. Exportação CSV do fluxo diário.
- **Contas reais:** login e logout, senha com hash PBKDF2 do ASP.NET Identity, cookie HttpOnly/SameSite Strict, expiração em 8 horas e limite de tentativas de login.
- **Permissões verificadas no servidor:** administrador gerencia pessoas e todas as funções; gestor gerencia projetos/sprints e tarefas; colaborador cria/edita tarefas e comenta; leitor somente consulta. Mudanças de papel e desativação revogam sessões.
- **Auditoria administrativa:** criação de projetos, sprints, usuários, mudanças de acesso e ciclo das sprints.

Os papéis são globais neste workspace: todos os usuários ativos podem consultar seus projetos. Os responsáveis originais das tarefas continuam como dados demonstrativos; contas são criadas separadamente. Ainda não há isolamento por projeto/organização, recuperação ou troca de senha pela interface, SSO, MFA, épicos, anexos, notificações ou integrações externas. Acesso continua limitado a este computador; não foi publicado nem certificado para produção.

## Arquitetura e dados

```text
Navegador → Next.js (127.0.0.1:3100)
          → proxy servidor com segredo local
          → API C#/.NET (127.0.0.1:5088)
          → PostgreSQL Docker (127.0.0.1:55432)
```

- `frontend/`: Next.js 16.3.5, React 19.3.0, TypeScript; App Router, sem fontes externas. Versões exatas transitivas em `package-lock.json`. Telemetria do Next desabilitada pelo launcher.
- `backend/`: ASP.NET Core 10, Npgsql 10.0.3 e SQL parametrizado; transação para numeração/criação de tarefas; restrições no banco.
- PostgreSQL 18.6 Alpine, imagem fixada por digest no launcher; container `localauthor-orbit-postgres`; volume `localauthor-orbit-pg18`. Limites do container: 512 MB e 1 CPU.
- `scripts/smoke.py`: teste real com Edge/Playwright, API e banco; cria um projeto de QA exclusivo e remove apenas os registros daquele projeto ao terminar. Não testa carga ou usuários simultâneos reais.
- `artifacts/`: resultados e screenshots locais, ignorados pelo Git.

Segredos, PIDs e logs ficam em `%LOCALAPPDATA%\LocalAuthor\jira-experiment`, fora do código. `runtime.json` e `postgres.env` contêm credenciais: não compartilhar nem versionar. O proxy valida Host/Origin e mantém o token fora do JavaScript enviado ao navegador. A API também exige o segredo em cada chamada. Os serviços escutam somente em loopback.

O volume do Docker guarda os dados mesmo após parar/reiniciar. Não executar `docker volume rm` para esse volume se quiser preservá-los. Não há backup automático periódico. Foi criado um backup SQL privado antes desta evolução. A atualização idempotente em `backend/Upgrade.cs` adiciona contas, sessões, sprints, eventos e auditoria preservando as tarefas existentes. Ela é aplicada na inicialização; não representa um sistema completo de migrações versionadas.

## O que a nossa IA local fez

Rodada atual: continuação dos próprios pesos com 810 exemplos de xUnit/Playwright. **36/36 casos reservados aprovados**, contra 0/36 antes do novo treino: código bruto executado em sandbox, aprovado na implementação correta e capaz de detectar cada defeito controlado. O painel mostra esse resultado. São novos parâmetros de nove famílias conhecidas, não prova de todos os casos possíveis ou autonomia em qualquer projeto. Evidências: [experiments/GENERALIZACAO.md](experiments/GENERALIZACAO.md).

Rodada anterior preservada: com 126 exemplos, repetiu 9/9 exercícios vistos, mas acertou 0/18 com novos parâmetros. Histórico: [experiments/CODIGO_TESTES.md](experiments/CODIGO_TESTES.md).

Além do experimento inicial abaixo, foi executado novo treinamento com currículo de permissões, mantendo checkpoints e avaliações anteriores. Consulte [experiments/APRENDIZADO.md](experiments/APRENDIZADO.md).

No experimento inicial com LocalAuthor: corpus sintético autorizado, modelo próprio inicializado do zero, treinamento em CPU e geração de uma função de validação de título em C#. O corpus de treino foi importado na memória do projeto LocalAuthor; validação e teste não foram importados.

**O modelo não produziu código C# válido e errou o limite solicitado. Nenhuma saída dele foi executada ou aplicada.** A aplicação funcional foi implementada por Codex; a participação da IA local foi o experimento de treinamento/geração documentado, não a autoria do sistema.

Detalhes e localização das evidências: [experiments/RESULTADO.md](experiments/RESULTADO.md). A aba de experimento lê o relatório local quando ele existe; o funcionamento das tarefas independe do LocalAuthor estar aberto.

## Validação

**Versão atual:** 51 verificações reais de navegador/API aprovadas em 17/09/2026, incluindo login, quatro papéis, bloqueios na API, revogação de sessão, sprints, burndown, velocidade, exportação CSV, cartões, interface móvel e relatório de código de testes protegido por sessão. Evidência: `artifacts/smoke-v2-results.json`. Contas e projeto temporários de QA foram removidos por seus UUIDs.

Validação da versão anterior em 17/09/2026: builds de produção .NET e Next.js aprovados; **24 verificações de navegador/API aprovadas**; reinício completo de aplicação e PostgreSQL preservou as 12 tarefas de demonstração. Screenshots desktop e móvel inspecionadas. O teste de QA removeu seu próprio projeto ao terminar. Evidências em `artifacts/smoke-results.json` e `artifacts/restart-results.json`.

A regressão do LocalAuthor executou 140 testes: 137 passaram e 3 de links simbólicos foram pulados por falta de privilégio do Windows, com exceção explícita do runner. A cobertura dessa suíte permanece incompleta nesses três casos; isso não é uma qualificação do modelo como programador.

Execute o teste v2 apenas em workspace de QA ainda sem administrador; ele recusa substituir uma conta existente. Para repetir após configurar seu administrador, use uma cópia isolada do banco/configuração. Requer Python com Playwright e Microsoft Edge instalado. Nesta máquina:

```powershell
& 'C:\Users\rafae\OneDrive\Desktop\ia-autoral\.venv\Scripts\python.exe' .\scripts\smoke-v2.py
```

Os resultados atuais são escritos em `artifacts/smoke-v2-results.json`. O script `smoke.py` registra a suíte legada da versão sem autenticação; não é a entrada de validação atual. Os builds são `dotnet build backend/Orbit.Api.csproj -c Release` e `npm run build` dentro de `frontend`. Resultado de compilação é validação da aplicação implementada, não demonstração de competência do modelo local.

## Referências de implementação

Fluxos de [quadros do Jira](https://www.atlassian.com/software/jira/guides/boards/overview) e [backlog](https://support.atlassian.com/jira-software-cloud/docs/enable-the-backlog/); documentação oficial de [Route Handlers do Next.js](https://nextjs.org/docs/app/getting-started/route-handlers), [Minimal APIs do ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/minimal-apis/responses?view=aspnetcore-10.0), [Npgsql](https://www.npgsql.org/doc/basic-usage.html) e [restrições do PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html). Código e identidade visual próprios para este laboratório; sem vínculo com a Atlassian.

## Como as estatísticas são coletadas

A trigger `issue_event` registra criação, mudanças de status, estimativa e sprint no PostgreSQL. Itens antigos recebem uma linha de base na atualização; não inventamos datas históricas de conclusão. Burndown usa o último estado conhecido de cada tarefa em cada dia UTC, e preserva a situação anterior à devolução de pendências no fechamento. Velocidade compara pontos registrados no início com os concluídos no encerramento. Pontos não informados contam como zero e tarefas sem estimativa aparecem no relatório. Conclusões diárias contam tarefas distintas por dia; o total de 30 dias remove duplicatas entre dias.

Referências: [burndown do Jira](https://support.atlassian.com/jira-software-cloud/docs/what-is-the-sprint-burndown-report/), [relatórios do Jira](https://support.atlassian.com/jira-software-cloud/docs/track-and-analyze-your-teams-work-with-reports/) e [limitação de requisições do ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/performance/rate-limit?view=aspnetcore-10.0).

## Ensino de revisão e testes

Foi executado um currículo adicional com 90 exemplos e avaliação de revisão de C#, casos unitários e HTTP. Resultados e limites estão em [experiments/TESTES.md](experiments/TESTES.md) e na aba **Experimento com IA**. A aplicação não usa o modelo para autorizar ações nem executa suas propostas como código. Os testes xUnit/Playwright de referência são de autoria de Codex.
