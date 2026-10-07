# Fontes primárias e procedência

Consultadas em 2026-10-07. URLs em `main` e páginas de produto são mutáveis: antes de reproduzir um experimento, fixar revisão efetiva, salvar manifesto local e registrar hashes. Não foram baixados nem licenciados em nome do usuário pesos ou datasets nesta entrega. Nenhuma revisão de checkpoint é inventada aqui.

| ID | Fonte primária | Uso no estudo |
|---|---|---|
| S1 | https://github.com/JustVugg/colibri | Hierarquia de pesos e motores por arquitetura; não prova suporte Nemotron |
| S2 | https://github.com/NVIDIA-NeMo/Nemotron | Catálogo de receitas, modelos, datasets e avaliações; selecionar subconjuntos |
| S3 | https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 | Arquitetura Lightning; parâmetros totais versus ativos; homologação por checkpoint |
| S4 | https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 | Alternativa menor; Mamba/MLP/atenção, diferente do MoE Lightning |
| S5 | https://github.com/JustVugg/colibri/blob/main/docs/ENVIRONMENT.md | Controles experimentais: não adotar alterações de seleção como padrão |
| S6 | https://www.kingston.com/en/blog/servers-and-data-centers/understanding-ssd-endurance-tbw-dwpd | TBW, DWPD e programação/limpeza da NAND; não é diagnóstico do SSD do usuário |
| S7 | https://huggingface.co/nvidia/llama-nemotron-embed-1b-v2 | Candidato de recuperação semântica; validar no corpus local |
| S8 | https://arxiv.org/abs/2106.09685 | Artigo original de LoRA; adaptação não é transferência integral de conhecimento |
| S9 | https://developer.nvidia.com/blog/developing-nemotron-3-5-lightning-nvfp4-with-qad-using-nvidia-model-optimizer/ | Quantização e distilação; motivação para pesquisa local, não ganho garantido |
| S10 | https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16 | Percepção multimodal com saída textual; não confundir com gerador de imagens |
| S11 | https://docs.nvidia.com/nemotron/latest/nemotron/lightning35/quantization.html | Receita técnica PTQ/QAD de referência; não executada neste PR |
| S12 | https://www.micron.com/sales-support/downloads/software-drivers/storage-executive-software | Exemplo de informações SMART/temperatura/vida útil específicas do fabricante; não usado para alterar discos |
| S13 | https://github.com/python/cpython/issues/157671 | Diferença entre `stat(path)` e `fstat(fd)` no Windows; justificativa para metadados obtidos de forma consistente pelo descritor |

## Reutilização responsável

As implementações novas de `efficiency` foram escritas para o LocalAuthor; não se declara um port linha a linha do Colibri. O repositório Colibri consultado identifica Apache-2.0, mas qualquer incorporação futura de arquivos deve preservar avisos e sua licença específica. Para modelos, datasets, tokenizadores e código auxiliar, revisar cada licença separadamente: não presumir que a licença de um repositório cobre todos os ativos ligados por ele.

A origem de um checkpoint adaptado continua registrada, assim como professor usado, dataset, receitas e revisões. Usar localmente não transforma pesos de terceiros em pesos treinados do zero pelo LocalAuthor. Identidade de produto e procedência técnica são campos diferentes.

Os Markdown de conhecimento deste PR são textos de orientação para consulta, não cópias de datasets externos. Os exemplos de testes são gerados/sintéticos e identificados como tal. Nenhum segredo, corpus privado ou modelo real foi incorporado.

## Leituras deliberadamente não usadas como prova

Não usar forks, vídeos, manchetes ou um resultado publicado em outra GPU como prova do desempenho neste notebook. Não assumir que uma ficha de modelo, uma variável de ambiente ou um hash por si só demonstre compatibilidade, segurança ou execução. Os limites observados nos testes estão em README e no PR.
