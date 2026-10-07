# Execução local e critérios de aceitação

Este procedimento não baixa pesos, não treina modelos e não altera o computador remotamente. Use no checkout do repositório. As instalações iniciais de dependências podem exigir internet; a execução de IA não deve depender de APIs externas. Para ambiente isolado, prepare antes os pacotes e pesos aprovados.

## 1. Atualizar a main sem perder alterações

No PowerShell, dentro do repositório existente:

```powershell
$ErrorActionPreference = 'Stop'
$Alteracoes = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível consultar o checkout Git.' }
if ($Alteracoes) { throw 'Há alterações locais. Preserve-as antes de atualizar.' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Falha no fetch.' }
git switch main
if ($LASTEXITCODE -ne 0) { throw 'Falha ao selecionar a main.' }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw 'Atualização não aplicada; não usar reset --hard.' }
```

O upgrade foi incorporado à `main`. O PR #3 está encerrado por merge; a antiga branch não é necessária. Não apagar trabalho local para contornar conflitos. A política de entrega está registrada em `AGENTS.md`.

## 2. Testar o checkout real

Use o ambiente Python do projeto já preparado. Sem `.venv`, crie-o com `py -3 -m venv .venv` e instale as dependências declaradas de teste em `requirements-training.txt`, seguindo o README do repositório. Isso instala bibliotecas, não baixa pesos de IA.

```powershell
$Python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Prepare a .venv do projeto antes de continuar.' }
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
& $Python scripts\run-tests.py
if ($LASTEXITCODE -ne 0) { throw 'A suíte falhou. Consulte reports/test-results.json; não aprovar o upgrade.' }
& $Python -m localauthor.efficiency self-check
if ($LASTEXITCODE -ne 0) { throw 'O ensaio de equivalência sintética falhou.' }
```

O segundo comando cria apenas pesos sintéticos temporários. Resultado esperado: `equal_outputs=true`, `nemotron_executed=false`, `weights_trained=false`. Não comparar seu tempo de milissegundos com inferência de um modelo real.

O runner possui política explícita para testes de links no Windows. Uma ausência de privilégio deve ser registrada como cobertura incompleta, não removida do relatório. Não diminuir a contagem mínima de testes para obter verde. Para empacotamento e o teste opcional de checkpoint em processo descartável, consulte [PUBLICACAO_MAIN.md](../PUBLICACAO_MAIN.md).

## 3. Tornar os textos consultáveis pelo LocalAuthor

Encerre o servidor antes de importar. Informe a mesma pasta de dados do servidor e o ID real de um projeto cadastrado; não invente um ID só para o comando passar.

```powershell
$HomeLA = Read-Host 'Pasta de dados usada pelo servidor LocalAuthor'
$Projeto = Read-Host 'ID do projeto LocalAuthor já cadastrado'
$Arquivos = @(
  'knowledge/efficiency/01_memoria_fidelidade.md',
  'knowledge/efficiency/02_aprendizado_verificavel.md',
  'knowledge/efficiency/03_programacao_multimodalidade.md'
)
foreach ($Arquivo in $Arquivos) {
  & $Python -m localauthor.foundation --home $HomeLA import-md $Projeto $Arquivo --title ([IO.Path]::GetFileNameWithoutExtension($Arquivo))
  if ($LASTEXITCODE -ne 0) { throw "Falha na importação de $Arquivo." }
}
```

Cada importação cria uma cópia com hash e `training_allowed=false`. Não repetir indiscriminadamente: o importador atual cria uma nova fonte, não faz deduplicação automática. Reinicie o servidor e faça perguntas específicas, pedindo referências às fontes. Texto recuperado não é prova de que novos pesos foram aprendidos.

## 4. Configuração de um modelo real

O manifesto continua exigindo pasta local imutável, licença, revisão, revisor e inventário de hashes. O registro não é teste de compatibilidade. Use `python -m localauthor.foundation --home PASTA status` e `register-model --help` para conferir os argumentos no seu checkout.

Novos argumentos do registro textual: `--enable-thinking` e `--generation-seconds 120`. O primeiro apenas passa o perfil ao template; precisa de homologação. O segundo é cooperativo durante geração normal, não encerra um carregamento travado. Os padrões antigos são preservados: raciocínio desabilitado, 300 segundos. O CLI separado `localauthor.foundation.smoke` cobre o ciclo de verificação em processo descartável, sem mudar essa propriedade do servidor.

Não renomear um modelo incompatível para fazê-lo parecer Nemotron. Não escolher BF16/NVFP4 só porque aparece numa ficha; medir suporte de runtime, driver e hardware. Não habilitar código de checkpoint sem revisão local, nem permitir download de código remoto. Os pesos não são distribuídos no pacote de código.

## 5. Evidências para homologar o futuro forward

O relatório de homologação deve registrar checkpoint e hashes, versões de bibliotecas/driver, hardware, comando, seed, precisão, template, quantização, forma de contexto, estado, uso máximo de memória e limitações. Testar entrada real, saída real, rede bloqueada e ausência de fallback.

Comparar referência residente e nova implementação com o MESMO checkpoint e representação. Verificar valores intermediários, rotas, logits, geração determinística, prefill por partes, cold/warm cache, limites, cancelamento e retomada. Qualquer diferença precisa de tolerância justificada e medição por tarefa, não só exemplos escolhidos.

Somente depois fazer benchmark de tarefas inéditas com amostra previamente fixada. Separar tempo de carregamento, primeira resposta e duração total. Medir também caches frios e quentes. Não executar teste destrutivo de escrita de SSD para avaliar desgaste.

## 6. Evidências para aprendizado e promoção

`python -m localauthor.efficiency assess --baseline BASE.json --candidate CANDIDATO.json` avalia documentos de um runner confiável. O CLI não roda os modelos: os relatórios precisam vir de execução real externa a esse comando, com revisão. Não preencher booleanos com `true` apenas para aprovação.

O schema em `learning_gate.py` exige identidades dos checkpoints, dataset, suíte, runner e ambiente; resultados por hash de problema; inventário de problemas de treino; direitos e revisão humana; tempo, RAM e falhas de segurança. Critérios padrão: pelo menos 50 casos pareados, ganho de um ponto percentual, sem aumento de RAM, tempo até 1,2 vez baseline, nenhuma falha de segurança candidata. São critérios iniciais de projeto, não uma demonstração estatística universal.

Antes de promover, fazer revisão de duplicatas semânticas, testes por domínio/idioma, intervalos de incerteza e ensaios de regressão. Guardar o checkpoint anterior fora do Git e provar rollback. As exportações antigas não desaparecem quando uma autorização é revogada; rastrear sua linhagem.

## 7. O que não marcar como concluído

Não marcar treino, GPU, port completo de Nemotron, proteção térmica, embeddings, geração visual nova ou integração nativa como feitos ao terminar os testes CPU. Os documentos temporários anteriores continuam sujeitos ao próprio procedimento de conferência. Esta entrega não autoriza sua exclusão.
