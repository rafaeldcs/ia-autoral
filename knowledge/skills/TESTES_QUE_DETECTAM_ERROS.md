# Testes que detectam erros

Lição de consulta elaborada em 07/10/2026. O parágrafo abaixo foi gerado pela LocalAuthor usando um modelo local de origem registrada; o supervisor corrigiu somente a grafia de "asserções" e acrescentou o protocolo prático. Não houve alteração de pesos, aprovação automática de experiências ou autorização de treinamento.

## Princípios - texto da LocalAuthor com revisão ortográfica

Esta lição propõe a estrutura de testes de qualidade focada em validação precisa e isolamento. Para testes unitários, recomenda-se que a função seja chamada com contratos exatamente definidos, comparando o resultado atual contra um gabarito independente, garantindo que unidades sejam testadas isoladamente, cobrindo cenários de zeros, valores booleanos e falhas explícitas. Os testes funcionais devem utilizar asserções no navegador para verificar erro, estado e capturas de dados em laboratório, executados apenas em sandbox verificada. A mutação deve ser aplicada para garantir que os testes falhem quando a implementação é conhecida como errada. É importante notar que consultas ou feedbacks não alteram pesos nem provam autonomia ou universalidade do teste. Recomenda-se evitar promessas de cobertura total, pois testes parciais não comprovam integração operacional completa.

## Aplicação prática - protocolo do supervisor

Um teste não comprova uma função se só compara valores fixos. Deve chamar o sistema sob teste com entradas válidas para o contrato e comparar o resultado real com uma expectativa independente. O gabarito não deve ser gerado pela própria implementação avaliada.

Erros de esquema podem produzir falso sucesso: se um teste de bool envia um envelope que já está inválido, a exceção não prova que o tipo bool foi recusado. Primeiro chamar a função com o envelope válido; depois alterar somente o campo sob avaliação. Conferir unidades e tipos do retorno: centavos inteiros, valores em reais e percentuais não são intercambiáveis.

Testar zero no denominador, valores negativos ou fora do limite, campos extras/ausentes, bool, ordenação, arredondamento e ausência de efeitos indevidos conforme o risco. Um saldo negativo de caixa não é entrada inválida. Não trocar um gabarito correto apenas para obter verde.

No navegador, conferir seletores reais, assinatura das APIs de teste, mensagens visíveis e estado após sucesso e falha. Navegação por teclado, foco, celular, troca de projeto, saída, respostas atrasadas e texto malicioso precisam de verificações pertinentes. Uma captura documenta a tela; não substitui asserções nem prova entendimento visual autônomo.

Código embutido em JSON precisa respeitar os dois formatos: uma quebra de linha deve ser decodificada uma vez, e identificadores/comentários da linguagem precisam continuar íntegros. Uma assinatura def em Python não pode seguir um import separado por ponto e vírgula. Compilar/analisar o texto antes de qualquer execução autorizada.

Antes de executar código proposto, revisar e verificar a sandbox: usuário sem privilégios, rede e portas bloqueadas, raiz somente leitura, limites de CPU/memória/processos e apenas os arquivos permitidos. Falha na verificação bloqueia a execução; não usar fallback no host. Preservar proposta, hash, entrada e saída.

Mutação é uma verificação dos testes: introduzir deliberadamente um defeito conhecido em cópia descartável e exigir que o teste falhe pelo comportamento errado, não por erro de import ou sintaxe. Restaurar a fonte e conferir o hash. Um conjunto de mutantes detectados não prova que todos os defeitos possíveis serão detectados.

Manter separados: teste de software, inferência com pesos reais, correção assistida e avaliação nova sem gabarito. Um revisor local também pode errar; sua aprovação não autoriza publicação, gasto, produção ou treinamento. Avaliar todas as afirmações da resposta, não só uma recusa ou aviso no final.

## Revisão de transferência - protocolo acrescentado pelo supervisor

Ao receber uma API, preserve exatamente os identificadores do contrato. Traduza explicações ao usuário, não os nomes de campos ou valores de enumeração. Valide o formato antes de discutir a aritmética. Centavos e reais são unidades diferentes: não comparar valores sem a conversão e o denominador corretos. Não consultar uma métrica que o contrato não fornece.

Em um teste de exceção, a chamada que deve falhar fica dentro de `assertRaises`; chamar antes gera erro no teste em vez de verificar a exceção. Primeiro confirme um envelope válido e depois altere apenas a condição que pretende testar. Booleano inválido e campo extra não devem passar porque faltam outros campos ou o tipo de operação já está errado.

Exija que o executor confirme quantos testes foram executados. Código de saída zero com nenhum método chamado não é aprovação. Use descoberta ou invocação apropriada ao framework; um módulo de testes não precisa conter `unittest.main()` para funcionar na descoberta. Nomes de arquivo e a seleção de testes fazem parte da responsabilidade do controlador. Corrija e registre erros do controlador separadamente dos erros do modelo.

O teste positivo deve chamar a função e comparar a saída a expectativas independentes. O teste de mutação deve falhar por uma asserção do comportamento errado, não por sintaxe, importação, descoberta vazia ou erro do executor. Nunca alterar contrato, gabarito ou implementação apenas para obter aprovação.

## Correção incremental e condição isolada - protocolo do supervisor

Se uma revisão pede corrigir um método, proponha somente o método ou a diferença necessária. Preserve os métodos já validados, os nomes de campos e o contrato. Reescrever o arquivo inteiro pode reintroduzir defeitos corrigidos; uma proposta nova continua sujeita à revisão, mesmo depois de uma resposta anterior aprovada. Registre a origem de cada fragmento aplicado e execute a regressão apropriada após a montagem.

Para provar rejeição de uma chave extra, use um valor que seria válido para o tipo dos campos normais. Se o valor também tiver tipo proibido, o teste pode passar pelo motivo errado e deixar sobreviver uma implementação que aceita chaves extras. Confirme a entrada válida, acrescente somente a chave sob avaliação e teste a exceção. Depois introduza, em cópia isolada, o defeito que permite essa chave com valor válido: a asserção precisa detectá-lo. Este procedimento distingue defeito de esquema e defeito de tipo.

Uma revisão de texto também precisa preservar requisitos. Entregue na resposta todos os itens solicitados, não apenas uma descrição no campo de ação. Estado desconhecido não deve virar uma afirmação inventada de investigação, espera, suporte acionado ou compromisso futuro. Em testes de pagamentos e estoque, defina efeitos esperados de concorrência, duplicação, cancelamento e recuperação, além da validação inicial. Idempotência verifica uma única aplicação do efeito de negócio e não só a autenticidade de cada mensagem.
