# Orbit — anúncio para demonstração e piloto

A peça principal é o novo anúncio de venda: [PNG](exports/orbit-venda.png),
[JPEG](exports/orbit-venda.jpg) e [layout editável](anuncios/orbit-venda.html).
Abra [index.html](index.html) para visualizar e baixar a imagem. A mensagem aprovada
na revisão é “Projetos e código em um lugar”, com a chamada “Solicite uma demonstração”.
A [legenda](anuncios/copy-venda.json) acompanha a proposta.

Esta revisão responde à rejeição do proprietário em 7 de outubro: o kit anterior
parecia uma apresentação técnica. As peças anteriores em [exports](exports/) e as
fotos em [images](images/) ficam como protótipos de apoio, não como anúncios aprovados
pelo proprietário. O novo anúncio usa uma captura real do produto com dados de QA;
não foi gerada uma nova foto nesta revisão. A autoria textual e do layout é da
LocalAuthor, com seleção e validação supervisionadas, registradas na
[proveniência desta revisão](anuncios/LOCAL_AI_SALES_AD_PROVENANCE.json).

A oferta é uma demonstração do produto em homologação, com condições do piloto a
combinar. O destino de contato ainda precisa ser definido antes de publicar.
Não houve publicação social nem teste de conversão com público real.

## Identidade visual

A marca atual está em [brand/README.md](brand/README.md), com SVGs, PNGs
transparentes, versões de cor, ícone e guia. O anúncio principal usa essa identidade.

## Material e uso

- [Estratégia comercial](ESTRATEGIA_COMERCIAL.md): público, posicionamento, oferta e funil.
- [Pesquisa e direção visual](PESQUISA_E_DIRECAO.md): referências, hipóteses e lacunas.
- [Calendário e medição](CALENDARIO_E_MEDICAO.md): plano de 30 dias e definição de métricas.
- [Vendas e apresentação](VENDAS_E_LANDING.md): demonstração, proposta e acompanhamento.
- [Copy de landing](LANDING.json), [postagens 01–06](posts-01.json),
  [postagens 07–12](posts-07.json), [carrossel](carrossel.json) e [roteiros](REELS.json).
- [Briefings de foto e arte](FOTOS_E_ARTES.json) e [layout editável](template.html).

Os PNGs e JPEGs são modelos para revisão. O JSON é a fonte das legendas; confira o canal,
o dia proposto e a chamada antes de usar cada peça. O carrossel tem quatro slides.
Os roteiros de vídeo ainda precisam ser gravados com dados fictícios.

Na demonstração, use exemplos separados de projetos Scrum e Kanban. A cena de
pull/push do Git próprio deve ser gravada no terminal, sem credenciais visíveis;
não simule uma tela de operação inexistente no aplicativo. Os rótulos `shot` dos
roteiros orientam a gravação, não comprovam uma visita ou um vídeo pronto.

Para o teste A/B proposto, escolha uma única postagem, mantenha sua legenda,
título, oferta e CTA, e prepare duas artes: captura QA e foto conceitual. A indicação
da origem da imagem deve acompanhar cada versão. Distribua as versões no mesmo
período e público; mudanças de público, texto ou oferta impedem atribuir o resultado
apenas à arte. É uma proposta de experimento, sem dados de conversão coletados.

O template usa HTML/CSS local. Para exportar outra versão, um operador deve fornecer
um objeto de postagem a `window.setCreative(post, "images/product.png", "feed")`
ou ao formato `story`, aguardar a imagem e renderizar o elemento `#art` em um
navegador isolado. Os arquivos JSON preservam o conteúdo do modelo; editar o JSON
sozinho não atualiza um PNG já exportado. Use sempre o processo de revisão e
isolamento do LocalAuthor; não execute código de projeto no Windows como fallback.

## O que precisa ser definido para uma campanha real

O público inicial e a direção original são premissas provisórias do supervisor:
pequenas equipes de desenvolvimento no Brasil e estilo próprio do Orbit.
A escolha de adaptar uma referência exige uma resposta explícita do proprietário.

Defina preço, escopo, duração e condições do piloto, responsável pelo atendimento,
contato comercial, domínio da página de apresentação e destino da bio. Implemente
e teste a captação, o consentimento e a medição antes de encaminhar tráfego. UTM
proposta não instala Analytics ou CRM. Nenhuma mensagem foi enviada, conta social
foi conectada ou verba de anúncio foi gasta por este kit.

Para lançar um SaaS de produção, revise os bloqueios descritos na estratégia.
Papéis são globais; o Orbit atual não oferece ACL independente por projeto.
Não ofereça uma instância compartilhada entre clientes como isolamento comprovado.
O Git nativo não possui SSH, LFS, PR ou editor online. A publicação via GitHub usa
a receita CI revisada do próprio Orbit; um push nativo não publica qualquer aplicação.

## Autoria e revisão

LocalAuthor produziu os rascunhos, correções, conteúdo e layout usando o modelo
textual local. Seu componente visual local gerou as fotos conceituais. O supervisor
descobriu URLs, forneceu fatos e contratos, rejeitou erros, operou ferramentas,
selecionou respostas e conferiu os resultados. As capturas de produto vieram do
avaliador de QA, com dados sintéticos; não são fotos de clientes.

A coleta de páginas foi feita pelo ResearchService do LocalAuthor. O modelo
recebeu resumos revisados dessa coleta, não navegou autonomamente toda a internet.
Originais, corpus coletado e diários ficam privados. A proveniência sanitizada e os
hashes estão em [LOCAL_AI_MARKETING_PROVENANCE.json](LOCAL_AI_MARKETING_PROVENANCE.json).
O inventário verificável está em [ASSET_HASHES.json](ASSET_HASHES.json). As fotos
conceituais têm resolução nativa de 512 × 512; a exportação em um canvas maior
não acrescenta detalhes ao arquivo original.

Importar a lição aprovada é consulta, não treinamento de pesos. Este lote não
qualifica um profissional de marketing autônomo nem demonstra retorno comercial.
O estilo que mais vende será uma conclusão de experimentos com dados reais.
