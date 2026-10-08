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
