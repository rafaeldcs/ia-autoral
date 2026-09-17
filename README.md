# LocalAuthor — IA local autoral (protótipo 0.1.0)

Plataforma local de conhecimento e revisão de código, acompanhada de um **motor neural experimental próprio em CPU**. Desenvolvida nesta conversa para Rafael, a partir do planejamento de 17/09/2026.

**Não é um substituto pronto do Codex. Não há modelo treinado e qualificado para programar.** O fluxo de revisão recebe propostas manuais/importadas; não apresenta essas propostas como geração de uma IA. Nenhuma API de IA, peso pré-treinado ou embedding externo é usado.

## Situação da entrega

**Escrita e código:** modo de entrada Código, cópia literal, rejeição de texto inválido sem substituição e aviso de geração incompleta implementados e testados. A ativação do backend na instância existente exige reinício, que ficou pendente. O novo candidato neural de escrita falhou nos pedidos reformulados e não foi ativado. Consulte [WRITING_AND_CODE.md](docs/WRITING_AND_CODE.md).

**Projetos e chat (17/09/2026):** a entrada na porta 8765 agora oferece pastas por projeto, conversas persistentes, orientações de qualidade e Scrum/Kanban. Há modos distintos de guia estruturado, consulta à memória e inferência do modelo próprio experimental. A interface anterior continua em `/advanced`. O novo curso teve 32/32 decisões guiadas aprovadas, com limitações explícitas; não equivale a um assistente geral. Consulte [PROJECT_CHAT.md](docs/PROJECT_CHAT.md).

**Continuação no notebook Windows em 17/09/2026:** correções de backup/recuperação,
validação real do host .NET e navegação executadas. Consulte o
[relatório atual e os 22 itens atualizados](docs/PROGRESS_WINDOWS.md).

| Item | Situação |
|---|---|
| Núcleo, API, memória SQLite, revisão e laboratório CPU | Python; versão inicial testada em Linux e continuação no notebook Windows |
| Modelo | Transformer e treinamento próprios, com NumPy apenas para operações numéricas |
| Testes atuais no Windows | 137 casos: 134 aprovados, 0 falhas/erros, 3 ignorados por privilégio de symlink; `reports/test-results-windows.json` |
| Interface web em português | Fluxos centrais testados com Playwright/Edge, teclado e viewport mobile |
| Host ASP.NET Core .NET 10 | Compilado no notebook sem avisos/erros; onze verificações HTTP aprovadas |
| GPU / CUDA | NÃO implementado |
| GitHub remoto | `rafaeldcs/ia-autoral` existe e está público; CI anterior falhou no Windows. Correções atuais ainda locais |
| Hardware e Docker | Windows medido; RTX 2060 de 6 GiB detectada, sem backend CUDA. Docker instalado, daemon indisponível na verificação |

O plano original previa predominância C#/.NET. **Esta entrega tem um núcleo funcional Python e um host .NET opcional**, não uma migração completa para C#. O SDK ausente na implementação inicial foi encontrado no notebook; o host agora foi compilado e exercitado.

## Iniciar no Windows

Pré-requisito: Python 3.11+ instalado. Para iniciar a plataforma, não é necessário instalar bibliotecas via pip, possuir uma GPU ou autenticar em serviço externo.

Extraia o ZIP, entre na pasta `ia-local-autoral` e execute:

```powershell
.\scripts\start.ps1
```

O script mostra o token **local** no seu console e inicia o serviço em `http://127.0.0.1:8765`. Abra o endereço e informe esse token na interface. Ele não é uma chave de serviço externo. Não o publique nem o envie pelo chat.

Caso scripts PowerShell não sejam permitidos na máquina, execute diretamente, sem alterar a política do sistema:

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONUTF8 = "1"
py -3 -m localauthor init
py -3 -m localauthor token
py -3 -m localauthor serve
```

No Linux/macOS, a entrada equivalente é `bash scripts/start.sh`. A versão inicial foi testada em Linux e a continuação no Windows; macOS continua sem validação. O diretório de dados padrão é `%LOCALAPPDATA%\LocalAuthor` no Windows e `~/.localauthor` nos demais sistemas. `LOCALAI_HOME` permite escolher outro diretório, **fora dos projetos e do repositório**.

**Use a distribuição-fonte completa.** O servidor busca os arquivos em `ui/` ao lado de `src/`; instalar somente um wheel do pacote Python não fornece a interface nesta versão.

## Primeiro uso sem treinamento

1. Cadastre a pasta `examples/laboratory` como projeto de laboratório, usando seu caminho absoluto.
2. Importe uma nota/documento ou indexe os arquivos permitidos do projeto.
3. Faça uma consulta. O resultado apresenta trechos e fontes, não uma resposta generativa fingindo entendimento.
4. Crie uma tarefa, abra o arquivo do snapshot, prepare uma proposta JSON e revise o diff.
5. Só aplique uma proposta após conferi-la. O executor de testes vem desabilitado; aplicar sem testes exige um aceite específico e não produz uma alegação de validação.

Comece em uma cópia de laboratório, não em produção. Teste backup/restauração antes de cadastrar repositórios importantes.

## Recursos implementados

- API local com autenticação, limite de corpo, verificação de origem/Host e política de conteúdo para a interface.
- Fontes, versões por hash, trechos com linhas, busca FTS5 e isolamento de projetos; importação idempotente e exclusão de derivados.
- Relações com evidência e status, registradas via API; pesquisa lexical, não busca semântica aprendida.
- Coleta opcional de URLs HTTPS autorizadas: cache, TTL, ETag/Last-Modified, robots.txt, limites e bloqueio de destinos privados. Offline por padrão; não existe busca geral da internet ou navegação autônoma ilimitada.
- Snapshot, propostas de até oito arquivos, diff, detecção de conflito, revisão, journal de recuperação e registro de feedback.
- Fila persistente, cancelamento cooperativo e reconhecimento de tarefas interrompidas.
- Executor Docker restrito e opt-in, sem fallback para shell do host. A construção dos comandos foi testada; o isolamento real ainda não.
- Tokenizadores byte/BPE, autodiferenciação, Transformer causal, AdamW, validação de corpus, treinamento e checkpoints retomáveis, todos sem frameworks de IA ou pesos prontos.
- Backup/restauração em streaming, com hashes, validação em pasta temporária e rejeição de caminhos perigosos; até 512 MB e com servidor parado.

## Testar e experimentar o motor neural

O motor e sua bateria numérica usam a versão testada `numpy==2.3.5`. Ela é uma dependência local de matemática, não um modelo. O runtime HTTP/banco não precisa dela.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\scripts\test.ps1
```

A suíte agora rejeita testes ignorados por padrão. Se o Windows não permitir criar
symlinks, `scripts/test.ps1 -AllowUnavailableSymlinks` aceita somente os três casos
específicos e registra cobertura incompleta. Falta de NumPy continua sendo falha.
Para incluir navegador, hardware e .NET, siga `docs/PROGRESS_WINDOWS.md`.

A instalação acima baixa NumPy quando não estiver disponível no cache. Para um computador sem internet, forneça previamente um wheel compatível e use `pip install --no-index --find-links CAMINHO_DO_WHEEL -r requirements-training.txt`. O ZIP não inclui Python, NumPy, .NET, drivers ou instalador offline.

Para treinar com **seus dados efetivamente autorizados**, prepare o manifesto descrito em `docs/DATASET.md`, fora do Git. Em um PowerShell com `PYTHONPATH=src`:

```powershell
.\.venv\Scripts\python.exe -m localauthor validate-dataset C:\LocalAuthorData\corpus\manifest.json
.\.venv\Scripts\python.exe -m localauthor train C:\LocalAuthorData\corpus\manifest.json --output C:\LocalAuthorData\models\experimento-001 --config experiments\configs\smoke-cpu.json --steps 100
.\.venv\Scripts\python.exe -m localauthor generate C:\LocalAuthorData\models\experimento-001\latest.npz --prompt "public " --max-tokens 32
```

Saída gerada nesse experimento **não constitui solução de programação**. O modelo inicial tem poucos milhares de parâmetros para validar a matemática; o motor CPU limita a configuração a dois milhões. Não há modelo de 34 milhões nem uso da RTX 2060 nesta versão.

## Publicar no GitHub

**Estado atual:** o remoto `rafaeldcs/ia-autoral` já existe e está público. Os passos
abaixo são para uma instalação nova, sem remoto. Não execute o bootstrap no repositório
existente. Veja [PROGRESS_WINDOWS.md](docs/PROGRESS_WINDOWS.md) para o CI e a divergência
de visibilidade; as correções desta continuação ainda não foram publicadas.

A publicação não aconteceu durante a entrega. Destino proposto: **`rafaeldcs/ia-local-autoral`, privado**.

Com Git e GitHub CLI instalados, configure sua identidade Git local, autentique pelo fluxo do seu computador e revise o destino:

```powershell
gh auth login
.\scripts\publish-github.ps1 -DryRun
.\scripts\publish-github.ps1
```

O script cria o repositório privado e faz push do código. Não altera um remoto existente e recusa sobrescrever um repositório com o mesmo nome. Confira `docs/GITHUB_PUBLICATION.md`. GitHub e Actions são ferramentas opcionais de desenvolvimento, **não dependências do funcionamento local**.

## Leitura recomendada

`docs/DELIVERY_REPORT.md` apresenta o que foi validado e o que falta. `docs/BACKLOG.md` transforma as pendências em atividades com critérios de aceite. `docs/ARCHITECTURE.md`, `docs/GETTING_STARTED_WINDOWS.md`, `docs/API.md`, `docs/DATASET.md` e `SECURITY.md` detalham operação, limites e segurança. O plano original foi preservado em `docs/ORIGINAL_PLAN.md`.

Não foi escolhida licença pública para o projeto. O repositório deve permanecer privado até o responsável definir sua política. A origem desta implementação assistida por IA é declarada em `THIRD_PARTY_NOTICES.md`; ela não oferece garantia jurídica de exclusividade sobre conceitos ou trechos.

Usabilidade do chat: [melhorias, critérios de ensino e resultados reais](docs/USABILITY_LEARNING.md). Interface validada em 27 verificações; candidato neural de usabilidade não ativado após 0/8 no teste reservado.

Cliente Windows instalável e servidor HTTPS na rede local: [instalação](docs/LAN_INSTALL.md) e [validação e pendências](docs/LAN_VALIDATION.md). Distribuição pessoal com chave revogável por dispositivo; não equivale a isolamento de usuários de equipe.
