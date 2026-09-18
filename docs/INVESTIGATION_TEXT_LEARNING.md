# Leitura experimental de textos de interface

Em 18/09/2026, a próxima etapa autoral passou a aprender diretamente com frases
de interface, em vez de receber apenas indicadores booleanos já interpretados.
São **dois classificadores próprios 2048 → 32 → classes**, com GELU e pesos
treinados do zero. A codificação fixa usa palavras, pares de palavras e trechos
de caracteres com hash. Não há embeddings externos, pesos pré-treinados, API de
IA ou dependência nova. São 131.433 parâmetros no total, separados do Transformer
de linguagem e do especialista de decisões anterior.

O classificador de estados distingue disponível, carregando, erro, acesso negado
e texto sem estado identificável. O classificador de controles distingue
navegação, alteração, autenticação e rótulo ambíguo. A saída vem dos pesos; nenhum
gabarito ou regra substitui uma previsão errada. O gabarito existe apenas no curso
e na avaliação, escritos pelo Codex. Os textos são fictícios, autorizados pelo
pedido de ensino; nenhuma tela, credencial ou dado privado da ShopAir foi usado.

## Resultado e correções

O curso inicial teve 204 exemplos de treino, 36 de validação e 36 de auditoria.
Passou nos 36 casos, mas uma auditoria adicional de 16 contrastes encontrou quatro
erros: negação de erro, falha ao obter registros, visualizar sem excluir e excluir
histórico de visualizações. O relatório dessa primeira tentativa foi preservado.

As correções acrescentaram demonstrações diferentes dos testes. Uma rodada com
244 exemplos acertou 63/64 na auditoria e 35/36 na validação. Com 260 exemplos,
a auditoria passou, mas a validação ainda confundia “Salvar configurações” com
navegação. O curso final usa **264 exemplos de treino, 36 de validação e 64 de
auditoria**, sem frases idênticas entre partições. Os pesos são escolhidos somente
pelos acertos e perda de validação; os alvos da auditoria não entram no gradiente.

Antes do treino, os pesos aleatórios acertavam 9/64 casos. Após ensinar contrastes
adicionais entre abrir e alterar configurações:

| Verificação | Resultado |
|---|---:|
| Frases de validação, após recarregar os pesos | 36/36 |
| Frases de auditoria, incluindo os erros anteriores | 64/64 |
| Páginas fictícias compostas, com texto acima de 256 bytes | 34/34 |
| Testes de software no Linux, sem casos ignorados | 200/200 |

As 34 páginas são composições offline dos mesmos casos, com cabeçalhos e controles
reordenados. Não são 34 sistemas distintos nem testes executados em navegador.
Como houve inspeção de resultados e correções sucessivas, a avaliação final é
**auditoria de desenvolvimento**, não um teste cego independente. Os 12 exemplos
adicionais também já foram avaliados durante as correções. Nenhum teste foi
removido, reclassificado ou contado como sucesso por ter sido bloqueado.

## Uso e evidências

```powershell
.\.venv\Scripts\python.exe scripts/teach-investigation-text.py --corrective
.\.venv\Scripts\python.exe scripts/teach-investigation-text.py --audit C:\pasta-privada\report.json
.\.venv\Scripts\python.exe scripts/inspect-investigation-text.py --report C:\pasta-privada\report.json --origin https://qa.example.test --observation C:\pasta-privada\observacao.json --output C:\pasta-privada\anotacoes.json
```

O treino salva corpus, permissões, manifesto, hashes, histórico de validação,
previsões antes/depois, pesos e casos congelados em `%LOCALAPPDATA%\LocalAuthor`,
nas pastas `corpus`, `models` e `exports`. Nada disso é incluído no Git. A auditoria
recarrega os pesos, confere hashes de pesos/casos, repete validação e testes e
confere os hashes dos checkpoints anteriores presentes no servidor.

A execução final desta entrega está em
`exports\investigation-text-20260918T141650Z\report.json`, dentro da pasta privada
do LocalAuthor. A inspeção por linha de comando também foi executada: classificou
carregamento, título sem estado, consulta e alteração, sem executar ações.

O comando de inspeção recebe somente a observação sanitizada do protocolo
`BrowserInvestigation`: `url`, `title`, `text`, `controls`. Cada controle tem
`id`, `role`, `name`, `navigation`, `href`. O observador confiável deve excluir
valores de campos, cookies e segredos **antes** de gravar o arquivo. As anotações
também podem conter texto privado, portanto devem ficar no diretório privado.
O script não abre sites, não autentica, não treina e não clica.

## Limites que continuam explícitos

- Cada segmento tem até 600 caracteres. A segmentação preserva integralmente
  texto e posições; páginas acima de 12.000 caracteres são recusadas, sem corte
  silencioso. Isso não é ampliação de contexto do Transformer.
- Não há raciocínio entre segmentos. Uma frase partida, negação distante,
  contradição entre regiões, modal sobreposto ou dependência de tela anterior
  ainda pode produzir interpretação errada.
- A categoria `unknown` foi aprendida com exemplos; não é detector garantido de
  qualquer texto desconhecido. Escores não são probabilidades calibradas.
- A previsão `navigation` nunca altera a autorização `navigation` do observador.
  Um teste força uma previsão errada e confirma que a exclusão continua bloqueada.
- Os módulos anteriores mantêm os mesmos pesos. O Transformer de texto continua
  reprovado no curso livre anterior; estes resultados não apagam essa reprovação.
- O novo especialista está disponível para experimentos por biblioteca e CLI.
  **Não foi ativado automaticamente no chat ou como investigador de sites reais.**

O próximo marco exige relacionar regiões e histórico, selecionar controles por
objetivo e demonstrar recuperação em um sistema novo, com navegador e evidências
de execução. Esse marco permanece pendente. Aprender frases de interface resolve
uma parte mensurável do limite anterior, não a investigação de qualquer sistema.
