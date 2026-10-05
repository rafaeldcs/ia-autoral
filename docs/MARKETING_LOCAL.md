# Marketing local com pesquisa, referência e distribuição

Abra `/marketing` no LocalAuthor ou o link **Marketing** na página de conversas. No aplicativo Windows pareado, o formulário de entrada usa o mesmo mecanismo de autenticação do cliente. O gateway LAN precisa da compilação atual, que permite as três rotas estáticas de marketing; atualizar somente o Python não atualiza esse executável. A inferência permanece local; a coleta de páginas públicas e os conectores de redes sociais precisam de internet. Não há API externa de IA.

## Como usar

1. Selecione o projeto e informe marca, público específico, objetivo, página de destino e canais. O padrão ShopAir é um exemplo editável, não uma oferta já aprovada.
2. Informe fontes do produto, uma referência existente e documentação de medição. Opcionalmente peça à IA um plano, confira os papéis e confirme a coleta. O plano é uma proposta, não prova de leitura. Use “Outras fontes relevantes” para acrescentar dados do público, concorrentes ou documentação do canal.
3. Confira o que foi coletado e o que foi bloqueado. A configuração `offline=false` e os nomes DNS exatos em `allowed_domains` são necessários. O coletor respeita HTTPS público, DNS, limites, redirecionamentos e robots.txt. Não há busca geral da internet nesta versão: a IA prioriza URLs explicitamente disponibilizadas; não descobre ou conhece todos os sites.
4. Escolha **original** ou **adaptar referência**. Sem esta resposta, gerar fica bloqueado. Adaptação exige uma referência realmente coletada no mesmo projeto. Uma documentação de Analytics é fonte de medição, não modelo de campanha. Estruturas genéricas não comprovam comportamento de um público.
5. Gere as propostas. Cada canal recebe uma peça curta com descrição de criativo proposto, fatos literais com linhas e link UTM. A IA seleciona fatos numerados; o controlador resolve a citação exata, sem reescrever a legenda. Outra chamada ao mesmo modelo critica fatos, linguagem e adequação ao canal. Essa crítica é feedback, não avaliação independente nem aprovação comercial. A descrição não é imagem ou vídeo produzido. As tentativas rejeitadas são preservadas; há até três tentativas por canal, sem repetição infinita. Um contrato editorial contraditório recebe uma tentativa adicional com feedback; a ferramenta não corrige o campo de aprovação por conta própria.
6. Revise o conteúdo completo: fonte atual, coerência factual, clareza, linguagem, proposta de valor, público, chamada para ação, direitos de imagens e funcionamento do destino. Verificações mecânicas não certificam a relação semântica entre fato e legenda. A aprovação vale para aquela versão; pesquisar novamente invalida a escolha e a aprovação. Fonte modificada, removida ou vencida bloqueia preparação/envio.
7. Prepare o pacote JSON visível na tela e copie-o para distribuição manual (o download de arquivo fica disponível no navegador) ou prepare uma peça para um conector. Publicar exige outra confirmação com conta, texto, destino e mídia exatos. Não há publicação automática por uma resposta da IA.

O histórico fica em tabelas separadas no banco existente, com revisões imutáveis, hash e controle de concorrência. Limites:100 campanhas por projeto,160KB por revisão,64MB para o histórico de marketing. Fontes/experiências mantêm as próprias quotas. Não apaga originais para liberar espaço silenciosamente, não transforma uma aprovação de campanha em autorização de treinamento.

## Conectores Meta

Esta versão implementa **Facebook Page orgânico (texto e link)** e **Instagram profissional via Facebook Login (JPEG público)**. Ela não implementa anúncios pagos, Reels, carrossel, Stories, mensagens privadas, edição de comentários, coleta de leads ou insights. YouTube, LinkedIn, site, WhatsApp e email recebem propostas/exportação manual; não estão conectados automaticamente.

Crie/configure um aplicativo Meta adequado ao canal e à organização. Use o painel oficial para selecionar uma versão Graph API vigente, autorizar a Page/conta profissional e obter o token com as permissões pertinentes. Não cole senhas ou tokens no chat. A tela avançada de conexão recebe o token por requisição autenticada, limpa o campo e salva apenas ciphertext DPAPI do usuário Windows do servidor. Não há tokens nos jobs, recibos ou respostas. O mesmo usuário Windows precisa executar o servidor para abrir a credencial. Não há fallback em texto em Linux.

Facebook confirma ID e `can_post`; Instagram confirma ID e `username`. Isso não garante que a Meta aprovou o aplicativo ou todas as permissões. A resposta de uma publicação específica confirma somente seu ID, não alcance, vendas ou retorno. Não foi realizado envio real às contas da empresa sem conexão/autorização pertinente.

Instagram precisa de um JPEG real acessível pela Meta em HTTPS, não uma imagem local ou uma descrição. A URL da imagem entra na prévia e no hash aprovado. PNG local do laboratório não é JPEG público pronto para este conector. URLs na legenda do feed não substituem o link da bio; a equipe precisa conferir esse destino. O criativo deve ser revisado fora desta tela antes da confirmação.

Há no máximo uma solicitação de entrega por peça/campanha, inclusive se a conta ou a versão da API mudar. Para distribuir uma campanha nova, crie outra campanha; não clone uma entrega incerta sem conferir a conta. Se a requisição cair depois de a plataforma receber o post, o recibo fica `unknown`: confira na conta. Esta versão não oferece reconciliação automática nem botão de repetir uma entrega incerta. Se o processo cair com estado `sending`, trate igualmente como incerto.

## Medição e aprendizado

UTM separa canal, campanha e peça, preserva parâmetros comerciais e não deve levar dados pessoais. Para medir demonstrações/leads: configure o evento apropriado no site, consentimento/privacidade, atribuição e deduplicação, teste o formulário e confronte Analytics/CRM. A IA não marca isso como instalado só porque acrescentou uma URL. Os cálculos existentes de CTR, conversão por clique, CPC e CPA usam dados fornecidos não verificados; valores ausentes/denominador zero não são resultados reais.

Para uma avaliação de marketing aceitável, congele antes da geração: público, objetivo, fontes, oferta, formatos e rubrica. Avalie factualidade, mensagem, adequação ao canal, originalidade, clareza/acessibilidade e medição. Preserve saídas completas e casos negativos (fonte contraditória, referência não escolhida, oferta desconhecida, injeção na fonte, token vencido, conta errada, entrega incerta e fonte revogada). Meça resultados comerciais somente após conexão, campanha aprovada e coleta real. Não declare “melhor possível” a partir de testes conhecidos.

O perfil de marketing foi ampliado com essas distinções. A revisão pela IA é separada em fatos/resultados, canal e criativo; cada etapa preserva sua resposta e só a aprovação das três permite seguir à revisão humana. Isso muda instruções/contexto e processo de trabalho; não significa que os pesos aprenderam permanentemente. Treinar exige curadoria e autorização completas, separadas da consulta e da aprovação de uma campanha.

O gerador atual usa uma checagem conservadora adicional de palavras de promessa, eficiência/simplicidade e propostas de interface sem captura real fornecida. Ela pode recusar uma expressão mesmo em uma negação; prefira descrever diretamente os elementos de uma ilustração simbólica. Essa regra não valida imagem real nem substitui a conferência semântica humana.

## Fontes oficiais consultadas em 05/10/2026

- Produto anunciado: [ShopAir](https://shopair.com.br/). Uma vitrine demonstrativa não é resultado de cliente. Informações comerciais precisam de reconferência/aprovação para cada oferta.
- Referência a comparar, sem copiar: [roteiro de campanhas da HubSpot](https://blog.hubspot.com/marketing/marketing-campaigns).
- [Meta — Posts de Page](https://developers.facebook.com/docs/pages-api/posts/), [SDK oficial Page](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/page.py), [SDK oficial IGUser](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/iguser.py), [coleção oficial de Instagram da Meta](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).
- [Google Analytics — parâmetros de campanha](https://developers.google.com/analytics/devguides/collection/ga4/reference/config).

Leia os requisitos vigentes de aplicativo/conta/permissões na sua organização antes de conectar; não adivinhe uma versão ou misture Instagram Login com Facebook Login. O adaptador atual usa `graph.facebook.com`, com operações limitadas a identidade, `feed`, `media` e `media_publish`.
