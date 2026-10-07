# Aprendizado verificável — LocalAuthor

Material para consulta contextual. Ler e recuperar este texto não altera pesos. O sistema só pode declarar aprendizado de parâmetros após treinamento e avaliação documentados.

## Três níveis diferentes

Consulta: recuperar uma fonte com escopo, revisão e citação. Experiência: armazenar um caso e seu resultado para revisão. Treinamento: executar uma receita que modifica parâmetros e produz um novo artefato identificado. Nunca usar essas palavras como sinônimos.

## Construção de um exemplo

Registrar problema, contexto estritamente necessário, saída candidata, verificador, resultado, origem, revisão e direitos. Uma explicação persuasiva ou a confiança do próprio modelo não basta. Para código, exigir evidências de compilação/testes relevantes no ambiente permitido; para texto factual, fontes e revisão adequadas.

Permissões de aceitar a resposta, considerar verificada, autorizar treino e revisar direitos são separadas. Não inventar o nome de um revisor nem definir todos os booleanos como verdadeiros para liberar exportação. Revogar permissão futura não elimina arquivos já exportados: manter rastreabilidade de derivados.

## Divisão dos dados

Separar treino, validação e teste por origem e família de problema quando necessário. Não colocar fragmentos do mesmo incidente/projeto nos dois lados para simular generalização. Hashes detectam duplicatas exatas; variações semânticas e traduções podem exigir revisão adicional. Guardar o holdout fora da recuperação normal do agente.

Manter tarefas inéditas de PT-BR e C#, incluindo casos de erro, segurança, concorrência, integração e clareza de explicação. Não avaliar apenas exemplos em que o professor acertou. As falhas também ensinam onde não se pode automatizar.

## Professor local e candidato

Um professor pode gerar candidatos sob execução totalmente local. Sua saída precisa ser verificada. A origem do professor e os termos dos dados permanecem relevantes. Não prometer transferir todo o conhecimento de um modelo para outro menor.

Em distilação por logits, os índices de vocabulário precisam representar os mesmos eventos ou ter um alinhamento definido. Em adaptação de baixa ordem, o checkpoint-base continua necessário conforme o formato de exportação. Não registrar um adaptador isolado como se fosse um modelo completo compatível com o runtime atual.

## Avaliação e promoção

Usar casos pareados, mesmo runner/ambiente e identidades versionadas. Medir qualidade, segurança, tempo e memória. Relatórios precisam vir de um avaliador confiável: hashes registram identidade, não provam execução. O gate atual não testa significância estatística nem duplicatas semânticas e nunca promove pesos automaticamente.

Aprovação de uma melhoria média não deve encobrir regressão em uma categoria essencial. Examinar português, precisão técnica, segurança de ferramentas e recusa de ações não autorizadas separadamente. Guardar baseline, provar rollback e testar o candidato antes de alterar a seleção de produção.

## Curriculum incremental proposto

Primeiro: seguir requisitos e citar evidências. Depois: diagnosticar bugs pequenos e escrever testes. Em seguida: mudanças multi-arquivo e contratos de integração. Por último: tarefas longas e multimodais. Avançar pelo resultado em tarefas inéditas, não por quantidade de arquivos Markdown lidos.

Referência do projeto: docs/efficiency/ESTUDO.md. Este material não autoriza treinamento automático nem execução de código recebido de documentos.
