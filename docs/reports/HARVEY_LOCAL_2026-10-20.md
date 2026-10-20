# Harvey LAB — evidências de integração local, 20/10/2026

O núcleo do Harvey LAB foi executado com os pesos locais já existentes da LocalAuthor, sem API de IA externa e sem importar o benchmark para treinamento. Esta entrega implementa avaliação; não altera os pesos nem homologa competência jurídica, comercial ou autonomia geral. Operação e dependências: [HARVEY_LOCAL.md](../HARVEY_LOCAL.md).

## Fonte e adaptações

Fonte MIT: [harveyai/harvey-labs](https://github.com/harveyai/harvey-labs), revisão `97810facfd447317b57f6dd02a1469561c573d79`, `lab-core` 1.2.0. Inventário completo por objetos Git: **2.010 tarefas e 114.437 critérios**, incluindo o corpus compartilhado indicado por `docs_dir`.

Foram utilizados o ciclo original do agente, as sete ferramentas, os parsers, o scorer, o gerador de relatório e os comparativos originais. A inicialização Podman foi adaptada para Docker verificado; transporte, avaliador e fallback de nomes de arquivo foram substituídos explicitamente por inferência local. O HTML original, que pode conter texto não escapado, é preservado como `.untrusted`; o acompanhamento usa HTML escapado e política de conteúdo restritiva.

Imagem executada: `sha256:66e10ff6ffc2a98cc8f0f14d99f0136289c0c4016932e8741a0c4e54e969b1cd`. Worker sem rede, raiz somente leitura, usuário sem privilégios, duas montagens somente leitura, trabalho/saída em tmpfs limitado. Cada tentativa guarda gerações, transcrição, hashes, critérios e erros. A implementação e o modelo de cada lote são congelados; resultados concluídos não são reclassificados ao retomar.

## Verificações de software concluídas

| Verificação | Resultado observado | Limite da evidência |
| --- | --- | --- |
| Suíte Python completa após o reforço final de retomada | 695 testes, zero falhas/erros, três skips de links simbólicos indisponíveis no Windows local | Não mede inteligência; CI da revisão publicada é conferido separadamente |
| Motor original, sete ferramentas e parsers DOCX/XLSX/PPTX/PDF | Execução real em Docker aprovada, incluindo bloqueio de rede e escrita nas entradas/controlador | Modelo e juiz roteirizados neste smoke |
| Todas as rubricas originais sem entregáveis | 2.010 tarefas / 114.437 critérios corretamente reprovados, sem erro de avaliação | Avaliador negativo determinístico; não são acertos da IA |
| Código `billing.py` gerado no piloto real | Sete asserções numéricas independentes aprovadas em nova sandbox | Exercício sintético pequeno; não certifica projetos arbitrários |
| Comparativos originais | Dashboard gerado para três lotes de desenvolvimento terminados, preservando falhas | Mesmo avaliador local; custos de API zero não medem energia/tempo; tokens de saída não medidos |

SHA-256 do código avaliado pelas sete asserções: `1f6c9b461bc2a6864bd037f948d141ddef7040116997fdaf7eecbdcdb8b4a01e`. Ele foi produzido pela LocalAuthor; o script de conferência independente foi preparado pelo operador e executado na sandbox.

## Piloto com inferência real

Modelo existente: `unsloth/Qwen3.5-4B-GGUF`, backend GGUF Docker/CUDA, contexto de 4.096 tokens, saída de até 1.536 tokens. O lote final de desenvolvimento terminou com **três aprovações provisórias em quatro cenários**:

| Cenário sintético | Estado |
| --- | --- |
| ShopAir: postagem baseada nos fatos fornecidos | Reprovado; a proposta acrescentou “demonstração gratuita”, oferta não informada no contexto. O parecer do juiz também apresentou justificativa parcialmente incorreta |
| ShopAir: respeitar recusa de contato comercial | Aprovado provisoriamente |
| Programação, testes executados e relato | Aprovado provisoriamente; código também passou nas sete asserções independentes |
| Plano de QA com riscos | Aprovado provisoriamente; produzir um plano não significa executar uma aplicação real |

O modelo também é o juiz. Seus pareceres não são independentes e exigem revisão humana. Pilotos anteriores mantêm falhas de protocolo e de avaliação; não foram descartados para apresentar um resultado melhor. Os critérios não foram reduzidos. A integração solicita correção de chamadas inválidas ao próprio modelo, com limite explícito, sem executar ou reparar silenciosamente essas chamadas.

## Tarefas jurídicas originais: lote em andamento

As **2.010 tarefas** entraram no estado persistente do lote original, com as rubricas completas. No corte deste relatório, cinco tarefas haviam terminado reprovadas, uma estava em execução e 2.004 aguardavam. **Isso não é conclusão nem aprovação do benchmark completo.** O `state.json` e o `report.html` privados trazem o progresso posterior; números deste documento são apenas um corte datado.

O lote ativo usa cópia congelada integral do controlador e clone Git privado da revisão original, para que atualizações do projeto não mudem a implementação durante a medição. Essa cópia antecede o reforço de conferência do hash de todos os fontes de inferência na retomada, ajustes de apresentação do relatório de erro e limpeza de imports. O motor, as ferramentas e os critérios de avaliação do lote permanecem os congelados. Não há descarte silencioso do histórico quando o contexto se esgota: o limite aparece como falha. O comando não reinicia automaticamente com o Windows; a retomada explícita exige a mesma configuração congelada.

## Pendências de qualificação

Concluir o lote jurídico, revisar amostras e divergências do juiz, corrigir limitações com novos lotes comparáveis e realizar avaliação independente continuam necessários. O erro de marketing e os limites de contexto impedem afirmar “100% aprovado”, “qualquer tarefa” ou equivalência com um modelo de fronteira. Não houve novo treinamento nesta entrega.

Transcrições, documentos, artefatos e resultados individuais permanecem no armazenamento privado de benchmarks do servidor, fora do Git. O código público contém somente infraestrutura, testes e cenários sintéticos. O instalador Windows 0.3.13 não foi alterado por esta ferramenta opcional de operador.
