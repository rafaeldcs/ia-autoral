# Currículo de criação visual e especialização

**Uso:** ensino e desenvolvimento. Não é um dataset de imagens pronto. Briefs deste documento são conhecidos pelo executor e não podem ser apresentados como prova final inédita.

## Dois aprendizados separados

O eixo textual aprende a transformar pedido em brief e selecionar parâmetros suportados. O eixo visual aprende, quando necessário e autorizado, uma adaptação de estilo/domínio a partir de imagens reais. Não contabilizar exemplos de prompts como se fossem exemplos de treinamento dos pixels.

## Módulos

| Módulo | Objetivo | Material necessário | Verificação |
|---|---|---|---|
| VIS-01 | Interpretar requisitos | Pedido e brief estruturado | Nenhuma restrição obrigatória perdida |
| VIS-02 | Objeto único | Imagens autorizadas de formas/objetos simples | Quantidade, cor e objeto conferidos |
| VIS-03 | Relações espaciais | Composições com dois/três elementos | Esquerda/direita, frente/fundo e contagem |
| VIS-04 | Materiais e luz | Exemplos com descrição coerente | Material/iluminação e ausência de contradições |
| VIS-05 | Ícones e séries | Série original autorizada | Consistência e legibilidade em tamanho pequeno |
| VIS-06 | Produto e enquadramento | Fotos próprias ou licenciadas | Proporção e detalhes pertinentes preservados |
| VIS-07 | Brief em português | Pedidos variados e descrição do pipeline | Aderência ao pedido, não apenas tradução literal |
| VIS-08 | Limites de texto/formato | Pedidos fora do perfil atual | Explicar restrição sem fingir imagem pronta |
| VIS-09 | Especialização visual | Dataset de estilo/domínio autorizado | Ganho sobre base e ausência de memorização excessiva |
| VIS-10 | Persistência/reprodução | PNGs, parâmetros, hashes e versões | Recarga/consulta e resultado rastreável |

## Briefs de desenvolvimento

Um vaso amarelo isolado, fundo azul-claro, sem texto. Dois blocos geométricos, vermelho à esquerda e verde à direita. Uma caixa branca sobre superfície escura, iluminação lateral suave. Um ícone de livro aberto, fundo uniforme e sem letras. Uma série de três ícones originais de organização, todos com a mesma espessura visual e paleta.

Inspecionar cada saída e registrar o que falhou. Se o modelo trocou a posição dos blocos, não reescrever o brief para coincidir com a imagem. O professor pode propor um brief melhor, mas isso é outra tentativa.

## Estrutura de exemplos de treinamento

Para especialização visual, cada exemplo deve ter uma imagem íntegra e uma legenda fiel. Incluir grupos de origem para evitar que recortes da mesma arte atravessem partições. Não usar imagens finais do avaliador no dataset. Revisar termos de uso e autorização para pessoas/marcas quando pertinentes.

Não fixar um número universal de imagens. Começar com um conjunto pequeno autorizado para validar o pipeline; definir a necessidade de expansão por diversidade, desempenho de validação e sinais de memorização. Um conjunto minúsculo pode permitir teste técnico sem sustentar generalização.

## Rubrica de desenvolvimento

Avaliar de 1 a 5 aderência ao brief, composição, coerência de formas, qualidade visual e adequação ao uso. Requisitos obrigatórios são verificados à parte: média alta não compensa objeto ausente ou restrição violada. Guardar todas as tentativas avaliadas, não apenas as escolhidas para mostrar.

O perfil atual usa uma seed e resolução fixas; registrar esse limite. Quando novos perfis forem implementados, repetir avaliação com conjunto predefinido de seeds e dimensões. Edição de imagens e visão entram somente após implementação própria, fora do mínimo v1.
