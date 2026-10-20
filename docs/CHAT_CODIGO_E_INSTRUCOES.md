# Código no chat e revisão de instruções

O chat separa o texto dos blocos cercados por crases ou tils. Cada bloco tem linguagem, botão **Copiar código** e rolagem horizontal própria. O conteúdo é inserido como texto: HTML, comentários, Unicode, tabulações e quebras de linha não são executados nem reescritos. **Copiar mensagem** preserva a resposta original, incluindo as cercas. Um bloco sem fechamento recebe aviso visível.

Quando o modelo omite todas as cercas, o detector conservador de formato já existente classifica a resposta inteira. Se detectar código, o chat usa um bloco genérico copiável, preservando integralmente o texto. Essa apresentação alternativa não inventa uma linguagem nem aprova o código sem cercas na revisão de instruções.

Pedidos de programação recebem orientação para conferir requisitos, proibições, tipos, imports e correções do usuário. Essa orientação não ocupa o orçamento das conversas sociais e de marketing. Fontes recuperadas continuam sendo dados não confiáveis, separados das regras do sistema; o pedido atual não é cortado para caber no contexto.

Após gerar código com o modelo local, a plataforma verifica alguns critérios explícitos do pedido atual: um limite não ambíguo de linhas, proibições de `useEffect`, imports relativos e algumas classes Tailwind, além de identity do PostgreSQL quando pedida. São verificações lexicais limitadas; não são um compilador nem uma avaliação semântica completa. Comentários também contam para essas verificações e as regras não reconhecem toda formulação possível.

Quando encontra uma violação e a resposta não está truncada, solicita **uma única nova geração ao mesmo modelo local**, com o pedido e o diagnóstico. Não edita o código para aparentar conformidade. As duas respostas e seus diagnósticos ficam na experiência privada. A segunda geração consome tempo adicional. Se não houver orçamento para o retorno, mantém a resposta e a falha; se a revisão continuar falhando, o chat mostra o critério pendente. Retirar todo o código na revisão não elimina a falha anterior.

Os testes de software verificam apresentação segura, cópia exata, largura em telas pequenas, entrega das instruções ao contexto e repetição limitada com dublês identificados. A qualidade do modelo deve ser conferida separadamente em conversas reais, preservando também as tentativas malsucedidas. Nenhum desses controles garante obediência universal, compila o código gerado ou altera os pesos do modelo. Memória, orientação de contexto, revisão automática e treinamento são processos diferentes.

Não há nova dependência, serviço externo ou permissão de execução. Os modelos e as experiências continuam no servidor local.

Para compilar e testar exemplos registrados com autorização explícita do operador, há um [laboratório separado com Docker offline](CHAT_CODIGO_TESTES_REAIS.md). O fluxo de apresentação/revisão acima continua sem executar código gerado.
