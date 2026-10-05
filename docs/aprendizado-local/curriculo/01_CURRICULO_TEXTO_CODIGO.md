# Currículo de desenvolvimento — texto e código

**Uso:** ensino, geração de exemplos e validação interna. Não importar esta pasta no RAG do candidato; não tratar suas perguntas como prova final inédita. Quantidades abaixo são um planejamento de cobertura, não um volume comprovadamente suficiente para treinamento.

## Estrutura de cada lição

A lição deve declarar objetivo, pré-requisitos, contrato, contexto permitido, resposta-alvo, evidência de verificação, família e direitos. Produzir casos positivos, negativos e de fronteira, além de variações linguísticas. A solução não pode depender de um nome fixo de variável que denuncia o gabarito.

Começar com 5–10 exemplos revisados por módulo para detectar problemas do pipeline. Expandir somente quando os novos exemplos acrescentarem diversidade e evidência. Para código, priorizar famílias executáveis verificadas em vez de milhares de respostas plausíveis sem teste.

## Módulos e progressão

| Módulo | Competência-alvo | Exercício didático | Evidência necessária |
|---|---|---|---|
| TXT-01 | Pedido, idioma e formato | Responder em português preservando um identificador inglês | Rubrica de atendimento, sem renomeação indevida |
| TXT-02 | Contexto de conversa | Resolver uma referência a uma decisão anterior | Resposta utiliza a decisão correta, sem inventar histórico |
| TXT-03 | Fontes e incerteza | Responder com duas notas conflitantes | Explicitar divergência e citar trechos reais |
| TXT-04 | JSON e saídas estruturadas | Produzir objeto conforme schema fornecido | Parser e validador externo, sem reparo oculto |
| COD-01 | Leitura de código | Explicar fluxo de um método pequeno | Correspondência linha a linha e ausência de operações inventadas |
| COD-02 | Null e validação | Tratar ausência sem confundir com valor zero | Testes positivos, negativos e de fronteira |
| COD-03 | Async/cancelamento | Propagar cancelamento em fluxo permitido | Execução demonstra cancelamento sem sucesso falso |
| COD-04 | SQL determinístico | Consultar registro mais recente e desempatar | Fixture de banco e resultado esperado |
| COD-05 | Persistência | Corrigir consulta sem alterar contrato | Resultado, transações e número de consultas medidos |
| COD-06 | APIs/autenticação | Investigar falha a partir de logs fictícios | Hipóteses testadas; sem remover proteção |
| COD-07 | Webhooks/filas | Tratar duplicata e repetição controlada | Efeito de negócio ocorre uma vez na fixture |
| COD-08 | Frontend | Preservar pedido após falha e evitar reenvio cego | Teste de interação real no navegador |
| COD-09 | Refatoração mínima | Alterar implementação sem mudar contrato | Regressões e consumidores de laboratório preservados |
| COD-10 | Diagnóstico de ambiente | Diferenciar dependência ausente e falha de código | Bloqueio registrado sem inventar execução |
| AGT-01 | Ferramentas tipadas | Selecionar leitura/busca/proposta conforme estado | Executor nega ação fora de escopo |
| AGT-02 | Loop de correção | Investigar, propor, testar e encerrar com limite | Recibos por etapa e nenhum efeito não autorizado |
| MEM-01 | Reutilização | Aplicar experiência válida e recusar a obsoleta | Fontes/versionamento conferidos |
| OPS-01 | Transparência | Responder após ferramenta ou teste indisponível | Estado correto; nenhuma alegação de sucesso sem evidência |

AGT-01/02 exigem ENG-12 implementado. Até lá, podem existir exemplos de formato e tarefas de planejamento, mas não uma alegação de uso real de ferramentas pelo LocalAuthor.

## Diversidade controlada

Variar nomes, linguagem do pedido, tamanho do contexto, estilo de código, valores-limite e ordem das informações. Preservar a família de origem de cada variante. Uma tradução ou renomeação não transforma um exercício conhecido em holdout.

Para cada módulo, incluir ao menos um caso em que não mudar código é a resposta correta e outro em que falta informação. Não ensinar que toda solicitação exige patch. Evitar treinar obediência a instruções maliciosas dentro de arquivos recuperados.

## Rotina de ensino

Gerar candidato → validar contrato/direitos → executar verificador ou revisão → rejeitar/corrigir o exemplo → registrar alvo aprovado → particionar por família → usar no piloto. Não chamar esse ciclo de treinamento até a execução do trainer.

Ao concluir cada módulo, avaliar um conjunto de validação distinto das amostras usadas no ajuste. Registrar erros por categoria para decidir a próxima lição. Uma melhoria só na redação não deve ser contada como melhoria de correção de código.

## Matriz de saída

O relatório deve marcar para cada módulo: exemplos revisados, famílias, validação, capacidade suportada pelo runtime, avaliação final e limites. As metas globais estão no documento de critérios; o avaliador final cria novos casos em ambiente separado.
