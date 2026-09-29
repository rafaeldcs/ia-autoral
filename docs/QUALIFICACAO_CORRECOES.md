# Qualificação restrita de correções — 29/09/2026

O LocalAuthor agora possui um **especialista generativo qualificado para duas famílias pequenas**: quebrar um bloco `handle` Caddy inválido em linhas próprias e gerar uma condição C# que rejeite valor nulo antes de chamar um validador.

Não é qualificação geral para corrigir autonomamente o saravaAPP, escrever funcionalidades financeiras ou entender código arbitrário. O modelo geral anterior permanece não qualificado. O campo global `model_qualified` continua falso intencionalmente.

## O que mudou de fato

- Um Transformer original, com 103.936 parâmetros, foi treinado do zero no motor NumPy/autograd do projeto. Não foram usados pesos baixados, API de IA ou geração por outro modelo.
- 93 exemplos sintéticos de treino; sete de validação; nove de teste reservado; três alvos do projeto separados. São combinações distintas de famílias conhecidas, não problemas de natureza inédita.
- O BPE foi aprendido somente no treino. A seleção do checkpoint usou a validação. Foram 1.500 passos; o teste reservado e os alvos não foram usados para ajuste dos pesos.
- A inferência gera tokens de código. Não consulta o corpus, não busca a resposta nas notas e não escolhe um template de correção. O professor escreveu exemplos, protocolo, verificadores e testes; os pesos geraram as propostas.
- Um verificador determinístico rejeita alterações de identificadores, destino, operador e sintaxe. Ele **não escreve a resposta**. A saída não é aplicada automaticamente.
- O chat encaminha somente o protocolo documentado ao especialista. A resposta identifica o checkpoint e o escopo. Não houve substituição silenciosa do modelo geral.

## Resultados executados

| Avaliação | Resultado |
|---|---|
| Casos reservados, gerados novamente a partir dos pesos | 9/9 |
| Alvos originais do saravaAPP, fora do treino | 3/3 |
| Configurações verificadas pelo Caddy real | 9/9 |
| Condições compiladas em .NET 10, warnings como erros | 3/3 |
| Comportamento C#: nulo, vazio, inválido e válido | 12/12 |
| Controles negativos: código original defeituoso | 10/10 defeitos detectados |
| Código original do saravaAPP + somente saídas neurais | Caddy válido, API publicada, 138/138 testes C# |
| Regressão do LocalAuthor | 225/225, sem pulos, em Linux |
| Navegador → chat → pesos, desktop/celular | 6/6 checks |
| Servidor Windows em uso | Duas gerações corretas; pedido fora do escopo recusado |

Os grupos acima se sobrepõem; não devem ser somados como requisitos independentes. Os 138 testes são os testes existentes da API, não uma prova de cobertura total. O especialista resolveu os alvos em cópia isolada do commit `35586e8`; o código atual já tinha as correções anteriores de Codex. Não houve necessidade de inventar uma nova alteração no aplicativo para demonstrar autoria.

Checksum do checkpoint: `6008cee62a16b8490d6b7e57b31bafcd6279ccd8650deb605d779a700833e1a5`.

## Usar no aplicativo

1. Atualize a página do LocalAuthor e escolha o projeto MeuTerreiro.
2. Abra **Exercitar correção de código** abaixo das mensagens.
3. Escolha **Testar configuração do servidor** ou **Testar validação C#**. O botão preenche o problema, não a solução.
4. Clique em **Enviar**. A resposta aparece como código, identificada como correção avaliada em escopo limitado.
5. Revise o diff, execute o compilador e testes de regressão antes de aplicar qualquer proposta ao projeto.

O protocolo Caddy admite `handle`, os matchers vazios/`@api`/`@web`/`@files`, serviços `api`/`app`/`files`/`worker` e portas 3000/5000/8080/8090. O protocolo C# admite os objetos `input`/`request`/`data`/`item`, propriedades `Endpoint`/`Url`/`Address`/`Name` e os validadores `Rules.ValidPushEndpoint`/`Rules.ValidText`/`Rules.IsAllowed`. Fora dessa distribuição, não há certificado de capacidade.

Em outro computador conectado ao **mesmo servidor**, a inferência usa esses mesmos pesos centrais. Não é necessário treinar cada cliente. Um servidor diferente precisa receber o checkpoint e seu certificado por procedimento privado; `git pull` não transporta os pesos. Nenhum instalador foi modificado nesta rodada.

## Arquivos e reprodução

- `qa/code_repair_course.py`: fábrica original de exemplos; o corpus concretizado fica fora do Git.
- `scripts/train-code-repair.py`: treino com perda somente na resposta. Use pasta de saída nova; `--resume` também deve apontar saída nova, preservando o experimento anterior.
- `scripts/qualify-code-repair.py`: recarrega os pesos, reproduz cada proposta, confere hashes, compila/executa e testa controles negativos.
- `scripts/verify-project-repair.py`: substituição mecânica exclusivamente com saídas neurais no código original, em container descartável.
- `scripts/code-repair-chat-smoke.py`: servidor/usuário temporários e navegador real, sem token real nos logs/capturas.
- `src/localauthor/code_repair.py`: acesso ao especialista, escopo e verificações antes de entregar a proposta.

Infraestrutura declarada: imagem `localauthor-code-repair-lab:1`, derivada do laboratório existente e do binário Caddy da imagem oficial, com Python, NumPy, .NET 10 e Playwright. Treino e qualificação foram executados sem rede. A verificação do projeto usou rede somente para restaurar dependências NuGet no container. Raiz somente leitura, temporários limitados, sem capabilities e sem socket Docker montado.

Pesos, corpus congelado e recibos ficam em `%LOCALAPPDATA%\LocalAuthor\models\code-repair-20260929`. O certificado ativo fica em `%LOCALAPPDATA%\LocalAuthor\exports\code-repair-qualification.json`. Hash divergente, certificado ausente ou gate reprovado impedem uso. A ativação foi feita após testes e revisão; treino isolado não ativa o especialista.

## Lições de investigação

Na primeira execução, Caddy não iniciou porque seu binário carregava uma capability de porta privilegiada incompatível com a sandbox sem capabilities. A imagem de laboratório passou a copiar o binário sem esse atributo; os privilégios não foram ampliados.

O segundo impedimento era o apphost .NET tentando executar em temporário sem permissão de execução. O avaliador passou a compilar e executar a DLL pelo runtime `dotnet`, preservando a montagem. Eram falhas do executor, não erros das propostas. Os recibos de falha foram preservados e os testes repetidos.

Para ampliar a qualificação, crie novas famílias com contratos e testes de comportamento, congele avaliações antes do treino e exija propostas originais. Não use estes 12 casos novamente como uma avaliação inédita, nem troque sucesso em duas famílias por uma alegação de programação geral.
