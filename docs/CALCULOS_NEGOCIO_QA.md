# Cálculos e QA da LocalAuthor - uso no servidor local

Atualização de 07/10/2026. Este guia descreve ferramentas implementadas e a revisão de testes escritos pela IA local. Não é uma certificação de programação autônoma, gestão empresarial completa ou ausência de erros futuros.

## Abrir e calcular

1. Inicie o servidor LocalAuthor pelo aplicativo instalado e abra **Modelos locais** em `/foundation` no endereço do seu servidor. Use o acesso autenticado disponível nessa instalação; não compartilhe nem coloque o token na URL.
2. Selecione o projeto. Abra **Calcular leads, ativação e caixa** e escolha Campanha, Ativação ou Caixa.
3. Preencha todos os campos. Contagens são inteiros não negativos. Valores monetários são em **reais**, com vírgula ou ponto decimal, até duas casas e sem separador de milhar. Por exemplo, `200,00` significa R$ 200,00, convertido pelo servidor para 20.000 centavos.
4. Clique em **Calcular**. Entradas inválidas mostram um erro. Um denominador zero aparece como **indisponível**. O saldo de caixa pode ser negativo.
5. **Usar estes cálculos no pedido** prepara o texto do pedido. Revise e envie se desejar interpretação pelo modelo. O botão não envia automaticamente, publica ou gasta.

A ferramenta de cálculo funciona sem carregar pesos. A interpretação depende de um modelo textual registrado e homologado no servidor. O perfil experimental usado na avaliação é privado e separado da configuração do servidor central; não confundir uma avaliação local com uma atualização automática do modelo em todas as instalações.

## O que cada resultado significa

| Tipo | Resultado | Limite de interpretação |
| --- | --- | --- |
| Campanha | CTR, custo por lead, custo de mídia por cliente | Mídia por cliente não inclui todos os custos de aquisição e não é ROI. |
| Ativação | Taxas entre etapas, sobre cadastros e perdas absolutas | Confirmar mesma coorte e período; perdas totais e intermediárias se sobrepõem. |
| Caixa | Saldo inicial + entradas - saídas | Saldo não comprova lucro ou prejuízo contábil. |

Este esquema de campanha supõe `novos clientes <= leads <= cliques <= impressões`. Não representa todos os modelos de atribuição: uma conversão por visualização ou uma campanha com fontes combinadas precisa de outro esquema revisado. Não alterar números para forçar essa ordem. O funil supõe `concluíram <= iniciaram <= cadastraram`.

Os dados informados não são conferidos nas plataformas. A ferramenta não verifica vendas reais, direitos de mídia, consentimento, causalidade, significância, autorizações de gasto ou disponibilidade de funções do produto.

## Contrato de integração

Rota autenticada: `POST /api/foundation/business-metrics`. Corpo exato: `project_id` (string não vazia até 128 caracteres) e `payload` com `kind` e `data`. Projeto inexistente retorna 404; esquema, tipo, ordem ou limites inválidos retornam 400; ausência de autenticação retorna 401.

`kind`: `campaign`, `funnel` ou `cash`. Campos de campanha: `impressions`, `clicks`, `leads`, `new_clients`, `spend_cents`. Funil: `registrations`, `started`, `completed`. Caixa: `opening_cents`, `incoming_cents`, `outgoing_cents`. Todos são inteiros de 0 a 10¹², incluindo dinheiro em **centavos**. Booleanos não são contagens.

A resposta contém `metrics`, `inputs`, `notice`, `data_origin="user_supplied_unverified"`, `published=false` e `weights_trained=false`. Percentuais e reais são strings com duas casas, com arredondamento half-up; denominadores zero retornam `null`. Não usar floats para representar dinheiro na integração.

## O que a IA local escreveu e o que o supervisor fez

A LocalAuthor propôs as funções de validação/cálculo, componentes da interface e validação do identificador de projeto. Houve propostas rejeitadas, erros de esquema, unidades, sintaxe e estado da interface. Os originais e recibos foram preservados fora do Git.

O supervisor definiu os contratos, pediu correções específicas, revisou cada fragmento, montou os componentes e integrou a rota e a interface autenticada. Também escreveu testes independentes e os controles da sandbox. A autoria é conjunta; não descrever isso como aplicação autônoma de código.

No exercício de QA, a LocalAuthor escreveu quatro métodos de teste e um teste funcional. O primeiro teste de campanha era tautológico: comparava constantes sem chamar a função. Outras propostas usavam campos inexistentes, esquema errado ou sintaxe inválida. Foram rejeitadas antes de executar. Após feedback e montagem supervisionada, os quatro métodos chamam a função real e o teste funcional verifica a API e a interface no navegador.

## Evidência de software e limites

- Suíte local Linux: **537/537 testes**, sem falhas, erros ou pulos.
- Oráculos de aritmética: **13.842 combinações** de campanha, funil e caixa, além de esquema, tipos, arredondamento, limites e entradas inválidas. Isso não esgota o domínio inteiro de entradas.
- Navegador: **14 fluxos de integração**; o exercício funcional adicional escrito pela LocalAuthor completou o 15º fluxo.
- Exercício da LocalAuthor: **4/4 testes unitários** e detecção de **4/4 mutantes** (aceitar bool, tratar zero como taxa, errar unidade monetária e somar saída no caixa).

Um segundo exercício supervisionado completou **6/6 métodos unitários e 6/6 mutantes detectados**. Os gabaritos monetários foram explicados pelo professor; isso não é uma avaliação cega. O supervisor montou cinco métodos de uma proposta válida com um método corrigido pela LocalAuthor. A regeneração integral posterior foi rejeitada por reintroduzir um campo inexistente e um teste negativo ambíguo. O teste de campo extra agora confirma uma entrada válida e adiciona somente uma chave com inteiro válido; sua versão anterior passava pelo tipo errado, sem detectar o defeito de esquema.

A primeira instrução desse exercício também tinha ambiguidade de contrato: essa tentativa não é uma prova justa de transferência independente. Após explicitar o contrato, a proposta ainda apresentou erros reais de unidades e exceções, corrigidos com feedback. Erros do executor, como descoberta vazia, foram registrados separadamente e não contados como aprovação nem atribuídos ao modelo.

Os mutantes foram introduzidos exclusivamente na cópia descartável da sandbox, e a fonte foi restaurada antes do teste de navegador. A captura de tela desse exercício foi feita pelo script escrito pela IA local, executado e supervisionado pelo controlador de QA. Não é prova de investigação visual autônoma.

Os testes de navegador usam a API real de aritmética e dublês explícitos para geração textual/visual. Não comprovam qualidade dos pesos. A avaliação das respostas dos modelos reais é separada, preserva primeira tentativa e distingue correções assistidas de casos novos. Uma resposta em JSON correto ou uma palavra de recusa não basta: revisar todas as afirmações.

## Manter o aprendizado compartilhado

A lição `CALCULOS_NEGOCIO_E_REVISAO.md` foi importada para consulta nos projetos de ShopAir, Orbit e aprendizado do servidor, com backup conferido. Os clientes da rede consultam o servidor central; importar lição não altera os pesos, não aprova exemplos privados e não autoriza treinamento.

Atualizações de código dependem da versão que o servidor executa e do processo de distribuição descrito em `docs/PUBLICACAO_MAIN.md`. Um push no GitHub não equivale a publicar o instalador nem a atualizar pesos automaticamente. Só promover um novo perfil após avaliação apropriada ao uso. Rejeições e pendências permanecem registradas.

Não habilitar publicação, cobrança ou alterações de produção para contornar falhas do modelo. Preparar planos e rascunhos legítimos é permitido; executar requer os controles e autorizações correspondentes.

## Diagnósticos do motor local

A LocalAuthor escreveu um filtro de diagnósticos; o supervisor integrou e testou o ciclo de vida. Todas as linhas de inicialização continuam preservadas até a verificação dos pesos na GPU. Depois, somente debug repetitivo e a mensagem informativa de slots ociosos são filtrados; avisos, erros, informações úteis e formatos desconhecidos permanecem. Redação de chave privada, cota de 64 MB, limite por linha de 1 MB, exigência de offload completo e encerramento ao exceder limites permanecem. O encerramento repetido também foi testado. Reduzir diretamente a verbosidade removia evidência de GPU e foi rejeitado. O filtro passou na suíte e comprovou carregamento de 33/33 camadas em inferência real; qualidade das respostas continua sendo outra avaliação.
