# Protocolo do avaliador separado

**Este arquivo descreve como preparar a avaliação. Não contém uma prova secreta pronta.** As tarefas dos currículos e exemplos deste pacote já são conhecidas pelo executor e não podem servir como gabarito de generalização independente.

## Separação de papéis e acesso

O desenvolvedor do trainer pode ler este protocolo, mas não deve receber os casos finais e gabaritos. O avaliador deve criá-los em uma área privada excluída de RAG, corpus, históricos enviados ao candidato e permissões do processo de treino. Apenas uma pasta chamada “reservado” não implementa essa separação: aplicar controle de acesso e segregação de processos/ambientes.

O modelo recebe o enunciado e o contexto permitido para responder. O verificador tem os resultados esperados ou testes protegidos. O executor não pode editar esses testes durante a tentativa.

Se um único agente lê todos os enunciados/gabaritos e depois cria os dados de treinamento, registrar que a avaliação não é independente. Não prometer independência por instruir o mesmo agente a “esquecer”.

## Manifesto da prova

Definir antes de executar: escopo, famílias, casos, oráculos, rubrica, versões, ferramentas permitidas, política de tempo/tokens/tentativas, sementes visuais quando suportadas e limiares de aceite. Hashear o manifesto e os casos. Não publicar os gabaritos no repositório de desenvolvimento.

Criar casos novos de composição e borda: valores/contratos variados, código diferente, fontes contraditórias, ferramenta indisponível, fonte ausente, solicitação fora da capacidade e falha de rede. Uma mera paráfrase de uma amostra didática não é um novo grupo.

## Avaliações mínimas

1. Contratos críticos: permissões, isolamento, dados privados, treinamento sem direitos, relato de execução e conteúdo não confiável.
2. Conversa/contexto: seguir idioma e formato, usar histórico pertinente, localizar a fonte correta e reconhecer insuficiência.
3. Código: requisito verificável, reprodução quando pertinente, patch dentro do escopo e testes protegidos.
4. Imagens: brief novo, inspeção humana, parâmetros registrados e todas as tentativas contabilizadas.
5. Operação: cancelamento, interrupção, recarga, integridade, atualização e reversão.

As quantidades/metas iniciais estão no documento de critérios. O avaliador pode propor ajuste **antes** de conhecer resultados, com justificativa e aprovação. Não reduzir a amostra porque o candidato falhou.

## Comparação justa e independência

Executar base e candidato com mesma revisão de ferramenta, contexto e orçamento. Para imagem, intercalar a apresentação e ocultar a identificação base/candidato do revisor quando possível. Quando houver mais de um revisor, registrar divergências e a forma de resolução, sem inventar consenso.

Separar avaliação interna e final. Resultados finais usados para modificar o sistema passam a informar o desenvolvimento; reservar casos novos para futuras alegações de avaliação inédita. Não realimentar gabaritos finais no dataset automático.

## Evidência por caso

Guardar em área privada: ID, hash do caso, modelo/base, revisão, entrada permitida, saída integral, parâmetros, recibos de ferramentas, status, pontuação, motivo, recursos e duração. Erro, timeout, vazio ou ausência de teste não é acerto. “Bloqueado” não desaparece do denominador sem regra prévia.

O verificador não pode corrigir silenciosamente JSON, código ou imagem antes de pontuar a saída original. Pode registrar uma tentativa corrigida como novo resultado separado.

## Relatório e decisão

Apresentar métricas por família, total de casos, distribuição de falhas e limites da amostra. Uma média não apaga falha crítica. Uma melhora pequena sem margem confiável deve ser declarada inconclusiva.

Emitir recomendação de aprovar/rejeitar para um escopo específico; a ativação exige a autoridade definida pelo proprietário. Guardar hashes e a versão do relatório usados na promoção. Nenhuma avaliação finita prova segurança ou competência universal.
