# Fontes, revisão de referência e limites de compatibilidade

## Como interpretar este material

Este pacote foi preparado em 05/10/2026 por análise de código/documentação. Não executou testes na máquina do proprietário. O código pode evoluir depois: o executor deve conferir o HEAD e os contratos atuais antes de usar comandos.

As propostas de currículo, limiares, nomes ENG e organização de registros são **decisões propostas neste pacote**, não afirmações de que já foram implementadas nem padrões universais de treinamento. Os exemplos didáticos foram redigidos para este pacote e não foram compilados/executados nesta entrega.

## Fontes do repositório consultadas

Revisão fixa: `dd8a1376ad89230461fd85b2fcb5b5507590dcec`. Todos os caminhos abaixo pertencem a `rafaeldcs/ia-autoral`.

| ID | Caminho | O que fundamenta |
|---|---|---|
| R1 | `AGENTS.md` | Permissão de bases locais; dados fora do Git; preservação dos controles e evidências |
| R2 | `docs/FOUNDATION.md` | Escopo entregue, instalação, lacunas, quotas, importação, operação e limites |
| R3 | `src/localauthor/foundation/__main__.py` | Subcomandos reais: status, register-model, import-md, experience, review e export-training |
| R4 | `src/localauthor/foundation/runtime.py` | Loaders locais, template textual, perfil visual e cancelamento |
| R5 | `requirements-foundation.txt` | Faixas iniciais de dependências, sem lockfile homologado |
| R6 | `src/localauthor/cli.py` e `src/localauthor/__main__.py` | CLI raiz, home, diagnose, backup, serve e treino NumPy distinto |
| R7 | Metadados da branch `main` | Revisão fixa usada para evitar inferir estado futuro |

Endereços para conferir as fontes originais, sem depender de nomes de arquivo de conversas anteriores:

```text
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/AGENTS.md
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/docs/FOUNDATION.md
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/src/localauthor/foundation/__main__.py
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/src/localauthor/foundation/runtime.py
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/requirements-foundation.txt
https://github.com/rafaeldcs/ia-autoral/blob/dd8a1376ad89230461fd85b2fcb5b5507590dcec/src/localauthor/cli.py
```

## Documentação primária externa consultada

**T1 — Transformers, instalação e offline.** Uso de arquivos locais e modo offline requer preparação anterior dos artefatos; a opção da biblioteca não substitui controle de rede do sistema.

```text
https://huggingface.co/docs/transformers/installation
```

**T2 — Ficha oficial NVIDIA Nemotron 3 Nano BF16.** Consultada para entrada/saída textual, arquitetura, termos específicos e integração documentada com Transformers. Não é evidência de que o Ultra, outras gerações, outra quantização ou o equipamento do proprietário funcionem da mesma forma. A licença deve ser lida na revisão exata selecionada. Não foram usados rankings ou benchmarks como critérios de conclusão.

```text
https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
```

**T3 — TRL, SFT Trainer.** Apoio técnico para dados de conversa/prompt-completion e mascaramento das respostas. A opção assistant-only depende de suporte do template; validar máscaras reais no ambiente fixado. A documentação evolui e não comprova compatibilidade de um checkpoint concreto.

```text
https://huggingface.co/docs/trl/sft_trainer
https://huggingface.co/docs/trl/v0.28.0/en/sft_trainer
```

**T4 — PEFT, LoRA.** Apoio para distinguir base, adaptador e fusão quando suportada. A arquitetura/quantização precisam ser verificadas. Usar PEFT não transfere automaticamente conhecimento entre modelos de arquitetura diferente.

```text
https://huggingface.co/docs/peft/developer_guides/lora
https://huggingface.co/docs/peft/v0.21.0/package_reference/lora
```

**T5 — Diffusers, treinamento LoRA.** Apoio para receita visual separada e revisão de dependências/parâmetros específicos. Os exemplos oficiais podem conter upload e trackers externos; este pacote exige execução local sem essas opções.

```text
https://huggingface.co/docs/diffusers/training/lora
```

**T6 — Diffusers, callbacks.** Apoio ao uso de callbacks de etapa; cancelamento cooperativo não é interrupção imediata de qualquer operação.

```text
https://huggingface.co/docs/diffusers/using-diffusers/callback
```

**T7 — Diffusers, text-to-image e visão geral de treinamento.** Os scripts são específicos por tarefa/modelo; não existe uma receita única garantida para toda arquitetura visual.

```text
https://huggingface.co/docs/diffusers/training/text2image
https://huggingface.co/docs/diffusers/training/overview
```

**T8 — Microsoft, práticas de testes unitários .NET.** Referência geral de testes; as exigências adicionais de sandbox, hashes e promoção pertencem ao desenho do LocalAuthor.

```text
https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-best-practices
```

**T9 — PostgreSQL, LIMIT/OFFSET.** Apoio à ordenação explícita para subconjuntos determinísticos. A regra de “último registro” e o desempate precisam vir do requisito do projeto, não de suposição.

```text
https://www.postgresql.org/docs/current/queries-limit.html
```

## O que não foi verificado por este pacote

Compatibilidade real de PyTorch/CUDA/Windows no computador do proprietário; disponibilidade de pesos; aceitação de licenças; execução ou qualidade do Nemotron escolhido; geração/treinamento de imagens; suporte de todos os módulos a LoRA; memória/velocidade; resultado de treinamento; competência equivalente a outro produto.

Os links externos são referências, não autorização de rede, download, execução de código ou treinamento. Conferir revisões e termos atuais quando for executar. Manter recibos localmente.
