# Pipeline experimental de aprendizado foundation

O laboratório NumPy e este pipeline são componentes diferentes. Os comandos abaixo existem em `python -m localauthor.foundation.learning --help`. Nenhum deles é ferramenta liberada ao modelo pelo chat. Não há dependência de API externa de IA nem download durante inferência/treino.

## Ambiente homologado para os testes de integração

O ambiente dedicado usa Python 3.12, PyTorch 2.6 CPU, Transformers 4.57.6, PEFT 0.18.1 e Diffusers 0.35.2. As dependências principais estão fixadas em `requirements-learning.txt`; construa `qa/foundation/Dockerfile` somente na aquisição autorizada. Registre o digest da imagem e as versões transitivas efetivas. Transformers 5.3 carregou o Qwen, mas falhou com o verificador do Stable Diffusion neste experimento; não é o perfil visual adotado.

Execução de treino, export e avaliação exige container Linux sem rede, usuário não root, capabilities removidas, no-new-privileges, seccomp e raiz somente leitura. Inspecione também mounts, imagem e limites antes de iniciar. Os canários não substituem a inspeção do Docker. Pesos e código são montados somente para leitura; somente a área privada de resultados é gravável. Não monte dados ativos, segredos, socket Docker ou a avaliação final no trainer. Não há fallback para Windows/host.

O primeiro trainer suporta **Qwen3 nativo, CPU/float32, LoRA em q_proj/v_proj**. Não homologa Nemotron, todas as arquiteturas, GPU ou quantização. O perfil visual suporta **StableDiffusionPipeline nativo**, com verificador habilitado, dimensões 256–768 em múltiplos de 64, seed explícita, 1–50 passos e guidance 1–15. Imagens reais continuam exigindo julgamento de qualidade.

## Capacidade antes de adquirir outra base

`preflight REQUISITOS.json HARDWARE.json --report NOVO.json` faz uma conferência offline dos orçamentos declarados, sem baixar ou carregar pesos. Ambos os documentos usam `schema: 1`. Requisitos contêm `model_id`, revisão Git imutável `revision`, URLs técnicas `sources`, `weights_bytes` (todos os especialistas de um MoE), `additional_weight_copies`, `additional_disk_overhead_bytes`, `required_ram_bytes` e `gpu_profiles`. Cada alternativa GPU declara `family`, `count` e `minimum_memory_bytes_each`. Não combina famílias diferentes para completar uma alternativa.

Hardware contém `total_ram_bytes`, `available_ram_bytes`, `free_disk_bytes` e `gpus`, cada GPU com `family` e `memory_bytes`. Use famílias normalizadas iguais nos dois documentos e registre data, comando e proveniência da medição. Atualize RAM/VRAM livre e disco antes de executar; uma medição antiga ou VRAM total pode superestimar disponibilidade. Orçamentos de staging, cache KV, runtime, treino, export e cópias temporárias precisam ser estimados separadamente pelo operador. Zero indica somente um limite inferior declarado, não ausência comprovada de consumo.

O relatório conserva hashes dos dois documentos e nunca sobrescreve evidências. Falta de disco/RAM/perfil GPU retorna `blocked` e exit 1; entrada inválida retorna exit 2. Mesmo com capacidade suficiente, retorna somente `capacity-only`, `acquisition_authorized: false` e `qualification_suite: false`. Não homologa licença, driver, arquitetura, desempenho ou inteligência. RAM e VRAM não são somadas.

Na revisão `02462641f13d3af838b904f48195b9bb8a1e4ebc` do [Nemotron 3 Ultra NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4/tree/02462641f13d3af838b904f48195b9bb8a1e4ebc), o inventário oficial lista 113 arquivos Safetensors somando 352.308.689.576 bytes. O [model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4/raw/02462641f13d3af838b904f48195b9bb8a1e4ebc/README.md) recomenda, entre outras alternativas, quatro B200 ou oito H100. O servidor observado em 5 de outubro tem cerca de 16 GiB de RAM, RTX 2060 de 6 GiB e 182 GB livres: não atende nem ao disco dos pesos, nem ao perfil GPU. Não foi adquirido/carregado/treinado e não houve chamada a uma API NVIDIA.

O [Nemotron Nano 4B GGUF oficial](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF/tree/ba223d14e45525f7fae81db77ea8cabeb2fc6c25) tem um Q4_K_M de 2.837.072.864 bytes. É candidato a investigação de inferência local, sem equivalência ao Ultra. O runtime atual de treino Qwen3/Safetensors não suporta esse GGUF híbrido Mamba2; exige outro runtime homologado, revisão da licença e testes reais de português/código/segurança/latência antes de integração. O arquivo `LICENSE` desse repositório é vazio; conserve o texto integral da licença oficial vinculada pelo model card, sem tratar o arquivo vazio como autorização. Não há aquisição ou promoção implícita nesse diagnóstico.

## Dados e recibos

O schema 1 exige fontes locais com hash, licença, estado de revogação e recibo. Cada exemplo preserva todas as mensagens, hashes de contexto/alvo, família, grupo de projeto, grupo de vazamento, modalidade e partição train/validation. A avaliação final não é entrada do trainer.

Aceitação, verificação técnica, direitos e autorização para treinamento são decisões distintas. O recibo precisa existir, ter hash conferido e vincular o conteúdo exato da fonte e do exemplo. Esses arquivos são declarações do operador; não constituem uma assinatura criptográfica de identidade humana. O modelo não cria suas próprias aprovações. Um teste com fixtures explicitamente identificadas não autoriza dados de produção.

`validate-data DATASET.json` verifica essas condições, integridade UTF-8, segredos, conteúdo integral nas fontes, duplicatas e separação por grupos. A heurística de variantes não garante deduplicação semântica universal. O índice de alvos reservados é somente de hashes, sem gabaritos. Ele precisa ser preparado pelo avaliador; uma lista vazia não comprova independência.

O CLI de experiências exporta train e validation separadamente com `export-training PROJETO TIPO --split validation`. Test não é exportado por esse fluxo. `convert EXPORT.jsonl CURADORIA.json --output DATASET.json` exige hash do export, projeto/saída exatos, contexto original, integridade, grupos previamente revisados e fontes transitivas autorizadas. Não inventa direitos, agrupamento ou partições. Publica somente após validar o resultado completo.

## Experimento, treino e export

O manifesto congela revisão Git real, alterações locais, hashes dos módulos foundation/controles, versões efetivas, base, tokenizer, dataset, seed, limites, hipótese e critérios. Mudança de código, runtime, dados ou receita invalida retomada/export.

`train EXPERIMENTO.json --base-manifest BASE.json --dataset DATASET.json --output PASTA_NOVA [--resume CHECKPOINT]` mantém a base congelada, calcula perda somente na resposta/EOS e rejeita truncamento, NaN/Inf e atualização fora do adaptador. A receita fixa batch 1, AdamW, peso de regularização zero, learning rate constante, dropout zero e clipping declarado; a configuração efetiva é registrada.

O checkpoint salva adaptador e otimizador em Safetensors, estado RNG e JSON de configuração, sem pickle. Registra atualização dos tensores, loss, gradientes, base preservada e igualdade após recarga. SIGTERM solicita cancelamento cooperativo. O limite de tempo é conferido entre operações; um kernel bloqueado precisa do limite externo de execução. Falha/interrupção deixa recibo, sem promoção.

`export EXPERIMENTO.json --base-manifest BASE.json --dataset DATASET.json --checkpoint CHECKPOINT --output PASTA_NOVA --model-id IDENTIDADE --reviewed-by REVISOR` funde um checkpoint completo em **outra** pasta, preserva licença/procedência e recarrega o modelo nativo. Compara logits antes/depois da fusão e após recarga. Não apague adapter_config para fingir que um adaptador isolado é uma base completa.

`--output-bytes` limita separadamente a exportação completa (padrão/máximo 10 GB). O orçamento do treino cobre adaptador/otimizador, não o modelo fundido. A exportação verifica estimativa/espaço antes de escrever pesos e tamanho efetivo antes de registrar o candidato; planeje ambos os orçamentos antes do piloto.

## Avaliação, promoção e reversão

`evaluate MODELO.json CASOS.json --report NOVO.json` executa pesos reais com oráculos exact/JSON, registrando todos os erros, vazios e truncamentos no denominador. **Este avaliador textual ainda não substitui compilação funcional, julgamento semântico ou rubrica visual.** Seu relatório mantém `qualification_suite: false`.

`compare --base-manifest BASE.json --candidate CANDIDATO.json --cases CASOS.json --output PASTA_NOVA` exige as mesmas condições de geração e conserva os dois relatórios. Regressões rejeitam o candidato. Um replay de exemplos de treino é avaliação de desenvolvimento, não prova inédita de competência.

`promote --home INSTALACAO --candidate CANDIDATO.json --evaluation AVALIACAO.json --approval APROVACAO.json` exige qualificação completa e aprovação humana vinculadas aos hashes exatos. Smoke/replay textual não libera promoção. O servidor precisa estar parado. A troca do ponteiro é atômica, com journal anterior preservado. `rollback --home INSTALACAO JOURNAL.json` confere versão ativa e hashes; não sobrescreve uma promoção posterior. Contratos com fixtures não equivalem a rollback comprovado de um modelo aprovado em produção.

## Provas opt-in e limites atuais

`foundation-trainer-check.py` usa uma **rede pequena original aleatória**, com tokenizer Qwen licenciado: prova atualização, cancelamento, retomada idêntica, fusão/recarga e rejeição de NaN. Não especializa o Qwen adquirido nem mede competência.

`foundation-real-smoke.py` usa o checkpoint Qwen real e somente as sete notas destinadas a consulta. `foundation-pilot-baseline.py` congela/reexecuta exemplos próprios de desenvolvimento, sem treinamento e sem independência final. `foundation-visual-check.py` usa pesos visuais reais, verifica PNG, recuperação, seed, tamanho, cancelamento e limite do tokenizer. `foundation-real-image-ui.py` mostra um PNG já gerado pela interface autenticada; não recria pixels nem usa dublê visual.

Os relatórios e datasets ficam privados fora do Git. As falhas reais são preservadas. Aprovação de dados, piloto sobre a base adquirida, avaliação final independente, integração/ativação na instalação Windows e promoção continuam sendo etapas separadas. Não há qualificação geral de programadora autônoma, compreensão/edição de imagens, fine-tuning visual ou autorização de limpeza dos roteiros por este incremento.

## Resultados observados em 5 de outubro de 2026

- A suíte normal passou de 291 para 328 testes, sem falhas/erros/skips no laboratório Linux. Isso mede contratos e regressões, não competência dos checkpoints.
- O Qwen3-0.6B, revisão `c1899de289a04d12100db370d81485cdf75e47ca`, foi carregado localmente. O replay de desenvolvimento com oito casos e oráculos literais/JSON acertou **1/8** e foi rejeitado. Houve afirmação de sucesso sem execução e SQL truncado; divergências literais também não substituem julgamento semântico. Nenhum desses casos é prova final independente.
- As sete notas foram importadas para consulta em um projeto separado da instalação real, sem autorização de treino. A reimportação foi idempotente. Trinta consultas internas recuperaram a identidade esperada; hashes/trechos, escopo incorreto e consulta sem fonte foram conferidos. A busca é lexical e esse resultado não mede trinta respostas corretas do modelo nem prova independência da avaliação.
- O Stable Diffusion 1.5, revisão `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`, gerou PNGs reais de 512 × 512. A prova funcional passou com seed repetida, armazenamento, recarga, cancelamento e limite de tokenizer. No perfil CPU com quatro threads, cada geração levou aproximadamente 190–207 segundos. A mesma seed produziu bytes iguais somente no mesmo perfil; tentativas anteriores falharam por incompatibilidade, bloqueio visual ou tempo e foram conservadas.
- O PNG real foi recuperado pela interface autenticada. O navegador também verificou os controles com dublês identificados, sem desativar a política CSP. Nenhuma nota humana de qualidade visual foi inventada.
- A rede pequena original comprovou atualização dos adaptadores, base preservada, recarga, cancelamento, retomada idêntica, fusão/recarregamento, rejeição de NaN, retomada divergente e orçamento de exportação. **O checkpoint Qwen adquirido não foi treinado.**
- O backup privado do servidor foi restaurado em outra pasta, com hashes conferidos e integridade dos sete bancos SQLite preservados. A instalação ativa manteve seus dados e nenhum checkpoint foundation foi promovido.

Esses resultados descrevem execução em andamento. O alvo N4, o treino autorizado da base adquirida, a avaliação final e a promoção permanecem pendentes; os roteiros Markdown permanecem necessários.

## Backup do servidor

O perfil padrão continua limitado a 512 MB/20.000 entradas. O operador pode escolher `backup ARQUIVO.zip --server-profile` e `restore ARQUIVO.zip PASTA_NOVA --server-profile`: até 10 GB/50.000 entradas, incluindo exports. Tokens API e locks não são restaurados; locks aninhados só podem ser omitidos depois de comprovar processo inativo. O arquivo é privado e pode conter outros dados/credenciais da instalação: não publicar no Git/share público.

`scripts/lan/Stop-ServerForMaintenance.ps1` confere identidade, fila vazia e membros do console, então solicita Ctrl+C normal. Não força o backend nem remove seu lock. `maintenance-until.txt` no diretório LAN pausa relançamentos por até duas horas; preserve o script anterior e remova somente o marcador criado pela operação ao terminar. Restaure em outra pasta, confira hashes/bancos e religue o supervisor mesmo se o backup falhar.
