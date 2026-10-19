# ShopAir — revisão supervisionada de leitura e identidade

Continuação do [benchmark visual](SHOPAIR_VISUAL_BENCHMARK_20261019.md), em 19/10/2026. O arquivo de avaliação recebido registrou preferência pelas três candidatas e solicitou melhorar leitura/nitidez de textos e logos em catálogo e restaurante. A preferência não foi convertida em homologação geral, autorização de publicação ou de treinamento. O arquivo original e suas decisões permanecem em armazenamento privado.

## Experimento realizado

O supervisor forneceu esse feedback ao motor textual local, `unsloth/Qwen3.5-4B-GGUF`, revisão `e87f176479d0855a907a41277aca2f8ee7a09523`, já existente, via `FoundationService`. A execução usou o backend Docker offline registrado. Não foram baixados modelos nem usados serviços externos de IA.

A primeira resposta produziu briefings de fotografias sem inscrições, mas confundiu a ShopAir com uma loja de objetos e um restaurante nos textos comerciais. O supervisor rejeitou essa redação, explicou que o produto é uma plataforma de e-commerce/cardápio digital e pediu nova resposta. A LocalAuthor corrigiu a mensagem para apresentar loja online e cardápio digital. A resposta inicial foi preservada: o acerto posterior não transforma a primeira tentativa em aprovada.

As fotografias foram geradas pelo `FoundationService/ImageRuntime`, usando o mesmo SD 1.5, manifesto, runtime CUDA e snapshot de fonte `a28a71c7711e0953d012563e2c90ee065ecb4a31` identificados no benchmark. Foram mantidas sandbox inspecionada, rede desativada, pesos somente leitura, verificador visual ativo e verificação dos hashes. Não houve execução de código gerado. Os controladores e artefatos desta avaliação ficaram privados.

| Captura | Pixels nativos | Passos | Seed | Geração observada |
| --- | --- | ---: | ---: | ---: |
| Catálogo: vasos sem inscrições | 768 × 512 | 40 | 1102 | 11,37 s |
| Restaurante: primeira direção | 768 × 512 | 40 | 1103 | 20,79 s |
| Restaurante: direção corrigida | 768 × 512 | 40 | 1103 | 11,34 s |

As três capturas foram entregues tecnicamente. A primeira fotografia de restaurante foi rejeitada pelo supervisor por tingir excessivamente a comida de roxo. O supervisor devolveu essa falha ao motor textual: preservar cores naturais dos alimentos e reservar as cores da marca ao fundo/composição. A LocalAuthor refez o prompt, e uma nova inferência produziu uma salada com cores naturais. As duas tentativas e seus prompts foram preservados. Essas latências, com prompts diferentes e apenas uma captura cada, **não demonstram aceleração do modelo**.

## Texto e logo exatos

Em vez de solicitar inscrições ao difusor, o supervisor montou duas peças experimentais em canvas com a logo PNG oficial já verificada e as fontes Outfit locais licenciadas. Texto comercial e briefings são respostas da LocalAuthor, revisadas; layout, composição e QA são trabalho do supervisor. Não se trata de composição autônoma pelo modelo, leitura de imagens pelo motor textual ou treinamento dos pesos.

Cada PNG final tem 1080 × 1350; a fotografia ocupa seus 768 × 512 pixels nativos, sem ampliação. A logo e as letras são desenhadas separadamente. Isso elimina inscrições inventadas nesta composição e permite leitura nítida do texto final; não recupera detalhe perdido de fotos anteriores nem comprova qualidade fotográfica universal. As fotos são ilustrativas, não telas do software ou produtos de clientes reais.

## Verificação e resultado

A galeria V2 contém a candidata anterior, nova composição, foto original, relatórios de inferência e respostas do motor textual. A execução real no Edge verificou oito itens: decodificação das imagens; dimensões dos PNGs; download com bytes iguais; ausência de rolagem horizontal no celular; decisões inicialmente pendentes; preservação de Unicode/aspas/markup no JSON de comentário; ausência de consentimento implícito para publicação/treino; e limpeza das escolhas de teste ao recarregar. Não houve erro JavaScript. As escolhas de QA não representam avaliação do proprietário.

A suíte local voltou a executar 593 testes, com **590 aprovados, zero falhas/erros e três skips de symlink por privilégio indisponível no Windows**, usando `PYTHONUTF8=1`, como no workflow. A execução anterior desta sessão, sem essa configuração documentada, falhou em uma comparação de texto UTF-8 lido com o encoding padrão do Windows; o relatório dessa tentativa também foi preservado. Nenhum teste ou critério foi removido para passar. A cobertura local permanece incompleta nos três skips; a conclusão do CI remoto deve ser conferida pela revisão publicada, sem tratar jobs em fila como aprovados.

**Estado:** nova revisão visual pendente do proprietário; publicação e treinamento não autorizados; pesos intactos; modelo de imagem não ativado no servidor principal. O feedback foi usado como contexto de uma tarefa supervisionada e registrado nas evidências, sem importar a avaliação para corpus ou alterar checkpoints. A correção não demonstra autonomia de marketing nem aprendizado permanente.

## Regra reutilizável

Uma marca precisa manter textos, nomes, preços e logo como conteúdo exato, fora da geração fotográfica. Prompt negativo ajuda, mas não garante ausência de letras falsas. Antes de compor, conferir o que a empresa realmente vende; separar cor da identidade de cor natural dos objetos; preservar falhas e comparar originais. Somente a avaliação humana pode aprovar a peça final. A aprovação visual, a publicação e o uso em treinamento continuam decisões distintas.
