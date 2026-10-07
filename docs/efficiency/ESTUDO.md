# LocalAuthor: estudo Nemotron + ideia Colibri

Data de consulta: 2026-10-07. As referências [S1] a [S13] estão em [FONTES.md](FONTES.md). Descrições externas são separadas de nossas propostas. Este documento não declara uma invenção inédita na literatura nem equivalência de qualidade com modelos de fronteira.

## 1. A decisão central

Construir um sistema local que economiza trabalho desnecessário sem esconder perda de qualidade. A identidade pública é LocalAuthor; internamente, distinguir o que foi implementado por nós, o que é biblioteca de referência e de onde vieram os pesos. Executar pesos abertos localmente elimina chamadas de inferência remotas, mas não transforma sua origem em treinamento do zero.

A proposta de pesquisa é uma **execução econômica verificável**: minimizar custo por tarefa aceita, mantendo um piso de qualidade e controles de execução. A originalidade pretendida está na combinação adaptada ao LocalAuthor; sua superioridade depende de experimentos. Nomear classes não substitui implementar operações e treinar pesos.

Uma função de seleção futura poderia comparar custo = a·tempo + b·energia + c·leituras + d·escritas, sujeita a qualidade mínima, limites de memória e aprovação de segurança. Os pesos a,b,c,d são decisões do operador, não valores universais. Sem sensor de energia, reportar essa métrica como indisponível, nunca como zero. O planejador entregue ainda não realiza essa otimização multiobjetivo.

## 2. O que estudar de cada referência

O Colibri separa componentes residentes e especialistas carregados sob demanda, administrando armazenamento e caches. Seu projeto oferece motores específicos para diferentes arquiteturas; o catálogo consultado não estabelece um carregador Nemotron universal. Aproveitamos o princípio de colocação dos pesos, não assumimos compatibilidade binária. [S1]

O Nemotron é um ecossistema de modelos, datasets e receitas. O hub oficial inclui materiais de código, instruções, agentes, avaliações e multimodalidade. A seleção deve seguir a tarefa e a licença de cada ativo, não a ideia de baixar o catálogo inteiro. [S2]

O Lightning 30B-A3B é uma referência de arquitetura híbrida Mamba-2, atenção e MoE. Seus parâmetros ativos não representam o tamanho de todos os pesos. Já o Nano 4B consultado usa Mamba-2, MLP e atenção; tratá-lo como o mesmo layout MoE seria um erro. As fichas não substituem testes próprios de português, C# e hardware. [S3][S4]

A política de colocação e a seleção do modelo são decisões diferentes. Escolher previamente um modelo menor pode ser uma decisão explícita de produto. Trocar especialistas silenciosamente durante um forward altera outra coisa: a função computada. Nossa implementação não faz isso.

## 3. Arquitetura proposta e estado real

```text
Interface LocalAuthor
    -> contexto e evidências do projeto
    -> política de execução e permissões
    -> runtime local selecionado explicitamente
        -> componentes residentes
        -> estado por solicitação
        -> cache de pesos + armazenamento imutável
    -> resposta / proposta de alteração
    -> verificação externa e humana
    -> experiência candidata
    -> treino offline de candidato, avaliação, promoção revisada
```

Nesta entrega, o cache e o oráculo são primitivas experimentais independentes. O FoundationService recebeu a política de uma capacidade carregada por vez e perfis de geração. **O forward textual existente ainda usa sua biblioteca local de referência e não consome o novo WeightStore.** O aprendizado offline continua como próxima integração, não como efeito de abrir um Markdown.

Separar três memórias: pesos, estado de inferência e conhecimento. Pesos são parâmetros; estado conserva o processamento da solicitação; conhecimento recuperável reúne fontes e experiências. Um cache quente não aprendeu fatos. Um índice de documentos não atualizou parâmetros. Reutilizar estado entre projetos sem isolamento pode vazar contexto.

## 4. Memória: contas antes de carregar

A conta elementar N·bits/8 aproxima somente os pesos numa representação uniforme. Não inclui escalas, índices, camadas em maior precisão, alinhamento, tokenizador, ativações, buffers nem estado. Para 30 bilhões a quatro bits, o ideal aritmético seria 15 GB decimais; isso não é uma promessa sobre qualquer arquivo quantizado real.

Nosso orçamento deve reservar sistema operacional, aplicação, estado máximo admitido, workspace e pelo menos um bloco de staging antes de formar cache. Na GPU, reservar também cópia temporária e desquantização quando aplicáveis. A soma real pode ser maior que os bytes comprimidos. O `placement.py` exige que esses custos sejam informados; não os descobre automaticamente.

O cálculo CPU da implementação é: cache_RAM = min(pesos_especialistas, RAM_disponível − reserva − residentes − estado − workspace − maior_bloco). Se o mínimo obrigatório não cabe, recusar o plano. Em CUDA, planejar residentes/estado/workspace/staging em VRAM e um staging em RAM; só então distribuir caches sem contar o mesmo especialista duas vezes. Esse modo é estimativa, não suporte CUDA.

GB e GiB devem ser identificados. Um arquivo de 15 bilhões de bytes não ocupa 15 GiB. O espaço livre atual, e não a capacidade nominal do SSD, limita conversões, checkpoints, temporários e rollback. Registrar o pico durante carregamento: muitas vezes ele difere do consumo estabilizado.

Não desabilitar swap automaticamente. O processo ainda pode paginar, apesar de nosso limite interno. Em futura integração, usar limites e telemetria do sistema operacional revisados para a plataforma, com recusa de trabalho quando não for possível manter a reserva. Não afirmar proteção térmica quando não há sensor conectado.

A validação multiplataforma detectou que `stat(path)` e `fstat(fd)` podem fornecer `ctime` com semânticas diferentes no Windows [S13]. O leitor foi corrigido para obter as assinaturas sempre pelo descritor. Não se resolveu o problema removendo timestamps nem desabilitando o hash; um teste reproduz a divergência mesmo fora do Windows. Aberturas para consulta de metadados não são contadas como bytes de payload lidos.

## 5. Armazenamento read-only: implementação própria

`WeightStore` identifica blocos por caminho relativo, offset, comprimento e SHA-256. Restringe caminhos e arquivos regulares, verifica limites, valida conteúdo lido e detecta alterações de metadados antes de reutilizar cache. Usa um LRU limitado por bytes, não por quantidade de objetos. Um especialista grande não pode consumir o mesmo orçamento fictício que um pequeno.

A leitura é serializada e o orçamento é cumulativo na vida da instância. Uma falha não autoriza buscar um substituto parecido. O código não escreve sidecars no diretório dos pesos. Isso preserva a separação entre artefatos imutáveis e dados operacionais, importante para o inventário hash-bound que o LocalAuthor já possui.

O prefetch implementado é aquecimento síncrono explícito: respeita limites e não expulsa blocos de demanda para antecipar trabalho. Não é um preditor aprendido nem sobreposição real de I/O com computação. Esse passo conservador oferece uma referência para medir depois um prefetch assíncrono.

Bytes retornados podem continuar vivos no chamador; tensores decodificados também. O contador cobre apenas o cache que o store possui. Portanto, uma integração futura deve liberar referências por operação e reservar o pico externo. O armazenamento exige diretório controlado pelo operador: checagens de caminhos não são um sandbox contra processos hostis concorrentes.

## 6. Fidelidade matemática e o custo de otimizar errado

O objetivo inicial é produzir o mesmo cálculo com pesos em outro lugar. Não alterar top-k, pesos do roteamento, ordem de acumulação, precisão ou estado para aparentar maior velocidade. O Colibri documenta controles experimentais relacionados à seleção de especialistas; eles não se tornam padrões do LocalAuthor. [S5]

O oráculo entregue calcula SwiGLU pequeno em float32, lendo três matrizes por especialista. Recebe rotas e coeficientes do chamador e não os renormaliza. A igualdade entre cache e arquivo verifica essa primitiva, não a arquitetura inteira de Nemotron.

Para um forward real, escrever uma especificação por checkpoint: configuração das camadas, nomes de tensores, shapes, orientação de matrizes, normas, biases, funções de ativação, roteador, especialistas compartilhados, Mamba, atenção, embeddings, cabeça de saída, tokenizador e parada. A ausência de um campo obrigatório deve impedir carregamento, não gerar uma aproximação silenciosa.

Implementar primeiro uma camada e comparar ativações intermediárias com um runtime de referência, com tolerâncias declaradas por precisão. Depois uma sequência pequena, teacher forcing, geração determinística, prefill segmentado, cache quente/frio e contextos variados. Não testar apenas a resposta final: divergência inicial pode se propagar e parecer um erro de linguagem.

Estado recorrente merece atenção especial. Cancelamento, retomada e geração especulativa devem restaurar todos os estados relevantes, incluindo atenção, recorrência e aleatoriedade quando usados. Uma restauração parcial pode passar em um prompt curto e falhar depois. MTP e especulação só devem avançar depois dessa equivalência.

## 7. Pouco desgaste não é uma propriedade automática

TBW e DWPD descrevem resistência associada a escritas; os ciclos de programação/limpeza da NAND não devem ser confundidos com simples leituras. Isso não é garantia de vida ilimitada. [S6]

Nossa proposta reduz escritas próprias mantendo os pesos imutáveis e busca evitar leituras repetidas. Porém, swap, logs, conversões, downloads e checkpoints podem gerar escritas fora do store. Controladores, temperatura e duração do trabalho também precisam de medição. O `write_bytes=0` do teste significa somente que esse componente não chamou escrita durante a leitura, não que o computador inteiro escreveu zero.

Leitura lógica também não é I/O físico: o cache do sistema operacional pode atender a chamada. O ensaio entregue não mede SSD nem energia. Uma homologação deverá separar bytes lógicos, bytes de bloco físicos, cache do sistema, tempo de espera e temperatura, sempre sem executar testes destrutivos de resistência.

Métricas recomendadas: tarefas aceitas por hora, joules por tarefa quando mensuráveis, tempo até primeiro token, p50/p95 de duração total, pico RAM/VRAM, leituras e escritas totais, falhas, temperatura e eventos de limitação térmica. O relógio de ponta a ponta inclui carregamento e validação; não esconder esses custos ao divulgar tokens/s.

## 8. O que melhorar imediatamente no agente

A política de um modelo por vez corrige a diferença entre serializar pedidos e liberar memória. O serviço valida o candidato antes de expulsar o modelo válido, libera o anterior antes de nova alocação e descarta um candidato cancelado depois do carregamento. Uma falha de liberação bloqueia novos carregamentos até reinício.

Isso não isola bibliotecas nativas em processos nem impõe deadline duro de carregamento. A evolução correta é um worker supervisionado, com protocolo local, limites de memória, heartbeat e encerramento controlado. Não tentar interromper um kernel travado apenas com uma flag Python. Nenhum worker desse tipo foi anunciado como pronto nesta entrega.

Para contexto, preservar busca literal e acrescentar uma trilha semântica local somente após homologação. O embedding Nemotron de 1B é candidato documentado com avaliação multilíngue incluindo português. Isso não prova boa recuperação dos nossos repositórios. [S7]

Índice proposto: arquivo/revisão/símbolo/relações/testes/decisões, com pesquisa por identificadores C# e, futuramente, análise Roslyn. Recuperar assinaturas e pontos de chamada, não encher contexto com arquivos arbitrários. Medir recall de evidências em perguntas cujo conjunto correto seja conhecido. Consultar um documento não concede permissão de executar suas instruções.

O agente futuro propõe ferramentas tipadas: busca, leitura, diff, build e testes autorizados. A aplicação valida argumentos e permissões; um ambiente isolado executa. Sem sandbox comprovado, não executar código de projeto no host como fallback. O Foundation desta entrega continua sem execução de ferramentas geradas.

## 9. Aprender: plano de dados e pesos

Separar duas trilhas. Na trilha autoral, desenvolver arquitetura, tokenização, treino e checkpoints próprios; medir sua capacidade real sem prometer qualidade herdada. Na trilha de adaptação local, partir de pesos licenciados e conservar sua origem, mesmo após fine-tuning. As duas podem coexistir no produto sem disfarçar dependências.

O ciclo proposto é: problema com procedência → solução candidata → verificador independente → revisão de direitos e privacidade → conjunto versionado → treinamento → avaliação inédita → promoção humana e rollback. Um modelo professor local pode gerar exemplos; sua resposta não é verdade automaticamente. Nem todos os seus conhecimentos serão transferidos por distilação.

LoRA é uma técnica de adaptação de baixa ordem mantendo a base congelada; não elimina a base necessária à inferência nem concede nova autoria sobre ela. Deve ser comparada com baseline e aplicada apenas às camadas compatíveis com o checkpoint. [S8]

A receita QAD da NVIDIA combina quantização inicial e distilação com professor de maior precisão, usando divergência de logits para recuperar qualidade. Isso motiva nossa linha experimental de compressão, não garante recuperação total no hardware disponível. [S9]

Para implementar distilação por logits, verificar vocabulário/tokenizador e alinhamento de posições. Se forem diferentes, não calcular KL entre índices que representam tokens distintos; usar outra estratégia, como exemplos textuais revisados, ou estabelecer alinhamento apropriado. Manter professor congelado, loss mascarada corretamente e avaliação de estabilidade numérica. Treinar requer estado e memória que não aparecem na conta de inferência.

Curadoria recomendada: deduplicação por problema e por origem, remoção/revisão de segredos, separação por projeto/família de tarefas, validação temporal e retenção de procedência. Dividir aleatoriamente pedaços do mesmo arquivo entre treino e teste causa evidência enganosa. Hash exato detecta só uma parte do vazamento; equivalência semântica exige revisão adicional.

O `learning_gate` entregue compara relatos de um avaliador confiável: identidade de suíte/runner/ambiente, conjunto de casos, qualidade, segurança, tempo, RAM e contaminação exata. Ele não autentica quem escreveu JSON, não executa treinamento, não detecta paráfrases, não estabelece significância e não promove pesos. O requisito de ganho padrão serve a candidatos de aprendizado, não a uma otimização de runtime que mantém o mesmo checkpoint.

## 10. Currículo e multimodalidade

Prioridade de especialização proposta: leitura de requisitos em PT-BR; C#/.NET; testes e depuração; SQL e transações; contratos HTTP/mensageria; arquitetura e limites de segurança; documentação com evidências. Aumentar diversidade e dificuldade apenas quando tarefas inéditas mostrarem retenção do conteúdo anterior. São objetivos de ensino, não habilidades já adquiridas.

Os documentos em `knowledge/efficiency` ensinam regras de trabalho e critérios de revisão para recuperação contextual. Devem ser importados explicitamente para um projeto e continuar com `training_allowed=false` até revisão separada. Não importar automaticamente toda a pasta de testes ou resultados de holdout para o conhecimento de produção.

Percepção multimodal e geração são contratos diferentes. O Omni consultado recebe texto, imagem, áudio e vídeo, mas documenta saída textual. Não o apresentar como gerador de imagens. [S10]

Uma futura ferramenta visual precisa de pipeline gerador específico, limites de resolução/steps/semente, procedência, revisão de saída e descarregamento antes da volta ao texto. Áudio e vídeo precisam de limites de duração, taxa de amostragem/frames e privacidade. O usuário vê um LocalAuthor unificado; o manifesto registra honestamente capacidades e componentes locais.

## 11. Ordem de execução e critérios de parada

Fase A: aprovar regressão do código, integrar teardown do serviço ao ciclo de vida completo e adicionar processo supervisionado. Fase B: homologar um checkpoint pequeno real no hardware alvo, com rede bloqueada e dependências previamente preparadas. Fase C: construir loader/forward por arquitetura e ligar WeightStore a uma camada MoE correta. Fase D: GPU e prefetch assíncrono com contabilidade de picos e estados. Fase E: aprendizagem de pesos e multimodalidade após datasets e avaliações separados.

Cada fase produz relatório, não apenas uma caixa marcada. Interromper ao falhar integridade, ultrapassar orçamento, perder o ambiente isolado, faltar autorização ou observar regressão acima do critério. Um arquivo `.md` não deve instruir o agente a ignorar esses limites para terminar sozinho.

Critério de sucesso final do produto: tarefas inéditas resolvidas com evidências, dentro do orçamento, localmente, sem regressões proibidas e com recuperação comprovada. Um ganho de cache isolado não satisfaz esse critério inteiro.
