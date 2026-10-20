# Harvey LAB na LocalAuthor

Esta integração opcional executa o motor do [Harvey Legal Agent Benchmark](https://github.com/harveyai/harvey-labs) com o modelo **local** registrado na LocalAuthor. A revisão congelada é `97810facfd447317b57f6dd02a1469561c573d79` (`lab-core` 1.2.0, licença MIT). O inventário dessa revisão contém **2.010 tarefas e 114.437 critérios**, incluindo tarefas que consultam um corpus compartilhado de documentos. Inventariar não significa executar ou aprovar.

## O que é executado

- Ciclo original `run_agent`, ferramentas `bash`, `read`, `write`, `edit`, `glob`, `grep` e `finish`.
- Leitura original de DOCX, XLSX, PPTX e PDF dentro da sandbox; scripts e manuais de documentos da revisão original disponíveis em `skills/`.
- Rubricas originais e regra de aprovação integral por tarefa: um erro de avaliação não conta como acerto.
- Transcrição, métricas de ferramentas/documentos, artefatos, hashes, estados por tarefa e fonte do relatório original.
- Adaptação de transporte para o GGUF local, incluindo correção solicitada ao próprio modelo quando ele viola o protocolo, sem converter respostas inválidas em chamadas válidas.
- Avaliação local e resolução local de nomes de arquivos. O fallback original de nomes utiliza um provedor externo; ele é substituído explicitamente pelo adaptador local nesta revisão fixada.

O avaliador pode ser o mesmo modelo que executa a tarefa. Seus pareceres são **provisórios**, não independentes. Isso não torna o modelo juridicamente qualificado nem comprova qualidade comercial. Uma tarefa interrompida, com contexto insuficiente, artefato ausente ou avaliação inválida não recebe aprovação. Não há importação automática para treinamento nem alteração de pesos.

## Infraestrutura

O Python principal continua sem novas dependências obrigatórias. O worker usa Python 3.12 dentro da imagem Docker construída a partir do Dockerfile original, com Pandoc 3.11, LibreOffice, bibliotecas Python/JavaScript e ferramentas de documentos. O adaptador para Docker substitui a inicialização original em Podman. A imagem adicional incorpora o núcleo original e seu aviso MIT. A construção baixa dependências de infraestrutura, **não pesos de modelos generativos da LocalAuthor**. Bibliotecas de OCR/detecção de formatos podem incluir seus próprios dados de classificação. Um ambiente separado Python 3.13 pode ser usado para validar a biblioteca original; não substitui o ambiente do servidor.

Antes de iniciar cada worker, o host confere ID imutável da imagem, rede desativada, usuário sem privilégios, raiz somente leitura, capacidades removidas, proibição de novos privilégios, memória de 2 GB, dois CPUs, 128 processos e as duas montagens autorizadas, ambas somente leitura. Área de trabalho e saída usam memória temporária limitada a 512 MB e 64 MB; comandos gerados não ganham montagem gravável do host. A imagem não recebe chaves de provedores nem o banco do servidor. Scripts gerados executam apenas dentro do container; exportação de artefatos é limitada, autenticada e conferida por hash. O canal de controle é autenticado por execução e a memória do controlador não fica disponível a seus comandos filhos.

## Preparar uma vez

Use uma cópia local da revisão indicada. O clone completo inclui vários GB de materiais. No Windows, prefira checkout esparso de `lab_core`, `docs`, `tests` e `scripts`: os documentos são lidos diretamente dos objetos Git e preparados por corpus, sem renomear os arquivos originais ou duplicar o corpus compartilhado a cada tarefa.

```powershell
git clone --no-checkout https://github.com/harveyai/harvey-labs.git C:\LocalAuthor-Benchmarks\harvey-labs
git -C C:\LocalAuthor-Benchmarks\harvey-labs config core.longpaths true
git -C C:\LocalAuthor-Benchmarks\harvey-labs sparse-checkout set --cone lab_core docs tests scripts
git -C C:\LocalAuthor-Benchmarks\harvey-labs checkout 97810facfd447317b57f6dd02a1469561c573d79
python scripts/build-harvey.py --upstream C:\LocalAuthor-Benchmarks\harvey-labs --context build/harvey-image-context
```

Use o `image_id` emitido pela construção; tags mutáveis não são aceitas na execução. O script exporta os objetos Git com os finais de linha originais, evitando quebra de scripts Linux em checkouts Windows. Não executa o instalador nem as instruções textuais dos documentos no host.

## Inventariar todas as tarefas originais

```powershell
$env:PYTHONPATH = 'src'
python -m localauthor.harvey inventory --upstream C:\LocalAuthor-Benchmarks\harvey-labs --output C:\LocalAuthor-Benchmarks\inventario.json
```

O inventário contém os identificadores, a revisão, hashes de definição, critérios e o corpus efetivo, inclusive `docs_dir` compartilhado. Critérios e tarefas não desaparecem para melhorar a taxa de aprovação.

## Executar com os pesos locais existentes

```powershell
python -m localauthor.harvey run --upstream C:\LocalAuthor-Benchmarks\harvey-labs --home "$env:LOCALAPPDATA\LocalAuthor" --output C:\LocalAuthor-Benchmarks\execucao-001 --image sha256:ID_DA_IMAGEM --suite benchmarks/harvey-local/suite.json --max-turns 6
```

O conjunto versionado é sintético, voltado a marketing, leads, programação e QA. É desenvolvimento interno, não um conjunto reservado de qualificação. Para as tarefas jurídicas originais, substitua `--suite ...` por `--original`. Sem `--max-cases`, todas as tarefas originais entram no lote. `--max-cases 2` executa duas pendências e deixa o restante explicitamente pendente, sem anunciar conclusão do benchmark inteiro. Pode-se escolher até 200 turnos; um orçamento maior não amplia a janela de contexto dos pesos existentes.

## Acompanhar, interromper e retomar

Abra `report.html` na pasta da execução. `state.json` mantém todas as tarefas e `summary.json` diferencia concluídas de pendentes. Cada tentativa tem sua pasta própria, entradas, saída, transcrição, gerações, inspeção de sandbox e resultados. A fonte HTML original é preservada como `.untrusted`; o relatório de acompanhamento escapa texto da IA e usa uma política de conteúdo restritiva.

Para parar entre tarefas, crie um arquivo vazio `STOP_AFTER_CASE` nessa pasta. Para continuar, remova **somente esse marcador** e repita o comando com `--resume`. Uma tentativa interrompida é preservada e ganha uma pasta nova ao retomar. Modelo, revisão, conjunto, adaptador, imagem e orçamento precisam corresponder ao estado congelado; uma mudança exige uma execução nova para comparação. Falhas concluídas permanecem registradas, sem serem reclassificadas como acertos pela retomada. O reinício do Windows não inicia esse comando de avaliação automaticamente.

O hash do controlador inclui todos os fontes Python de `src/localauthor` e o script de transporte GGUF. Assim, atualizar somente o bridge ou o isolamento também impede retomar inadvertidamente com outra implementação. Para lotes longos, mantenha uma cópia congelada desses fontes e do script fora do checkout de desenvolvimento e execute/retome a partir dela. O lote original iniciado em 20/10 usa uma cópia anterior a esse endurecimento do hash; sua cópia integral está preservada, e a retomada deve usar aquele mesmo controlador.

## Verificar a integração

```powershell
python scripts/harvey-smoke.py --image sha256:ID_DA_IMAGEM --report reports/harvey-software.json
python scripts/run-tests.py
```

O smoke usa modelos/avaliadores roteirizados explicitamente para verificar o software, com Docker, núcleo original, ferramentas e parsers reais. Isso não mede a inteligência do modelo. Os ensaios com pesos reais precisam ser apresentados separadamente e manter também suas falhas. Tarefas jurídicas extensas podem ultrapassar o contexto disponível; 114 mil critérios não são uma operação instantânea nesta máquina.

`scripts/harvey-negative-corpus.py` executa todas as rubricas originais com saídas ausentes e avaliador determinístico negativo; confirma que elas não são aprovadas sem entrega. É teste de software com dublê, nunca 114 mil acertos do modelo. `scripts/harvey-code-oracle.py` verifica código gerado com sete asserções independentes em uma sandbox nova, sem usar o parecer da IA como oráculo. `scripts/harvey-compare.py` usa os comparativos originais sobre lotes terminados; o ambiente opcional precisa das dependências de gráficos de `lab-core`. Rótulos locais têm tarifa de API zero, que não estima energia nem tempo de máquina. Contagem de tokens de saída não está disponível nesse adaptador; não interpretar o zero padrão do núcleo original como medição real.

Esta integração é uma ferramenta de avaliação do operador. Não acrescenta navegação irrestrita, publicação em redes sociais, envio a leads, acesso a produção, execução de código no host ou um botão novo no cliente Windows. Não muda o instalador do aplicativo nem usa serviços externos de IA.
