# Lições da simulação administrativa do MeuTerreiro

Atualização posterior: o modelo geral continua reprovado para programação autônoma, mas foi treinado e ativado um especialista generativo restrito a blocos Caddy e condições C# de nulidade. Ele gerou os três alvos do projeto e passou em compilação/testes reais. Veja [qualificação de correções](QUALIFICACAO_CORRECOES.md); não confundir esse resultado com qualificação geral nem com o classificador de etapas descrito abaixo.

Escopo autorizado: centro fictício com cinco médiuns, sete perfis de acesso, mensalidade de R$ 100, banco isolado e nenhum pagamento real. A tradição religiosa não altera as regras técnicas de saldo, autorização ou auditoria; não inferir práticas religiosas dos dados administrativos.

## Como investigar antes de afirmar que funciona

1. Leia as instruções do projeto, a stack e as lacunas conhecidas. Preserve Next/.NET/MongoDB e o replica set necessário às transações.
2. Confirme a sandbox. Docker instalado não significa daemon pronto. Verifique o servidor Docker e os containers efetivamente usados. Não execute código desconhecido no host como alternativa.
3. Compile API e interface. Corrija a causa; não desabilite tratamento de warnings ou testes.
4. Valide o proxy, `/health` e autenticação antes de começar os fluxos de negócio.
5. Teste permissões no servidor com todos os cargos, incluindo URLs/IDs diretos, não apenas visibilidade dos botões.
6. Use centavos inteiros e compare obrigações, recebimentos, alocações, razão e saldos. Pagamento parcial, atraso, isenção e crédito excedente são estados distintos.
7. Reproduza estoque, compras, patrimônio, secretaria, limpeza, comunicação e documentos. Uma reserva não é consumo; leitura não é presença; upload não é pagamento.
8. Abra as telas reais em desktop e celular, com dados e sessões reais de laboratório. Capture evidências no navegador do executor local.
9. Diferencie código escrito, compilação, execução, evidência e limite não testado. Uma suíte verde não cobre funções que não existem.

## Erros observados e correções

- A API recusava compilação por `CS8604` ao gerar hash de um endpoint de push que podia ser nulo. A validação foi alterada para exigir explicitamente um endpoint não nulo e válido antes do hash. O warning não foi silenciado.
- O Caddy recusava o bloco com instrução logo após `{` na mesma linha. A configuração foi corrigida com instruções em linhas próprias, então o proxy e a integração HTTP foram realmente executados.
- Um teste Node precisava criar arquivos em `/tmp`; a primeira sandbox tinha raiz somente leitura e nenhuma área temporária. Foi adicionado tmpfs limitado, preservando a raiz somente leitura e sem liberar o host.
- A imagem de laboratório tinha entrypoint próprio. Para executar verificações Node/Python, foi necessário selecionar explicitamente o interpretador, sem atribuir essa falha de infraestrutura ao aplicativo.
- Contratos de API devem ser lidos antes de escrever o teste. Exemplos: `fromId`/`toId` para transferência; `approvalId` pertence à aprovação de isenção, não ao cadastro da isenção; razão usa `signedCents`; catálogo público de itens não concede acesso a quantidades de lotes.
- Os roteiros iniciais omitiram `quantityMilli` ao receber uma doação e `location` ao devolver um bem. Eram erros do teste, não defeitos de negócio. As execuções que falharam foram preservadas e o cenário refeito em bancos separados.
- Um teste de negação usava `/download`, mas o endpoint real era `/file`. Um 404 em URL inexistente não prova autorização. O teste foi corrigido e ganhou controle positivo: mesmo arquivo, mesma rota, secretaria recebe 200 e médium recebe 404. O endpoint de recibo utiliza 403 para acesso de outra pessoa; conferir o contrato antes de esperar 404.

## Execução e evidências desta rodada

- O especialista carregou seus pesos e recebeu observações derivadas do relatório HTTP que falhou: propôs `INVESTIGATE_FAILURE`, sem consultar o gabarito durante a inferência.
- `run-terreiro-browser.cjs` é um executor explícito de QA, com Playwright/Chromium dentro da imagem `localauthor-functional-lab:1`. Permite somente `http://localhost:3180`, usa raiz somente leitura e temporários limitados. Não registra senhas, não captura a tela de login e não envia dados para uma API de IA.
- O executor percorreu 154 combinações de perfil/rota em sete perfis, em desktop e celular: 505 checks e 308 capturas. `run-terreiro-interactions.cjs` acrescentou seis checks e cinco capturas de criação/conclusão de tarefa, consulta de pagamento/isenção e acesso negado.
- API e banco reais foram usados para os cinco médiuns: R$500 nominais, R$250 pagos, R$100 isentos e R$150 em aberto. Saldo livre excedente e saldo bancário são conceitos distintos.
- A execução inclui análise real de imagem pelo processador e ClamAV. Liberação do arquivo não confirma pagamento nem autentica um comprovante bancário.
- A suíte do LocalAuthor passou 220 testes em Linux, sem pulos. O treino usa NumPy já existente e o autograd original. O novo especialista é separado; não foi conectado automaticamente ao modo de conversa nem distribuído a outros servidores.
- `terreiro-gallery.py` cria a galeria local. Capturas demonstram estados observados; este especialista não interpreta visualmente essas imagens.

Dependências de infraestrutura: Docker Desktop/Compose, imagem de laboratório com Node, Python/NumPy e Playwright/Chromium; MeuTerreiro com .NET 10, Next, MongoDB replica set, Caddy e processador/ClamAV. Checkpoints e dados de simulação ficam fora do Git. Memória de consulta importada não é treinamento de pesos.

## O que a IA local aprendeu nesta rodada

Um especialista neural original e separado, `TerreiroQaPolicy`, foi treinado com observações booleanas sintéticas para selecionar a próxima etapa de QA. Estados fora do escopo pedem parada; falhas observadas pedem investigação; etapas faltantes não podem ser substituídas por um relatório de sucesso.

Os conjuntos de treino, validação e teste têm observações distintas. O checkpoint é escolhido pela validação, sem seleção pelo teste. O teste reservado teve 256 casos: 17 acertos antes e 256 depois. São variações dentro de famílias conhecidas, não prova de raciocínio geral ou transferência para qualquer sistema.

O modelo propôs a sequência: autenticação, permissões, mensalidades, tesouraria, estoque, administração, comunicação, documentos, navegador e evidências. O executor deve associar essa proposta a recibos reais de execução; uma lista de etapas não é um teste executado.

**Autoria:** investigação, normalização das observações, catálogo de ações, testes de negócio e correções foram escritos por Codex. O especialista local aprendeu a escolher classes de ações. Ele não escreveu sozinho o código dos testes nem compreendeu pixels do navegador. O Transformer de conversação anterior não foi substituído. Pesos, corpus sintético e relatórios ficam no servidor, fora do Git.

## Critério para uma próxima avaliação

Preferência reforçada pelo usuário: mudanças no código do saravaAPP/MeuTerreiro devem ser propostas pela IA local; Codex ensina, investiga e revisa. Não escrever a solução em seu lugar e depois atribuí-la ao modelo.

Na avaliação real de autoria, o modelo conversacional `engineering-20260917T173320Z/best-validation.npz` recebeu dois problemas curtos sem a solução: sintaxe de bloco Caddy e validação C# de string anulável. Ambas as respostas foram sintaticamente inválidas, reprovadas e não aplicadas. Ele **ainda não está qualificado para corrigir esse sistema**. As correções anteriores de compilação/proxy foram feitas por Codex antes dessa preferência ser reforçada; isso está registrado no projeto.

Diagnóstico do limite: o modo neural atual aceita apenas 180 bytes, não recebe os arquivos nem utiliza o histórico/consulta de notas. Importar esta lição não resolve essa limitação nem muda os pesos conversacionais. O especialista que passou a avaliação de sequência de QA é outro modelo, com outra tarefa. A próxima avaliação de autoria precisa medir código original compilável, comportamento correto e regressões, não apenas seleção de etapas ou recuperação de notas.

Apresente combinações novas de falhas e etapas incompletas, sem incluir o gabarito na entrada do modelo. Guarde propostas erradas e recibos de falha. Se um teste do produto falhar, a próxima proposta deve ser investigar, não publicar sucesso. Depois de uma correção, repita o caso e suas regressões em banco descartável. Nunca treine usando senhas, dados reais de membros ou o teste reservado para depois chamá-lo de avaliação inédita.
