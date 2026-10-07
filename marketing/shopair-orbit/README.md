# Campanhas ShopAir e Orbit — rascunhos locais

Quatro propostas da LocalAuthor, revisadas tecnicamente: duas da ShopAir e duas do Orbit. Cada peça tem PNG para feed (1080 × 1350) e story (1080 × 1920), legenda, descrição, hipótese de teste e identificadores dos fatos utilizados. A direção original é provisória; ainda falta a escolha humana entre original e referência.

- `posts.json`: textos e calendário relativo proposto. Nenhuma data de publicação está confirmada.
- `assets/`: oito imagens exportadas e conferidas em Chromium isolado. ShopAir usa ilustração conceitual; Orbit reutiliza layout e logo anteriores da LocalAuthor com captura QA de dados fictícios.
- `gestao.html`: filtrar por marca, revisar legendas e anotar datas/notas. Precisa ser servido por HTTP com `posts.json` ao lado. Notas ficam no armazenamento deste navegador; esta tela não implementa banco compartilhado, agendador ou conexão às redes.
- `shopair-art.html` e `orbit-art.html`: fontes editáveis dos layouts. Os textos de cada exportação são aplicados pelo verificador de QA.
- `qa-functional.json` e `provenance.json`: verificações, hashes e autoria. Não representam autorização de publicação nem treino de pesos.

O painel foi verificado com filtro de marcas, salvamento/reabertura, celular, armazenamento indisponível/corrompido, JSON ausente e texto com HTML malicioso. As artes foram verificadas quanto a dimensões, imagens e corte de texto. Estes testes verificam funcionamento; não medem eficácia comercial.

## Gestão e medição

Revisar mensagem, marca, descrição, fonte e destino de cada peça antes de publicar. Para Instagram, configurar o destino na bio; legenda não recebe link clicável por simples inclusão de URL. O destino do Orbit ainda precisa de definição comercial. A ShopAir tem a página oficial `https://shopair.com.br/`, consultada em 7/10/2026; recursos anunciados não são resultados medidos.

O evento principal proposto é **pedido de demonstração qualificado**. Registrar publicação efetiva, canal, peça e URL com UTM; conferir instrumentação e consentimento no destino antes de atribuir conversões. Comparar propostas em períodos equivalentes, separando alcance, cliques, pedidos e custo quando houver gasto. Sem campanha publicada não há CTR, CPA, receita atribuída ou vencedor de teste.

Publicação, contas de redes, investimento e aprovação humana permanecem pendentes. Nenhum conteúdo foi enviado às redes; nenhuma verba foi consumida. A aprovação editorial da IA e os testes não substituem a revisão comercial.

## Reproduzir QA

`qa/functional-lab/marketing-delivery-regression.cjs` roda exclusivamente no laboratório Docker verificado, com `/tmp/marketing` contendo este diretório, o logo em `orbit/brand/orbit-logo-inverse.svg` e a captura sintética em `orbit/images/product.png`. Usa o Playwright local de `/opt/node_modules/playwright`, sem serviços externos de IA.

O verificador sobe HTTP apenas no loopback do contêiner e escreve evidências em `/tmp/evidence`. Executar com rede desativada, raiz somente leitura, usuário 10001, sem capacidades, `no-new-privileges`, limites de memória/CPU/processos e entradas conferidas. O operador desta entrega está na pasta privada `LocalAuthor-Delivery/shopair-orbit-qa-marketing-20261007`; não executar fontes geradas diretamente no host.

A captura da ShopAir autenticada não é usada nos anúncios ou versionada. Credenciais, registros completos e propostas rejeitadas ficam privados no servidor. Consulta às fontes e feedback operacional não concedem direitos para treinamento.
