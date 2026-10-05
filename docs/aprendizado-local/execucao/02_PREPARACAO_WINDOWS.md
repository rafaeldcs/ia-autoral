# Preparação da máquina Windows e preservação do ambiente

## Antes de executar

Este procedimento é para Windows/PowerShell. Em Linux, o executor deve produzir e revisar a variante equivalente; não executar comandos PowerShell por suposição. O hardware anteriormente informado pelo proprietário é apenas referência histórica: medir o equipamento atual antes de escolher o modelo.

Mantenha quatro locais distintos: repositório, dados ativos do LocalAuthor, área privada de experimentos e pesos imutáveis. A área de experimentos e o pacote não devem ficar em uma pasta que será indexada como projeto. Não colocar pesos no Git, nem usar uma pasta de produção para testes.

## Diagnóstico inicial — comandos existentes

Abra um PowerShell na raiz real do repositório. Os comandos abaixo consultam estado; `git fetch` é aquisição de rede e só deve ser usado na fase autorizada.

```powershell
$ErrorActionPreference = 'Stop'
git status --short
if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar o Git.' }
git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Repositório não identificado.' }
py -0p
Get-PSDrive -PSProvider FileSystem
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { nvidia-smi }
```

Não registrar tokens ou variáveis de ambiente completas. Se houver mudanças humanas, preservá-las e trabalhar em branch/worktree separado; não usar stash automático sem saber o que será movido. Atualize com fast-forward somente quando a árvore estiver preparada e a rede autorizada.

## Ambiente dedicado

Não substitua `.venv` em uso. Se já houver um ambiente de aprendizado homologado, reutilize-o depois de verificar seu Python e suas dependências. Caso contrário, escolha um interpretador compatível entre os listados por `py -0p`; o exemplo abaixo usa o Python padrão e precisa dessa conferência prévia.

```powershell
if (-not (Test-Path '.venv-learning\Scripts\python.exe')) {
    py -3 -m venv .venv-learning
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente de aprendizado.' }
}
$python = (Resolve-Path '.venv-learning\Scripts\python.exe').Path
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
$env:PYTHONUTF8 = '1'
& $python --version
if ($LASTEXITCODE -ne 0) { throw 'Interpretador inválido.' }
```

Instale a distribuição PyTorch CPU/CUDA adequada a partir do procedimento oficial para o equipamento. Em seguida, na fase de aquisição autorizada:

```powershell
& $python -m pip install -r requirements-training.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências do laboratório/testes.' }
& $python -m pip install -r requirements-foundation.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências de inferência.' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Ambiente com dependências incompatíveis.' }
```

O arquivo foundation existente contém faixas de versões, não um lockfile homologado. A instalação poderá resolver versões novas; registre as efetivas e não use o ambiente ativo até testar a combinação. As dependências futuras do trainer precisam de arquivo separado e versões revisadas. Para aquisição offline, substitua o índice por um wheelhouse previamente autorizado com `--no-index --find-links`.

## Escolher os dados sem criar outra instalação por engano

O valor já configurado de `LOCALAI_HOME` deve ser preservado. Se estiver ausente, confirme a pasta ativa no script de inicialização/configuração e com o operador. O padrão Windows é uma hipótese, não prova de que esta instalação o utiliza.

```powershell
if (-not $env:LOCALAI_HOME) {
    $env:LOCALAI_HOME = Read-Host 'Caminho absoluto CONFIRMADO dos dados ativos do LocalAuthor'
}
if (-not [IO.Path]::IsPathRooted($env:LOCALAI_HOME)) { throw 'Use caminho absoluto.' }
if (-not (Test-Path -LiteralPath $env:LOCALAI_HOME)) {
    throw 'Pasta não existente: confirme se é uma nova instalação antes de inicializar.'
}
& $python -m localauthor --home "$env:LOCALAI_HOME" --help
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" --help
```

Para uma instalação realmente nova, crie e inicialize a pasta somente após essa decisão explícita. O comando existente é `localauthor --home CAMINHO init`. Não mudar silenciosamente `LOCALAI_HOME` para fazer um teste funcionar.

## Evidências privadas e backup

Escolha uma área de experimentos nova e fora do repositório/dados ativos. Crie nela `estado`, `relatorios`, `datasets`, `checkpoints`, `backups` e `avaliacao-reservada`. Confirme que não está dentro de nenhum projeto indexado. Armazene `pip freeze`, versões, relatórios e hashes nessa área.

Pare o serviço pelo mecanismo normal antes do backup consistente. O comando existente é:

```powershell
# Escolha um caminho NOVO, privado e fora da pasta de dados.
$backupPath = Read-Host 'Caminho absoluto do novo arquivo ZIP de backup'
if (-not $backupPath) { throw 'Defina um arquivo de backup novo e autorizado.' }
if (Test-Path -LiteralPath $backupPath) { throw 'Não sobrescrever backup existente.' }
& $python -m localauthor --home "$env:LOCALAI_HOME" backup "$backupPath"
if ($LASTEXITCODE -ne 0) { throw 'Backup não concluído; não avance para alterações destrutivas.' }
```

Inspecione o inventário e faça uma restauração em pasta nova antes de confiar no backup. Confirme cobertura de `foundation/experiences.sqlite3`, manifestos, Markdown e PNGs. Pesos externos, wheelhouse e checkpoints fora de `LOCALAI_HOME` exigem preservação separada. Não suponha que o backup legado cobre automaticamente toda adição. Um limite de tamanho ou extensão deve ser tratado como bloqueio, não ignorado.

## Testes e diagnóstico real

```powershell
& $python scripts/run-tests.py
if ($LASTEXITCODE -ne 0) { throw 'A suíte falhou; registre e corrija antes de avançar.' }
& $python -m localauthor --home "$env:LOCALAI_HOME" diagnose
if ($LASTEXITCODE -ne 0) { throw 'Diagnóstico não concluído.' }
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" status
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível consultar a camada foundation.' }
& $python -c "import torch; print({'torch':torch.__version__,'cuda':torch.cuda.is_available(),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'bf16':torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False})"
if ($LASTEXITCODE -ne 0) { throw 'PyTorch indisponível ou incompatível.' }
```

Não adotar BF16, quantização ou kernels acelerados só pelo nome da GPU. Diagnóstico positivo não prova que um checkpoint cabe nem que seu treinamento funciona. Se o hardware não comportar o alvo, concluir preparações independentes e registrar a etapa pesada como bloqueada; um modelo menor valida somente seu próprio escopo.

Referências: R2, R3, R5 e R6; T1 em [Fontes](../FONTES_E_COMPATIBILIDADE.md). Os comandos foram conferidos no código de referência, mas não executados no Windows do proprietário durante a criação deste pacote.
