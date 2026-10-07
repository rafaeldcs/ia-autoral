# Publicação do código na main

Em 7 de outubro de 2026 o proprietário determinou entrega direta na `main`, sem trabalho retido em PR. O PR #3 foi integrado por merge, preservando o histórico. As correções seguintes são commits diretos na principal, sem force push.

## Distribuição reproduzível

O job `source-package` do workflow `local-platform-ci` só roda na `main` após aprovação de todas as matrizes Python, .NET e interface do mesmo workflow. Gera um arquivo `LocalAuthor-source-<commit>.zip` e um manifesto JSON com commit, árvore e SHA-256. O artefato se chama `source-<sha completo>` no GitHub Actions.

O pacote contém o código versionado. Não é um instalador com Python/CUDA/pesos embutidos nem uma IA já treinada. Dependências de execução continuam as declaradas no projeto. Não confundir sucesso da distribuição com qualidade de inferência ou instalação no servidor do usuário.

O empacotador usa `git archive` de uma revisão exata, recusa modificações versionadas não commitadas, links, submódulos e nomes de arquivos de pesos/dados/credenciais proibidos. Arquivos locais não versionados não são incluídos. O filtro de nomes não substitui revisão de conteúdo e segredos. A geração de código-fonte não baixa modelos e não modifica os originais.

Para gerar manualmente de um checkout Git limpo:

```powershell
.\.venv\Scripts\python.exe scripts\package-source.py --output dist/source
```

A geração manual não verifica o CI; conferir o commit do manifesto contra o workflow aprovado. O comando recusa sobrescrever o pacote existente da mesma revisão.

## Teste real opcional do checkpoint local

Encerre o servidor para não carregar duas cópias do modelo. Registre previamente um checkpoint local revisado conforme `FOUNDATION.md`, mantendo pesos e dados fora do Git. Com o Python e as dependências opcionais de inferência já preparados:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$HomeLA = Read-Host 'Pasta de dados usada pelo servidor LocalAuthor'
.\.venv\Scripts\python.exe -m localauthor.foundation.smoke --home $HomeLA --kind text --timeout 300
if ($LASTEXITCODE -ne 0) { throw 'Checkpoint não homologado nem ativado por este teste.' }
```

`--kind image` testa a capacidade visual separada. Cada invocação usa um processo descartável; o supervisor cobre verificação, carregamento, geração e liberação. No estouro de prazo tenta encerrar esse processo e informa se sua saída foi confirmada. Isso não instala isolamento por sistema operacional nem altera o servidor principal: o timeout de geração normal continua cooperativo.

Só há sucesso após saída não vazia/não truncada, hashes novamente verificados e término normal do processo. O JSON não inclui a resposta gerada. Ausência de pesos, falha de carregamento, corrupção e timeout não viram aprovação. O teste não baixa, treina ou ativa modelos, não executa código gerado e não certifica competência em programação. Código de checkpoint revisado continua sendo código confiado pelo operador, não uma sandbox.

## Encerramento

A fila impede novos jobs após o início do encerramento e sincroniza a troca do sinal de cancelamento. `Application.close()` aguarda a fila, fecha o navegador e libera os modelos. Se um worker não cooperar, informa falha sem descartar recursos ainda em uso. Jobs pendentes permanecem na fila persistente para um reinício explícito. A geração normal não ganhou interrupção forçada de threads.

## Estado das capacidades

A gestão de residência, perfis de geração e ferramentas de eficiência publicadas estão no código. O leitor de blocos é um componente experimental independente; não está conectado ao forward Nemotron. Não houve nesta publicação novo checkpoint Nemotron treinado, implementação completa de Mamba/CUDA, incorporação integral da inteligência NVIDIA, nova geração visual ou implantação no equipamento do usuário. Essas afirmações exigem implementação e evidências reais, não apenas merge ou CI verde.

Os documentos de `docs/aprendizado-local` não são apagados enquanto os critérios que exigem execução de treino/homologação não forem cumpridos. Consulte `efficiency/README.md` e `efficiency/EXECUCAO_LOCAL.md` para o estudo e a operação das funcionalidades existentes.
