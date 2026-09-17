# Planejamento — IA local autoral de programação

**Versão:** 1.0 do planejamento  
**Data:** 17 de setembro de 2026  
**Responsável pelo produto:** Rafael  
**Equipamento inicial:** notebook Intel Core i7 de 10ª geração, 16 GB de RAM, SSD de 256 GB e NVIDIA RTX 2060. A VRAM, o espaço disponível, o sistema operacional e o desempenho sustentado ainda precisam ser medidos no próprio notebook.

**Status:** especificação de projeto. Nenhum treinamento, benchmark ou teste no notebook foi executado nesta etapa. As metas e configurações abaixo são propostas de engenharia, não resultados medidos nem garantias de capacidade.

## 1. Objetivo e limite da primeira entrega

Construir uma aplicação local que mantenha uma memória de conhecimento rastreável, consulte fontes externas somente quando autorizado e necessário, compreenda o contexto de projetos selecionados e utilize um modelo próprio para propor alterações pequenas de C#/.NET. O usuário revisa o resultado antes de aplicá-lo no projeto original.

A primeira versão não terá como condição de sucesso equivalência a um modelo de fronteira. O objetivo mensurável será resolver uma classe delimitada de tarefas inéditas com fontes, testes e revisão. A competência do modelo é uma hipótese a validar; concluir a interface e o armazenamento não comprova que o modelo aprendeu a programar.

Haverá dois resultados separados: uma plataforma útil de consulta e execução controlada; e um modelo experimental treinado do zero. O modo agente generativo só será disponibilizado para classes de tarefa em que o modelo demonstrar capacidade suficiente. Se o treinamento não atingir o requisito, a plataforma continua funcionando, mas a funcionalidade não recebe o rótulo de agente capaz de programar.

### O significado de autoral neste projeto

Serão próprios: aplicação, regras do agente, organização da memória, política de pesquisa, implementação do modelo, tokenizador aprendido no corpus aprovado, código de treinamento e pesos resultantes. Não haverá carregamento disfarçado de pesos de modelos prontos, nem embeddings obtidos de APIs.

A autoria da implementação não implica inventar do zero conceitos matemáticos conhecidos. A arquitetura poderá usar técnicas publicadas, como Transformer, cuja origem científica será reconhecida. [1]

O projeto terá dependências locais explícitas de infraestrutura: sistema operacional, compiladores, .NET, SQLite, Roslyn e ferramentas/bibliotecas CUDA compatíveis. Elas não serão chamadas de código autoral. Esta proposta significa independência de serviços externos para operar, não ausência de qualquer software de terceiros.

Não haverá conta obrigatória, cobrança por token, licença validada em servidor externo, telemetria remota, CDN, fonte web obrigatória ou fallback silencioso para uma API de IA. A instalação e a atualização poderão usar pacotes previamente obtidos, com versões e hashes registrados; o funcionamento cotidiano será testado com a rede bloqueada.

## 2. Escopo funcional

A versão 1 terá interface em português e foco técnico em C#/.NET. Poderá consultar documentação técnica em português e inglês, desde que o modelo demonstre capacidade para a tarefa. A interface não depende de o modelo já produzir conversa livre fluente.

As capacidades pretendidas são: importar materiais selecionados; localizar documentação e símbolos de código; indicar fontes; reconhecer falta de informação por critérios verificáveis; registrar versões e contradições; propor uma alteração delimitada; executar verificações em ambiente restrito; apresentar diferenças; registrar aprovação ou rejeição; exportar dados e restaurar uma versão anterior.

Não entram na primeira entrega: criação irrestrita de sistemas completos, programação autônoma geral, deploy, bancos de produção, alterações fiscais ou financeiras automatizadas, voz, visão, geração de imagens, vários agentes simultâneos, treinamento contínuo a cada mensagem e um buscador de toda a internet.

## 3. Arquitetura proposta

Adotar um monólito modular para o produto, com processos separados nas fronteiras de segurança e computação. Um repositório; uma instalação local; sem Kubernetes, broker de mensagens, banco vetorial dedicado ou serviços cloud.

| Camada | Implementação proposta | Responsabilidade |
|---|---|---|
| Interface e host | C#/.NET 10, ASP.NET Core e Blazor | Projetos, conversa, pesquisa, revisão de alterações e diagnóstico |
| Aplicação e domínio | C# | Casos de uso, políticas, permissões, fila persistente e estados |
| Memória | SQLite e arquivos locais | Fontes, versões, trechos, relações, experiências e auditoria |
| Ferramentas de código | Roslyn e integração local com Git | Símbolos, referências, análise sintática/semântica e diferenças |
| Motor do modelo | Implementação própria em C#, com backend C++/CUDA | Cálculo, treinamento, checkpoints e inferência |
| Executor restrito | Processo com usuário/permissões limitadas | Compilação e testes, sem acesso geral ao computador |
| Pesquisador | Processo de coleta com saída de rede controlada | HTTP, cache, limites, extração e rastreabilidade |

.NET 10 tem suporte LTS segundo a documentação consultada. Roslyn oferece análise sintática e semântica de C#, mas análise estática não substitui testes de execução. SQLite FTS5 oferece busca textual local; a pontuação final e a política de recuperação serão nossas. [2][3][4]

O motor de GPU pode empregar primitivas matemáticas locais do CUDA, inclusive cuBLAS quando necessário. Essa dependência deve aparecer no inventário: não é um modelo pronto nem um serviço remoto. A compatibilidade do toolkit, do driver e do compilador será validada no notebook. [5]

Estrutura inicial sugerida:

```text
src/
  LocalAI.Domain/
  LocalAI.Application/
  LocalAI.Infrastructure/
  LocalAI.CodeTools/
  LocalAI.Safety/
  LocalAI.Host/
  LocalAI.Runner/
native/
  LocalAI.Compute/
tests/
  Unit/ Integration/ Safety/ Evaluation/
experiments/
  configs/ manifests/ reports/
docs/
```

Dados, corpus, checkpoints, índices e cópias dos projetos ficarão fora do controle de versão do código. O conjunto final de avaliação ficará fora do alcance do indexador, do agente e do treinamento.

## 4. Modelo de dados e memória

Separar cinco conjuntos: fontes originais; conhecimento extraído; contexto dos projetos; experiências de tarefas; e registros de experimentos/modelos.

Entidades principais: `Source`, `DocumentVersion`, `Chunk`, `Concept`, `Relation`, `Evidence`, `ProjectSnapshot`, `TaskRun`, `ToolCall`, `PatchProposal`, `TestRun`, `LearningCandidate`, `DatasetVersion`, `TrainingRun` e `ModelVersion`.

Cada trecho precisa ter fonte, hash, posição no documento, instante de coleta, tecnologia/versão quando identificável, classificação de acesso e política de uso. Cada relação precisa guardar sua evidência e origem: extração determinística, anotação humana ou hipótese do modelo.

As relações terão estados como `proposed`, `verified`, `contradicted` e `superseded`. Uma relação não se torna verdadeira só porque o modelo a repetiu. Material de projetos distintos fica separado por autorização; nenhuma busca poderá recuperar trechos de um projeto não autorizado naquela tarefa.

O conteúdo original será preservado quando seu armazenamento for autorizado. Resumos gerados serão derivados vinculados à fonte, nunca substitutos irreversíveis dela. Remover uma fonte precisa invalidar índices, relações derivadas e candidatos ao treinamento associados. Se já houver modelos treinados com o conteúdo, a linhagem identifica quais versões foram afetadas; excluir o documento do banco não será anunciado como apagamento dos pesos.

## 5. Planejamento por fases

### Fase 0 — Diagnóstico, limites e contrato do projeto

**Construir:** diagnóstico local para registrar sistema operacional, modelo exato do i7, VRAM, driver, RAM livre, SSD livre, temperatura e capacidade de sustentar carga. Não exigir formatação ou mudança de sistema operacional sem necessidade demonstrada.

Preparar um projeto C# de laboratório sem dados reais. Definir pasta autorizada, limite de armazenamento, operações permitidas, destino de backup e requisitos offline. Registrar as decisões em `VISION.md`, `ARCHITECTURE.md`, `SECURITY.md` e `HARDWARE_BASELINE.md`.

**Aceite:** diagnóstico salvo no notebook; permissões explícitas; limite de recursos ativo; testes básicos de leitura, persistência e cancelamento. Não realizar compra de hardware antes desse resultado.

### Fase 1 — Aplicação local e fronteiras de segurança

**Construir:** solução .NET, interface mínima, autenticação local, configurações, cadastro de projeto, fila persistente, logs e botão de interrupção. O host escuta somente no próprio computador por padrão; acesso pela rede local fica desativado inicialmente.

Criar interfaces para `IModelRuntime`, `IKnowledgeStore`, `IResearchProvider`, `ICodeWorkspace` e `IToolRunner`. O simulador de modelo usado nos testes deve ser identificado como simulador, sem ser apresentado como IA funcional.

Permissões são verificadas pelo software antes de qualquer ferramenta, não por um pedido ao modelo para se comportar. Fechar o processo não pode deixar alterações aplicadas parcialmente ou uma tarefa executando sem registro.

**Aceite:** abrir e retomar tarefas offline; nenhuma comunicação externa oculta; acesso bloqueado fora das pastas autorizadas; cancelamento interrompe também processos filhos. O runner ainda não recebe código não confiável sem isolamento verificado.

### Fase 2 — Biblioteca e busca local

**Construir:** importação de `.md`, `.txt`, `.html` e arquivos de código selecionados. PDF textual pode ser um adaptador posterior; OCR não é requisito inicial. Ignorar `.env`, credenciais, dumps, arquivos binários, dependências e diretórios gerados.

Preservar espaços, quebras de linha e codificação do código. Deduplicar documentos por hash e registrar versões. Dividir código por símbolos e documentos por seções. Começar com busca textual, nomes de tipos, assinaturas e referências; usar FTS5 como infraestrutura, sem embeddings prontos. [4]

Construir um grafo simples nas tabelas relacionais: `define`, `uses`, `depends_on`, `fixes`, `applies_to_version` e `contradicts`. Não é necessário instalar um banco de grafos.

**Aceite:** importar novamente um documento inalterado não duplica o conteúdo; recuperar o trecho esperado e sua fonte em perguntas de avaliação; nenhuma mistura entre versões incompatíveis; exclusão invalida os derivados. Nesta fase, apresentar trechos e relações verificáveis, sem prometer síntese inteligente.

### Fase 3 — Pesquisa seletiva e atualização

**Construir:** coletor próprio a partir de domínios e URLs autorizados, usando links e sitemaps para ampliar um acervo limitado. Não depender de Google/Bing ou outro buscador como requisito de funcionamento.

A decisão de pesquisar começa determinística: material ausente, versão incompatível, referência vencida para aquele uso, contradição não resolvida ou necessidade de fonte atual. Relevância textual não é tratada como probabilidade de verdade.

Quando a fonte suporta, utilizar `ETag` e `Last-Modified` para verificar mudanças; uma resposta `304` permite reutilizar a cópia. Isso ainda é acesso à rede, portanto não será contado como funcionamento offline. [6]

Limites propostos: até cinco páginas por rodada, duas rodadas por tarefa, limites de tamanho e duração, intervalo por domínio e interrupção quando novas fontes não acrescentarem evidência relevante. Esses valores são configurações iniciais a calibrar.

Respeitar regras de coleta, licenças e autorização de uso. `robots.txt` orienta crawlers, mas não equivale a autorização para copiar ou treinar com todo o material. [7]

O coletor não executa scripts de páginas; bloqueia acesso a endereços privados, credenciais e destinos não autorizados, inclusive após redirecionamento. Consultas externas não enviam código privado ou mensagens contendo segredos.

**Aceite:** reutilizar uma fonte válida sem nova coleta; detectar atualização quando necessário; tratar contradições; registrar todas as requisições; continuar com a base local sem internet e sinalizar a limitação de atualização.

### Fase 4 — Motor neural próprio em CPU

**Construir:** representação de tensores, operações matemáticas, derivadas, função de erro, otimizador e salvamento de pesos. Começar com um modelo minúsculo para validar o mecanismo.

Implementar testes de derivadas por diferenças finitas, tolerâncias numéricas documentadas e casos pequenos conhecidos. Demonstrar que o modelo consegue ajustar deliberadamente um conjunto minúsculo; depois verificar separadamente a generalização. Decorar o lote de teste do motor não é prova de inteligência.

Criar tokenizador por bytes inicialmente e evoluir para BPE treinado somente no corpus de treinamento autorizado. Exigir conversão texto → tokens → texto sem perda nos casos suportados, inclusive acentos, símbolos, indentação e quebras de linha.

Referências como microgpt mostram os componentes essenciais de um treinamento de linguagem implementado sem um framework de IA. Serão referências de estudo, não uma base copiada e renomeada como nossa. [8]

**Aceite:** derivadas corretas dentro das tolerâncias; erro diminuindo no caso controlado; salvar/recarregar preserva os resultados; tokenizer sem perda; ausência de pesos pré-treinados.

### Fase 5 — Backend GPU e primeiro candidato experimental

**Construir:** backend C++/CUDA para forward e backward, comparado à referência CPU. Começar com FP32; avaliar FP16 com estabilização numérica e acumulação de gradientes após comprovar correção. Não assumir suporte a recursos de placas recentes sem verificar a RTX 2060. [5]

Configuração candidata, não capacidade já comprovada:

| Item | Proposta inicial |
|---|---|
| Arquitetura | Transformer causal pequeno, somente decodificador |
| Blocos | 8 |
| Dimensão interna | 512 |
| Cabeças de atenção | 8 |
| Camada intermediária | 2.048 |
| Vocabulário | Aproximadamente 8.192 tokens, incluindo especiais |
| Contexto | 512 tokens inicialmente |
| Pesos de entrada/saída | Compartilhados quando compatível com a implementação |
| Parâmetros | Aproximadamente 34 milhões; contagem exata gerada pelo programa |
| Origem dos pesos | Inicialização aleatória |

O contexto inclui pedido, documentos recuperados, código e resposta. Não serão 512 tokens disponíveis separadamente para cada elemento. Operar sobre métodos pequenos e assinaturas antes de tentar arquivos inteiros. [1]

Na configuração convencional de treinamento misto exemplificada pela documentação consultada, pesos, gradientes e estados do Adam somam aproximadamente 18 bytes por parâmetro, além de ativações e temporários. Para 34 milhões, isso corresponde a aproximadamente 612 MB somente nessa parcela; não é o pico total da GPU. [9]

**Aceite:** concordância numérica CPU/GPU; ciclo de treino sem resultados inválidos; uso de memória medido; checkpoints retomáveis; interrupção controlada; desempenho sustentado registrado. Se falhar, reduzir modelo/contexto e corrigir o motor antes de ampliar.

### Fase 6 — Corpus autorizado e laboratório de avaliação

**Construir:** manifesto de dados com origem, licença/permissão, hash, classificação e uso autorizado: consulta, treinamento ou ambos. Não presumir que um repositório do usuário contém somente conteúdo de sua titularidade.

Usar inicialmente exercícios próprios e projetos de laboratório. Adicionar código e documentação externos apenas quando a política de uso estiver aprovada. Filtrar segredos e dados pessoais antes de indexar ou treinar. Conversas com serviços de IA e soluções geradas por professores externos não entram automaticamente no corpus.

Separar dados de pré-treinamento — código e texto — de dados supervisionados — pedido, contexto, alteração esperada e verificação. Criar também exemplos em que a resposta correta é indicar ausência de evidência ou não executar uma ação.

Dividir por projeto/família de problemas, e não por linhas aleatórias. O tokenizador aprende apenas com a partição de treinamento. Detectar duplicatas próximas entre partições e manter o teste final inacessível à memória pesquisável. Exemplos produzidos por modelos têm origem registrada e não recebem automaticamente status de corretos.

**Aceite:** nenhuma fonte sem política definida; teste isolado; exemplos verificáveis; tarefas com casos-limite; avaliação independente das soluções propostas pelo agente.

### Fase 7 — Treinar, medir e especializar

**Construir:** pipeline versionado de treinamento. Executar uma prova mínima e depois um piloto de aproximadamente 5–20 milhões de tokens processados, como experimento de custo e estabilidade, não como quantidade que garante programação competente. Registrar tokens únicos e repetições separadamente.

O programa salva configuração, seed, hash do código, versão do corpus/tokenizador, métricas de treinamento e validação, tokens por segundo, memória, duração e checkpoints. Prever pausa segura e retomada.

Começar aprendendo padrões de código e texto. Em seguida, ajustar o nosso próprio modelo para tarefas delimitadas: completar métodos, responder sobre trechos fornecidos, propor correções curtas e emitir propostas estruturadas de ferramenta. Incluir cenários com evidência recuperada e com informação insuficiente.

Comparar com baselines: busca literal, recuperação de uma solução semelhante e regras determinísticas. Avaliar separadamente ganho do modelo e ganho das ferramentas. Aumentar parâmetros não será a primeira reação automática a um erro: dados, implementação e recuperação também precisam ser investigados. Estudos de escala mostram que tamanho e quantidade de treinamento devem ser considerados conjuntamente; não adotaremos uma proporção universal como garantia para este caso. [10]

**Aceite:** melhoria em tarefas inéditas, não só queda no erro de treinamento; falhas documentadas; desempenho e recursos medidos. Se o piloto só memorizar exemplos, corrigir corpus/objetivo ou replanejar a escala. Não liberar o agente como programador antes de atingir seus critérios.

### Fase 8 — Integração do agente de programação

**Construir:** uma máquina de estados explícita: pedido → contexto → evidências → proposta → autorização → aplicação na cópia → verificações → revisão.

O modelo propõe ações estruturadas. Um validador independente confere esquema, caminhos, permissões, limites e pré-condições. Ferramentas iniciais: listar arquivos permitidos, buscar símbolos, ler trechos, propor patch, validar patch, aplicar em cópia, compilar, testar e mostrar diferenças.

Não expor um terminal irrestrito como ferramenta inicial. Até um comando permitido de build pode executar tarefas definidas pelo projeto; MSBuild permite executar programas e comandos. A proteção precisa estar no ambiente de execução e no sistema operacional, não só no nome do comando. [13] O runner terá usuário restrito, ambiente sem segredos, limites, diretórios explícitos e rede bloqueada por padrão.

Uma worktree do Git separa o trabalho de edição, mas não é uma sandbox de segurança. Preservar alterações não commitadas do usuário com snapshots e hashes; nunca presumir que criar uma branch já protege os arquivos. [11]

Política inicial: no máximo três tentativas totais; parar quando não houver progresso. Testes pré-existentes rodam antes para estabelecer a situação inicial. O agente não altera os testes do avaliador para fabricar aprovação. Alterações nos testes do projeto aparecem separadamente para revisão.

**Aceite:** uma tarefa inédita suportada passa no fluxo completo; diffs completos; testes registrados; nenhum acesso fora do escopo; rejeição deixa o original intacto; aplicar exige aprovação e verifica se o original mudou desde o snapshot.

### Fase 9 — Memória de experiência e melhoria controlada

**Construir:** registrar pedido, contexto, versão do projeto, fontes, patch, comandos, resultados, decisão do usuário e eventual regressão posterior. Estados: tentado, aprovado, rejeitado, regressão detectada e obsoleto.

O conhecimento reutilizável passa por verificação. Feedback isolado não é uma etiqueta infalível. Candidatos ao treinamento são promovidos somente depois de revisão, filtragem, teste e deduplicação.

O treinamento produz uma versão candidata. A versão em uso continua congelada. A candidata enfrenta o conjunto de avaliação e uma bateria antiga de regressão; se piorar critérios essenciais, não substitui a anterior. A promoção exige aprovação e mantém rollback.

Busca semântica aprendida por um encoder próprio pode ser um experimento posterior. Terá dataset, pesos, custos e avaliação separados, sem introduzir embeddings externos silenciosamente.

**Aceite:** reutilizar uma experiência aplicável; não repetir uma solução rejeitada em condições equivalentes; não confundir versão; recuperar a versão anterior do modelo; rastrear quais dados participaram de cada treinamento.

### Fase 10 — Validação, instalação e versão 1

**Construir:** pacote offline com binários, modelo próprio aprovado, tokenizador, esquemas, migrações, inventário de dependências e manual. Disponibilizar exportação/importação de conhecimento e configurações, sem obrigar login em serviço.

Para compilar projetos offline, preparar SDKs e dependências autorizadas no cache local. Pacote ausente deve gerar aviso, não uma tentativa oculta de download. Controlar restore implícito, telemetria e consultas de atualização do SDK, além de bloquear a rede do executor no sistema operacional. A documentação de dotnet build registra restore implícito e downloads de manifestos de workloads, portanto não basta a nossa aplicação deixar de chamar uma API. [14] O modo pesquisador é a única saída externa prevista, quando explicitamente habilitado.

Testar reinicialização, tarefa interrompida, disco cheio, documento corrompido, falta de rede, OOM, backup e restauração. Atualizações não substituem modelos sem autorização e mantêm versões recuperáveis.

**Aceite:** instalação e uso local documentados; suite de validação aprovada para o escopo; revisão humana funcional; recuperação testada; relatório de limitações. Sem modelo aprovado, entregar a plataforma e o laboratório identificados como tais, não afirmar que a versão completa já sabe programar.

## 6. Critérios propostos de avaliação

Criar inicialmente 200 casos independentes, distribuídos entre consulta/recuperação, atualização/contradições, alterações de código, segurança e recuperação offline. Esse tamanho não prova confiabilidade universal; é um primeiro conjunto de engenharia e deve crescer com o uso.

| Área | Meta inicial proposta para o modo assistido |
|---|---|
| Recuperação | Evidência esperada entre os cinco primeiros resultados em pelo menos 90% dos casos cobertos |
| Alteração de código | Pelo menos 80% das tarefas pequenas suportadas resolvidas dentro do limite de tentativas, sempre com revisão |
| Preservação do escopo | Nenhuma alteração não autorizada observada na bateria; qualquer caso bloqueia a publicação |
| Fontes | Todo trecho apresentado como evidência tem origem rastreável; suporte factual também é verificado |
| Offline | Fluxo aprovado funciona com saída de rede bloqueada; ausência de atualização é sinalizada |
| Recuperação | Interrupção e restauração não perdem alterações do usuário nos cenários testados |

Registrar sucesso na primeira tentativa e no total separadamente. Não esconder tarefas em que o agente desistiu. Medir taxa de recusa, acerto, regressões, tempo até o primeiro resultado, tempo total, consumo de recursos e reuso de memória. Uma execução que compila, mas não cumpre o pedido, falhou. Testes aprovados são evidência limitada, não prova de ausência de defeitos.

Repetir parte dos experimentos com seeds diferentes e reportar contagens, não somente percentuais. Não ajustar continuamente o modelo sobre o mesmo teste final; usar conjunto de desenvolvimento separado e renovar desafios para reduzir contaminação.

## 7. Orçamento de recursos no notebook

Valores abaixo são limites iniciais propostos, não consumo já medido.

| Recurso | Política inicial |
|---|---|
| Concorrência | Um usuário e uma tarefa pesada por vez |
| RAM do sistema do projeto | Tentar manter processos próprios dentro de 8–10 GB; reduzir pela disponibilidade real |
| GPU | Trabalhar abaixo de cerca de 75–80% da VRAM medida no piloto, recalibrando conforme picos |
| Contexto | 512 tokens no primeiro candidato; aumentar só após benchmark |
| Treinamento | Exclusivo quando usar a GPU; consultas pesadas ficam suspensas |
| CPU | Limitar paralelismo para preservar a interface e o sistema operacional |
| Armazenamento | Quota inicial de 30–50 GB se houver espaço, preservando margem livre do sistema |
| Checkpoints | Último, melhor e anterior aprovado, com coleta de versões intermediárias |
| Rede | Desligada por padrão; coleta autorizada tem orçamento próprio |

A memória medida inclui ativações, temporários e picos; não basta contar pesos. O loader deve ler blocos dos dados e não carregar todo o corpus na RAM. A interface deve mostrar fila, etapa atual, RAM/VRAM, ocupação de disco e motivo de interrupção.

Não é obrigatório trocar hardware para construir a plataforma e iniciar os experimentos pequenos. Upgrade de RAM ou SSD depende de medição e compatibilidade do notebook. Treinamentos maiores serão uma decisão posterior: usar o mesmo equipamento com escopo menor ou ampliar hardware próprio, sem substituir automaticamente o modelo autoral por um modelo externo.

Para calcular uma execução de treinamento:

`tempo estimado = tokens planejados / tokens por segundo medidos`

Somar avaliação, checkpoints e preparação. Tokens únicos e tokens processados em repetições não são a mesma medida. Throughput deve ser medido na mesma configuração e sob carga sustentada.

Para energia:

`custo = potência média em kW × horas de uso × tarifa em R$/kWh`

Exemplo hipotético: 0,300 kW × 4 horas × 30 dias × R$ 1,00/kWh = R$ 36. Não é a tarifa do usuário nem uma medição do notebook. Usar medidor na tomada para o consumo total; potência da GPU não representa sozinha o computador inteiro.

Desenvolvimento, curadoria, manutenção, energia e eventual hardware próprio são custos do projeto. O planejamento não presume serviço cloud, assinatura ou compra de dados. Não há estimativa de prazo/custo total confiável antes dos primeiros experimentos e da definição do corpus aprovado.

## 8. Segurança e qualidade transversais

Toda fonte externa é dado não confiável. Comentários de código, páginas e documentação podem conter instruções que tentam manipular um agente. Separar essas instruções das permissões e dos controles de execução é requisito permanente. [12]

Aplicar menor privilégio no sistema operacional; validar caminhos canônicos e links simbólicos; não herdar credenciais do usuário; não montar a pasta pessoal completa; impedir acesso do runner à configuração de segurança; não executar instaladores sugeridos pelo modelo; não permitir que o modelo publique uma versão de si mesmo ou altere a régua de avaliação.

A segurança não fica por último: as fases apenas aprofundam controles já presentes. A bateria inclui conteúdo malicioso na memória, tentativa de ler segredos, escrever fora do escopo, alterar testes, executar comandos arbitrários, acessar destinos privados e produzir consultas externas com código confidencial.

Backups devem ter restauração verificada e, quando possível, uma cópia em outro dispositivo. Uma segunda pasta no mesmo SSD não será tratada como proteção contra falha física do disco.

## 9. Backlog inicial executável

| ID | Entrega | Dependência principal |
|---|---|---|
| IA-001 | Visão, critérios de autoria e requisitos offline | Nenhuma |
| IA-002 | Diagnóstico do notebook e quotas | IA-001 |
| IA-003 | Solução modular, configuração e logs | IA-001 |
| IA-004 | Política de caminhos, segredos e cancelamento | IA-003 |
| IA-005 | SQLite, fontes, versões, chunks e evidências | IA-003 |
| IA-006 | Importação idempotente e busca com fonte | IA-004 e IA-005 |
| IA-007 | Roslyn: símbolos, referências e seleção de trechos | IA-004 |
| IA-008 | Cópia de trabalho, diff e aplicação com pré-condições | IA-004 e IA-007 |
| IA-009 | Runner restrito e testes independentes | IA-004 e IA-008 |
| IA-010 | Coletor autorizado, cache HTTP e limites | IA-005 e IA-006 |
| IA-011 | Tensores, derivadas e modelo mínimo em CPU | IA-002 e IA-003 |
| IA-012 | Tokenizador próprio e manifesto do corpus | IA-001 e IA-011 |
| IA-013 | Backend CUDA e comparação numérica | IA-011 |
| IA-014 | Corpus aprovado e divisão de avaliação | IA-012 |
| IA-015 | Treinamento piloto, checkpoints e métricas | IA-013 e IA-014 |
| IA-016 | Propostas estruturadas do modelo e validador | IA-009 e IA-015 |
| IA-017 | Experiências, candidatos de aprendizado e promoção | IA-016 |
| IA-018 | Suite integrada, pacote offline e restauração | Etapas anteriores |

A plataforma e o motor CPU podem ser desenvolvidos em paralelo depois da base, mas compartilham documentação, dados e contratos. Evitar construir um framework genérico de IA antes de validar uma única tarefa pequena de ponta a ponta.

## 10. Definição de conclusão

O encerramento da versão 1 exige demonstrar, no notebook, este cenário: com internet e professores externos indisponíveis, o usuário seleciona um projeto autorizado, apresenta uma tarefa inédita da classe suportada, recebe uma proposta do modelo próprio apoiada por evidências locais, executa verificações restritas, revisa o diff e aplica ou rejeita sem perder o estado anterior.

A entrega inclui código-fonte, instruções de compilação, modelo aprovado e tokenizador, manifesto do treinamento, relatório de avaliação, limites conhecidos, manual de operação e procedimento de restauração. Os objetivos posteriores — TypeScript, múltiplos arquivos, busca semântica própria e modelos maiores — entram em novas versões com novos critérios, sem mudar silenciosamente a promessa da versão 1.

**Primeiro marco concreto:** abrir a aplicação local, cadastrar um projeto de laboratório, importar um documento, fazer uma consulta com fonte e impedir leitura fora da pasta autorizada. Esse é o início da plataforma; não será apresentado como o modelo já treinado.

## Referências técnicas consultadas

As referências sustentam componentes e limitações técnicos. Arquitetura, tamanhos, metas, quotas e organização das fases são propostas deste planejamento, não resultados extraídos das fontes.

[1] Vaswani et al. — Attention Is All You Need. `https://arxiv.org/abs/1706.03762`

[2] Microsoft — .NET releases, patches, and support. `https://learn.microsoft.com/en-us/dotnet/core/releases-and-support`

[3] Microsoft — The .NET Compiler Platform SDK. `https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/`

[4] SQLite — FTS5 Extension. `https://www.sqlite.org/fts5.html`

[5] NVIDIA — CUDA Installation Guide for Microsoft Windows; Turing Tuning Guide. `https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html` e `https://docs.nvidia.com/cuda/turing-tuning-guide/index.html`

[6] MDN — HTTP conditional requests. `https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests`

[7] IETF — RFC 9309, Robots Exclusion Protocol. `https://www.rfc-editor.org/rfc/rfc9309.html`

[8] Andrej Karpathy — microgpt. `https://karpathy.github.io/2026/02/12/microgpt/`

[9] Hugging Face — GPU memory usage. `https://huggingface.co/docs/transformers/model_memory_anatomy`

[10] Hoffmann et al. — Training Compute-Optimal Large Language Models. `https://arxiv.org/abs/2203.15556`

[11] Git — git-worktree documentation. `https://git-scm.com/docs/git-worktree`

[12] OWASP — LLM Prompt Injection Prevention Cheat Sheet. `https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html`


[13] Microsoft — MSBuild Exec task. `https://learn.microsoft.com/en-us/visualstudio/msbuild/exec-task?view=vs-2022`

[14] Microsoft — dotnet build. `https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-build`
