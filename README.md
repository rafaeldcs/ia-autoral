# LocalAuthor — plataforma local e laboratório autoral

LocalAuthor reúne conhecimento por projeto, conversas persistentes e revisão controlada de código. O motor neural experimental próprio em NumPy continua disponível como laboratório. A camada opcional **foundation** acrescenta modelos locais de texto/código e geração de imagens, sem dependência de API externa de IA.

**Um único produto não significa pesos de origem única.** Modelos pré-treinados e derivados preservam procedência, licença e revisão. Carregar pesos, consultar Markdown ou guardar experiências não significa treiná-los. Nenhum checkpoint acompanha o repositório e nenhum modelo de fronteira foi homologado nesta entrega.

## Novo: texto, código e imagens locais

Acesse `/foundation` no mesmo servidor da plataforma. Há seleção de projeto/conversa, modos de texto e código sem execução, geração de PNG com um modelo visual separado, consulta de procedência/evidências, fila e cancelamento cooperativo. Falta de checkpoint ou incompatibilidade gera erro explícito, nunca fallback para nuvem.

A integração inclui contexto com histórico e fontes locais, importação Markdown vinculada a hash e projeto, registro privado de experiências e curadoria antes da exportação de datasets candidatos. Os templates e procedimentos iniciais estão em [`knowledge/`](knowledge/README.md).

**Instalação, registro de modelos, comandos e limites:** [`docs/FOUNDATION.md`](docs/FOUNDATION.md). Leia antes de instalar `requirements-foundation.txt`. Os loaders opcionais exigem bibliotecas/frameworks locais; a plataforma e o laboratório legado continuam independentes deles.

Não confunda esta integração com fine-tuning concluído, geração visual nativa do Nemotron textual, agente geral capaz de executar ferramentas, compreensão/edição de imagens ou prova de qualidade dos modelos. Os testes automatizados usam dublês explícitos para os motores; pesos reais, drivers e hardware precisam de validação própria. O código textual gerado não é executado nem aplicado automaticamente.

## Iniciar no Windows

Pré-requisito da plataforma: Python 3.11+. O modo legado não exige GPU nem autenticação em serviço externo. Execute na distribuição-fonte completa, pois a interface em `ui/` não é instalada por um wheel isolado.

```powershell
.\scripts\start.ps1
```

O script exibe o token **local** e inicia o serviço em `http://127.0.0.1:8765`. Esse token não é uma chave NVIDIA. Não o publique nem o envie em uma conversa. A tela principal organiza projetos e conversas; `/advanced` mantém as ferramentas e `/foundation` oferece a integração opcional.

Se PowerShell não permitir scripts, use diretamente, sem alterar a política do sistema:

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONUTF8 = "1"
py -3 -m localauthor init
py -3 -m localauthor token
py -3 -m localauthor serve
```

Para os modelos opcionais, execute o servidor com o Python do ambiente onde instalou suas dependências, como descrito no guia foundation. Caso contrário, o Python global pode não encontrá-las.

Linux/macOS: `bash scripts/start.sh`. O padrão de dados é `%LOCALAPPDATA%\LocalAuthor` no Windows e `~/.localauthor` nos demais sistemas. `LOCALAI_HOME` pode definir outro diretório **fora dos projetos e do repositório**. Preserve a pasta existente ao atualizar. macOS e pesos reais não são cobertos pela matriz atual de CI.

## Primeiro uso e segurança

Cadastre uma cópia de laboratório, importe notas ou indexe arquivos permitidos e consulte a memória. O modo legado de consulta apresenta trechos e fontes, não finge uma resposta neural. Na camada foundation, as evidências entram no contexto do modelo local registrado.

Para alterações, crie um snapshot, prepare a proposta JSON, revise o diff, execute verificações autorizadas e só então aplique. O executor Docker é opt-in e não faz fallback para shell do host. Aplicação sem testes exige aceite separado e não comprova correção.

A API local preserva token, verificação de Host/origem, limites e política de conteúdo. Pesquisa/navegação autorizadas são funções distintas; o runtime foundation não usa serviço externo de IA. Modo offline e hashes não substituem firewall e isolamento do sistema operacional. Consulte [`SECURITY.md`](SECURITY.md) e o guia foundation antes de habilitar código customizado de um checkpoint.

Mantenha fora do Git: dados reais, segredos, checkpoints, corpus, imagens pessoais, experiências e exportações. O isolamento por projeto não equivale a contas multiusuário. Faça backup e teste restauração antes de cadastrar material importante.

## Testes

O laboratório numérico usa a dependência local `numpy==2.3.5`. Para executar a suíte:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\scripts\test.ps1
```

Ou, com esse ambiente ativo: `python scripts/run-tests.py`. O CI executa Python 3.13/3.14 em Ubuntu e Windows, build/smoke do host .NET e testes de interface no Chromium. Consulte o run do commit exato, não resultados históricos de outra revisão.

A suíte rejeita testes ignorados por padrão. `scripts/test.ps1 -AllowUnavailableSymlinks` aceita apenas os três casos específicos de privilégio no Windows, registrando cobertura incompleta. Não use essa opção para esconder outras falhas.

`tests/test_foundation.py` testa contratos, contexto, curadoria, integração, fila e autenticação com dublês de modelo. `scripts/foundation-ui-smoke.py` exercita a nova tela, cancelamento, PNG de teste e layout mobile. Nenhum deles mede qualidade de inferência real ou treinamento. Para rodar os testes de navegador, instale `requirements-dev.txt` e o Chromium do Playwright conforme o CI.

Instalação sem rede exige wheels previamente disponibilizados e `pip install --no-index --find-links CAMINHO_DO_WHEEL ...`. O código não inclui Python, NumPy, PyTorch, drivers, pesos ou um instalador offline completo.

## Laboratório autoral preservado

O laboratório mantém tokenizadores byte/BPE, autodiferenciação, Transformer causal, AdamW, corpus com manifesto, checkpoints e experimentos NumPy. A geração inicial tem capacidade restrita; não equivale a um programador geral. O backend CUDA do motor próprio não foi implementado. Isso é distinto da possibilidade de usar CUDA nas bibliotecas opcionais foundation, que requer configuração e validação no destino.

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m localauthor validate-dataset C:\LocalAuthorData\corpus\manifest.json
.\.venv\Scripts\python.exe -m localauthor train C:\LocalAuthorData\corpus\manifest.json --output C:\LocalAuthorData\models\experimento-001 --config experiments\configs\smoke-cpu.json --steps 100
```

Esses comandos treinam o **laboratório NumPy**, não o Nemotron. O ajuste dos pesos foundation ainda depende de receita, corpus autorizado, avaliação independente e promoção revisada. Memória e dataset exportado não substituem essas etapas.

## Arquitetura e histórico

O núcleo é Python e o host ASP.NET Core .NET 10 é opcional; não houve migração completa para C#. Recursos existentes incluem FTS5, escopos por projeto, coleta HTTPS autorizada, snapshots, diffs, conflitos, diário de recuperação e fila persistente.

Documentos de histórico e operação:

- [`docs/FOUNDATION.md`](docs/FOUNDATION.md): integração atual e limites; [`knowledge/README.md`](knowledge/README.md): biblioteca inicial.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/API.md`](docs/API.md), [`docs/DATASET.md`](docs/DATASET.md) e [`docs/ORIGINAL_PLAN.md`](docs/ORIGINAL_PLAN.md): arquitetura e plano original; afirmações antigas sobre ausência de pesos prontos referem-se ao laboratório legado, não à camada opcional.
- [`docs/PROGRESS_WINDOWS.md`](docs/PROGRESS_WINDOWS.md), [`docs/WRITING_AND_CODE.md`](docs/WRITING_AND_CODE.md), [`docs/PROJECT_CHAT.md`](docs/PROJECT_CHAT.md), [`docs/USABILITY_LEARNING.md`](docs/USABILITY_LEARNING.md): avaliações históricas, não resultados do checkpoint atual.
- [`docs/LAN_INSTALL.md`](docs/LAN_INSTALL.md), [`docs/LAN_VALIDATION.md`](docs/LAN_VALIDATION.md): cliente Windows e host de rede. A nova interface deve ser validada separadamente em cada instalação/proxy.

O repositório remoto é `rafaeldcs/ia-autoral`. Não execute o bootstrap de publicação sobre esse remoto existente. GitHub/Actions são ferramentas de desenvolvimento, não dependências da inferência local. O estado de publicação e os resultados são os do commit e do workflow consultados.

Nenhuma nova licença pública é concedida por esta atualização. A autoria assistida por IA está declarada em [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Bibliotecas, modelos e dados têm licenças próprias; a licença de um modelo não se transfere automaticamente ao restante do produto.
