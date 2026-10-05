# LocalAuthor: modelos locais de texto e imagens

## Escopo desta entrega

A camada opcional `foundation` integra modelos de origem registrada ao aplicativo existente. O laboratório NumPy, os checkpoints autorais `.npz`, o navegador, os snapshots e a revisão de propostas permanecem separados e não foram substituídos.

O usuário utiliza um único produto, **LocalAuthor**. Internamente há um motor textual e, opcionalmente, outro motor visual. Pesos NVIDIA originais ou derivados continuam com sua procedência e licença; trocar a interface ou o nome não equivale a treinar um modelo autoral. A geração visual não é fornecida pelo checkpoint textual.

Implementado: registro local com inventário SHA-256, carregamento opcional, contexto de conversa e evidências, importação Markdown por projeto, texto/código sem execução, geração PNG, histórico, fila/cancelamento, leitura autenticada de imagens, experiências privadas, curadoria explícita e exportação de dataset candidato. A interface está em `/foundation` no mesmo servidor.

**Não entregue como capacidade validada:** pesos NVIDIA/visuais executados em hardware real, fine-tuning/LoRA, qualidade de programação, agente geral com ferramentas, leitura/edição de imagens, geração de vídeo/áudio, treinamento visual ou promoção automática de modelos. Testes com dublês não comprovam essas capacidades. As dependências opcionais e os checkpoints precisam de homologação conjunta no ambiente de destino.

## Instalação no Windows

Mantenha os dados e pesos fora do repositório e dos projetos. Use a mesma pasta de dados do servidor existente; não crie outra pasta inadvertidamente. O padrão do Windows é `$env:LOCALAPPDATA\LocalAuthor`; uma instalação já pode usar `LOCALAI_HOME` personalizado.

```powershell
# Na raiz do repositório. Não é necessário recriar um venv que já existe.
py -3 -m venv .venv
$python = "$PWD\.venv\Scripts\python.exe"
$env:PYTHONPATH = "$PWD\src"
$env:PYTHONUTF8 = "1"
if (-not $env:LOCALAI_HOME) { $env:LOCALAI_HOME = "$env:LOCALAPPDATA\LocalAuthor" }

& $python -m pip install -r requirements-training.txt
& $python -m pip install -r requirements-foundation.txt
& $python -m localauthor init
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" status
```

O arquivo de dependências define uma faixa inicial de APIs, não um ambiente homologado. Instale a distribuição PyTorch CPU/CUDA adequada ao sistema antes das demais dependências. Se o resolvedor não encontrar wheels para sua versão Python, use um ambiente compatível indicado pelo fornecedor, sem alterar o ambiente estável. Para instalação sem rede, prepare wheels compatíveis e use `--no-index --find-links` em ambos os comandos pip. Nenhum peso está incluso.

Depois de homologar a combinação específica, registre `pip freeze`, Python, sistema, driver, dispositivo, hashes do modelo e resultados no model card privado. Não publique caminhos pessoais, segredos ou esse ambiente privado no Git.

## Preparar e registrar os modelos

Obtenha os arquivos explicitamente, fora da execução do aplicativo, de uma fonte licenciada e revisada. A pasta deve ser um checkpoint completo no formato Transformers/Safetensors (texto) ou Diffusers/Safetensors (imagem), incluindo configurações e tokenizadores. Uma pasta do cache com symlinks não é aceita: use uma cópia materializada de arquivos regulares. Não aponte para o repositório Git inteiro, nem para um ID remoto do Hub.

Nemotron pode ser a base textual, mas escolha a revisão exata e confirme seu suporte na versão do runtime. A ficha oficial do Nemotron 3 Nano informa integração nativa a partir de Transformers 5.3. Isso não constitui teste do Ultra nem de um checkpoint específico nesta entrega. Prefira um export nativo sem código Python do checkpoint. Modelos com código customizado exigem auditoria dos arquivos e a autorização explícita `--reviewed-local-code`; isso executa código sob a conta do operador, não dentro da sandbox de projetos. Não habilite essa opção só para contornar um erro.

Exemplo de sintaxe — substitua todos os campos pelos valores reais revisados:

```powershell
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" register-model text "D:\Modelos\texto-local" --model-id "ORIGEM/MODELO" --revision "REVISAO_IMUTAVEL" --license "LICENCA_REVISADA" --reviewed-by "OPERADOR" --device auto --dtype bfloat16 --context-tokens 8192 --output-tokens 1024

& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" register-model image "D:\Modelos\imagem-local" --model-id "ORIGEM/MODELO-VISUAL" --revision "REVISAO_IMUTAVEL" --license "LICENCA_REVISADA" --reviewed-by "OPERADOR" --device cuda --dtype float16
```

CPU: use `--device cpu --dtype float32`. Isso especifica a execução, não garante memória ou desempenho. Para imagens, `auto` não é suportado nesta versão. Não convertemos GGUF/NVFP4 nem fundimos adaptadores. Um LoRA isolado é rejeitado: este backend requer um checkpoint completo compatível. A arquitetura permite novos backends no futuro; não é necessário treinar do zero para fazer inferência local.

O registro recusa sobrescrita. Para substituir um modelo, pare o servidor, preserve o manifesto e checkpoint anteriores num backup privado, mova o manifesto ativo para outro nome e registre a nova revisão. Reverta restaurando o par anterior com o servidor parado. O registro verifica arquivos, não veracidade da licença nem competência do modelo.

## Executar no mesmo ambiente

```powershell
& $python -m localauthor token
& $python -m localauthor serve
```

Abra `http://127.0.0.1:8765/foundation` (ou a porta indicada pelo servidor). O token é local, não uma chave NVIDIA. Cadastre um projeto na tela principal e selecione-o no novo espaço. Modos: conversar, escrever/analisar código e criar imagem. O último produz 512 × 512, 20 passos e seed 31; é um perfil inicial, não configuração ótima para todo modelo visual.

Texto e imagem são submetidos à fila persistente existente. As gerações ficam serializadas; treino/indexação também usam a fila existente. Não há streaming de tokens nesta versão. O cancelamento é cooperativo: não interrompe um kernel GPU, tokenização ou carregamento bloqueado imediatamente. O limite de 300 segundos cobre o loop de geração, não garante timeout de todo o carregamento. Uma falha de conexão não deve provocar reenvio automático: consulte a tarefa nas ferramentas avançadas ou use o botão de retomar consulta.

Os loaders usam caminhos locais, `local_files_only=True`, Safetensors e variáveis offline/sem telemetria; não existe fallback para API externa de IA. Essas opções não são firewall. Bloqueie saída de rede no sistema operacional/contêiner para isolamento forte, principalmente se autorizar código customizado. O navegador/pesquisa da plataforma continuam funcionalidades distintas com autorizações próprias.

## Conhecimento Markdown

Os arquivos em `knowledge/` são material inicial e templates. Não são automaticamente carregados só por estarem no Git. Importe os documentos pertinentes ao projeto pelo comando abaixo com o servidor parado, um processo de importação por vez. O identificador é retornado pelo cadastro/listagem de projetos; não é o nome da pasta.

```powershell
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" import-md "ID_DO_PROJETO" ".\knowledge\core\PROCESSO.md" --title "Processo do LocalAuthor"
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" import-md "ID_DO_PROJETO" ".\knowledge\skills\CSHARP_DOTNET.md" --title "Procedimento C# e .NET"
```

A importação grava uma cópia privada UTF-8 e um manifesto com hash, escopo e `training_allowed=false`. Limites: 200 KB por documento, 200 documentos por projeto, trechos de 40 linhas e recuperação lexical. Ela não autoriza treinamento. O front matter não concede privilégios, e fontes entram como dados de usuário, não como instruções de sistema.

O contexto também consulta as evidências da memória já existente. A busca existente usa os primeiros 1.000 caracteres do pedido; o pedido integral é preservado para geração. O tokenizador do modelo calcula o orçamento real de contexto. Omissões de histórico/evidências e possível truncamento de saída são explicitados nos metadados. Os documentos precisam conter termos relevantes para a consulta: não há embeddings neste fluxo.

Para atualizar/remover uma fonte importada, pare o servidor, preserve um backup e remova a entrada antiga de `sources.json` e sua cópia privada; reimporte a versão revisada pelo CLI. Alteração de conteúdo sem atualização do manifesto bloqueia a consulta. Não há painel de edição desse manifesto nesta versão. Remover uma fonte não apaga experiências, conversas, backups ou datasets exportados que a contiveram: revise cada derivado antes de reutilizar.

## Processo operacional implementado

Nas orientações de cada projeto, selecione Geral, Desenvolvimento ou Marketing.
O perfil persiste somente naquele projeto e orienta respostas do modo foundation;
não concede ferramentas, publicação, uso de verba ou autorização para treinamento.
Scrum/Kanban, WIP e critério de pronto entram no contexto como dados do projeto.
Os contratos antigos de preferências continuam compatíveis. Há uma única fila de
inferência; ao trocar texto/imagem, o serviço libera o modelo anterior antes de
carregar outro, após verificar o candidato. Não mantém ambos residentes na RAM.

### Laboratório GGUF opcional

`qa/foundation/Dockerfile.gguf` usa o arquivo oficial CPU do llama.cpp b11429,
com SHA-256 conferido e extração limitada. `Dockerfile.cuda118-builder` prepara
uma compilação separada CUDA 11.8 para Turing/sm75, sem alterar o driver Windows.
Essas imagens não contêm pesos e não são o runtime ativo do aplicativo.

`scripts/foundation-gguf-probe.py` executa pesos GGUF locais conferidos em sandbox
Linux verificada, sem rede, root ou execução do código produzido. `--gpu` exige
CUDA0 e offload completo comprovado no log; não cai silenciosamente para CPU.
Registra contexto real, truncamento, saídas originais, hashes e latência.
Casos de captura não contam como acertos; resultados são de desenvolvimento,
sem treinamento, promoção ou equivalência com modelos de fronteira.

`scripts/foundation-code-oracle-worker.py` observa artefatos originais de C#,
JavaScript e PostgreSQL em **outra** sandbox inspecionada, sem pesos, segredos,
gabaritos ou mounts graváveis do host. Recebe apenas entradas via stdin.
O controlador externo preserva e compara resultados esperados. Nunca execute
esse worker como alternativa no Windows nem monte a pasta privada inteira.
Compilação, saída do worker e testes com dublês não qualificam o modelo.

Pedido validado → contexto limitado e isolado por projeto → inferência local → checagem de cancelamento → resultado e procedência → experiência não aprovada → gravação da conversa → revisão humana. Falha ao salvar a conversa dispara limpeza compensatória do resultado não revisado; não apaga experiências já revisadas. Uma queda abrupta entre os dois bancos pode deixar um candidato órfão, nunca autorizado para treino; requer reconciliação manual.

Código gerado é texto. Para aplicar, use o fluxo existente de snapshot/proposta/diff/testes/revisão. O novo modo não tem shell, Git, acesso de escrita ao projeto nem ferramentas agentivas. Instruções dentro do código ou da documentação não podem conceder essas capacidades.

## Experiências e dataset candidato

Experiências ficam em `foundation/experiences.sqlite3`, separadas por projeto; imagens em `foundation/artifacts/PROJETO/ID.png`. Limites iniciais: aproximadamente 32 MB para experiências, 256 MB para PNGs e 8 MB por PNG. Conversas continuam com sua quota própria. O token HTTP permite operar toda a instância; isolamento por projeto não é autenticação multiusuário.

Consultar e revisar pelo terminal do operador:

```powershell
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" experience "ID_DO_PROJETO" "ID_DA_EXPERIENCIA"
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" review "ID_DO_PROJETO" "ID_DA_EXPERIENCIA" --expected-hash "HASH_DA_SAIDA" --reviewer "OPERADOR" --verification-note "Como verifiquei o resultado e revisei direitos de todo o contexto e histórico" --accepted --verified --rights-reviewed --training-allowed --split train
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" export-training "ID_DO_PROJETO" text
```

Não marque decisões que não ocorreram. A revisão de direitos abrange **todo** o contexto, histórico, fontes, prompts, respostas e imagem exportados, não apenas a frase final. Aprovação de uso não implica correção; ambas não implicam permissão de treino. Não exporte material confidencial ou não autorizado. O CLI é exclusivamente do operador; nenhuma saída do modelo o chama.

Há exportações separadas `text`, `code` e `image`. A visual verifica o hash do PNG e registra seu caminho; não treina um modelo de imagem. O dataset é candidato, não formato universal de trainer. Exemplos com problema exatamente repetido em validation/test são excluídos; duplicatas semânticas, relações entre tarefas e contaminação via histórico precisam de curadoria adicional. Revogar permissão impede futuras exportações, mas não apaga exportações anteriores nem desfaz treinamento já realizado fora da aplicação.

Próximo estágio de pesquisa: separar tarefas por família/projeto, reservar avaliações inéditas, preparar receita de SFT/LoRA compatível, treinar um candidato, medir regressões e obter aprovação antes de promovê-lo. Não há treinamento, promoção ou autoverificação automática nesta entrega. `localauthor train` continua sendo o laboratório NumPy, não o trainer do Nemotron.

## Validação e limites de segurança

Execute `python scripts/run-tests.py`. A suíte nova `tests/test_foundation.py` cobre contratos de carregamento offline com dublês, hashes, caminhos, contexto, Markdown, decisões de curadoria, histórico, PNGs, autenticação e fila. `python scripts/foundation-ui-smoke.py` exercita a interface no Chromium usando dublês explicitamente identificados, não pesos reais.

Para homologar um modelo, com rede bloqueada, registre uma execução real de texto e uma visual, memória usada, duração, versões, comportamento de cancelamento, limites do tokenizador e inspeção das saídas. O verificador de conteúdo do pipeline visual é respeitado quando presente, mas sua existência não é garantida para qualquer modelo. Avalie a segurança e a licença do pipeline escolhido antes de expor a outros usuários.

Mantenha os diretórios privados sob a conta do operador, sem processos não confiáveis alterando arquivos simultaneamente. Hashes e rejeição de symlinks são defesa em profundidade, não isolamento contra um atacante com a mesma conta do sistema operacional. Não inclua pesos/dados/experiências nos commits. Nenhuma instalação local do usuário é alterada por um commit remoto; ela exige atualização e reinício.

## Referências de implementação

- Transformers, instalação e modo offline: https://huggingface.co/docs/transformers/installation
- NVIDIA, modelo e requisitos por revisão: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
- NVIDIA, Ultra e sua própria licença: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16
- Diffusers, AutoPipeline: https://huggingface.co/docs/diffusers/api/pipelines/auto_pipeline
- Diffusers, callbacks: https://huggingface.co/docs/diffusers/using-diffusers/callback

Documentação consultada em 05/10/2026; requisitos e licenças devem ser verificados na revisão exata escolhida, não inferidos do nome da família.
