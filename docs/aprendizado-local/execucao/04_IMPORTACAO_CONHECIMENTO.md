# Importar conhecimento sem confundir consulta com treinamento

## Escopo de importação

Importe somente os sete arquivos em `conhecimento/` deste pacote e as notas privadas que o proprietário autorizar. Não importe prompts do executor, currículos, exemplos, templates preenchidos, relatórios de treino ou avaliações. Nenhum arquivo deste pacote concede direitos de treinamento automaticamente.

O importador existente aceita Markdown UTF-8, até 200 KB por arquivo e 200 documentos por projeto. A recuperação é lexical, em trechos de 40 linhas, não uma aprendizagem de pesos. A consulta depende de termos relevantes; explique e teste consultas com sinônimos em vez de assumir que o conteúdo sempre será encontrado. Referências R2 e R3.

## Obter o projeto correto

O identificador é o `id` real do projeto, não seu nome ou o caminho da pasta. Cadastre um projeto de laboratório pela interface, consulte a listagem autenticada e registre o ID privado. Não crie um projeto global contendo todos os dados.

Antes de importar, encerre o servidor normalmente. A CLI recusa importação enquanto `server.lock` existir. Não apague esse arquivo para contornar o bloqueio.

## Importação controlada e prevenção de duplicatas

Use as variáveis do procedimento Windows; informe o caminho onde este pacote foi extraído. O script usa somente a CLI já existente. Ele pula cópias cujo hash já está registrado **e confere o arquivo privado correspondente**. Não atualiza ou remove fontes automaticamente.

```powershell
$pacote = Read-Host 'Caminho absoluto da pasta deste pacote'
$projectId = Read-Host 'ID real do projeto de laboratório'
if ($projectId -notmatch '^[A-Za-z0-9_-]{1,128}$') { throw 'ID inválido.' }
$folder = Join-Path $pacote 'conhecimento'
if (-not (Test-Path -LiteralPath $folder)) { throw 'Pasta de conhecimento não encontrada.' }
if (Test-Path (Join-Path $env:LOCALAI_HOME 'server.lock')) { throw 'Encerre o servidor.' }
$privateRoot = Join-Path $env:LOCALAI_HOME "foundation\knowledge\$projectId"
$manifestPath = Join-Path $privateRoot 'sources.json'
$notes = @(Get-ChildItem -LiteralPath $folder -Filter '*.md' -File | Sort-Object Name)
if ($notes.Count -ne 7) { throw 'Esperados os sete documentos de conhecimento deste pacote. Revise a seleção.' }
foreach ($note in $notes) {
    $hash = (Get-FileHash -LiteralPath $note.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $sources = @()
    if (Test-Path -LiteralPath $manifestPath) {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($manifest.schema -ne 1 -or $null -eq $manifest.sources) { throw 'Manifesto inválido.' }
        $sources = @($manifest.sources)
    }
    $matches = @($sources | Where-Object { $_.scope -eq $projectId -and $_.sha256 -eq $hash })
    if ($matches.Count -gt 0) {
        foreach ($entry in $matches) {
            if ($entry.path -notmatch '^[a-f0-9]{32}\.md$') { throw 'Revise o caminho privado registrado antes de continuar.' }
            $privateFile = Join-Path $privateRoot $entry.path
            if (-not (Test-Path -LiteralPath $privateFile)) { throw 'Fonte registrada está ausente.' }
            if ((Get-FileHash -LiteralPath $privateFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) {
                throw 'Fonte registrada foi alterada. Não marcar como importada.'
            }
        }
        Write-Host "Já registrado e íntegro: $($note.Name)"
        continue
    }
    & $python -m localauthor.foundation --home "$env:LOCALAI_HOME" import-md "$projectId" "$($note.FullName)" --title "$($note.BaseName)"
    if ($LASTEXITCODE -ne 0) { throw "Falha na importação de $($note.Name)." }
}
```

O script não transforma a pasta em um canal de aprovação; a inspeção de links e as demais proteções do importador continuam obrigatórias. Execute um importador por vez. Para versões novas do pacote, compare fontes por identidade e versão; não acumule notas contraditórias silenciosamente.

## Testar o que foi realmente usado

Reinicie o servidor e consulte, em `/foundation`, perguntas que dependam das notas: “qual a diferença entre memória e treino?”, “como comprovar uma correção?” e “como revisar composição visual?”. Inspecione os metadados de contexto: documento, trecho, projeto e omissões. Depois formule perguntas com outros termos para descobrir limites da busca lexical.

Faça uma pergunta cuja resposta não está nas fontes; o resultado não deve inventar evidência. Crie outro projeto de laboratório com uma nota contraditória fictícia e comprove que os dados não se misturam. Verifique referência por referência; um formato de citação bonito não comprova a origem.

## Atualização e remoção

O CLI atual não possui um comando de atualização/remoção idempotente de Markdown. Para poucos documentos, o procedimento documentado é parar o servidor, preservar backup, revisar a remoção da entrada antiga e da cópia privada e reimportar. Não editar uma fonte sem atualizar o manifesto. Para operação recorrente, implementar a lacuna indicada no documento 05 antes de automatizar.

Remover uma fonte não apaga conversas, experiências, backups ou datasets que a contiveram. Registre vínculos e invalide derivados quando necessário. O atributo `training_allowed=false` no registro de importação não é convertido automaticamente em um veto transitivo sobre todas as exportações; o pipeline novo deve verificar a autorização de todas as fontes.

## Critério de saída

Lista privada de ID/título/hash por documento, recibos de importação ou reutilização, testes de recuperação e isolamento, falhas conhecidas e política de atualização. Resultado: **conhecimento disponível para consulta**, não “modelo retreinado”.
