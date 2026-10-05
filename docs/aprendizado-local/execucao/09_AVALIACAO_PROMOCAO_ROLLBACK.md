# Avaliação de competência, promoção e reversão

## Quatro avaliações, quatro perguntas

**Contratos de software:** o aplicativo, a fila, a API, os hashes e os controles funcionam? Dublês são válidos aqui quando identificados.

**Integração real:** o checkpoint escolhido carrega e gera, sem depender de serviço externo? Só execução com os pesos reais responde.

**Competência:** as respostas e imagens atendem a tarefas novas do escopo? Exige casos, oráculos e rubricas pertinentes, não apenas perda de treinamento.

**Operação:** cancelar, reiniciar, persistir e reverter funcionam sem corromper dados? Exige ensaio controlado.

Nenhuma dessas camadas substitui outra. CI verde não é aprovação do modelo.

## Protocolo de comparação

Congele a versão do código, a base, os datasets, as configurações, as ferramentas e a rubrica antes da prova. Avalie base e candidato sob condições iguais. Para isolar causas, mantenha ao menos três condições quando possível: base sem conhecimento, base com conhecimento, candidato com o mesmo conhecimento.

Essa separação evita atribuir ao fine-tuning um ganho que veio apenas de RAG ou de uma ferramenta nova. Se mudar ferramenta, prompt de sistema e pesos simultaneamente, declare a comparação como avaliação do sistema completo, não de um componente isolado.

O candidato não recebe gabaritos. O avaliador não modifica a resposta para fazê-la passar. Registre falhas, timeouts e saídas vazias no denominador. Use todas as amostras predefinidas, não apenas exemplos escolhidos depois.

## Código e testes

Cada correção de bug deve ser validada em cópia isolada. Identifique o contrato, reproduza a falha no original quando possível e confirme o comportamento esperado na proposta. Execute os testes existentes pertinentes e regressões novas com oráculo correto.

Proteja o avaliador e seus testes contra alterações pelo candidato. Testes criados pelo próprio modelo podem ajudar, mas não bastam como único oráculo. “Compilou”, “processo saiu com zero”, “nenhum teste foi descoberto” e “o modelo disse pronto” são estados diferentes.

Para stacks que exigem Windows, .NET Framework, IIS ou componentes específicos, registre essa necessidade. Não marcar a validação de um projeto Linux simples como validação desses ambientes. Sem executor isolado apropriado, a tarefa fica não verificada.

## Resultado, incerteza e decisão

Use as metas congeladas em `01_ESTADO_E_CRITERIOS_DE_CONCLUSAO.md`. Relate total de casos, acertos, falhas, bloqueados e distribuição por família. Se um caso é inválido por erro de especificação, registre a invalidação e revise a prova antes de reutilizá-la, sem ocultar o ocorrido.

Diferenças pequenas com poucos casos podem ser inconclusivas. Se o ganho-alvo não aparece ou há regressão relevante, mantenha a base ativa. Um candidato treinado e rejeitado é um experimento concluído, não uma versão promovida.

## Promoção controlada

Uma promoção precisa dos quatro elementos: artefato imutável; relatório aprovado; compatibilidade de carga; autorização humana de ativação. “O agente gostou” não preenche autorização humana.

Primeiro teste a nova versão num ambiente experimental, com configuração e diretório de dados separados do ativo. Documente diferenças de ambiente. Preserve manifesto e pesos anteriores. Pare o servidor ativo antes de trocar o registro. O CLI de referência recusa sobrescrita; não apagar o manifesto ativo sem um procedimento de recuperação comprovado.

Se for usar o fluxo manual existente, mova o manifesto anterior para um backup privado, registre o candidato completo, reinicie, execute consultas de sanidade e confira o modelo realmente ativo nos metadados. Se houver qualquer falha, pare o servidor e restaure o par anterior. Não escrever dois registros “ativos” conflitantes nem misturar tokenizer novo com pesos antigos.

ENG-06 deve automatizar esse processo com journal e verificação, mantendo a aprovação. Não inventar um comando de promoção antes de implementá-lo.

## Ensaio de rollback

Em instalação descartável, simular falha antes do registro, após o registro e após a primeira geração. Demonstrar retorno à base e preservação de conversas/artefatos. Conferir hashes do modelo anterior e executar um pedido conhecido. Um documento dizendo “há backup” não é ensaio.

## Declaração final permitida

“Candidato X, derivado de Y/revisão Z, treinado no dataset D e avaliado em N casos com estas métricas, foi aprovado para este escopo e ativado nesta instalação.” Não declarar equivalência geral com sistemas de fronteira ou que sabe qualquer tarefa.

Referências R2, R3 e R7 em [Fontes](../FONTES_E_COMPATIBILIDADE.md); orientação de testes T8. Ver também [protocolo do avaliador](../avaliacao/PROTOCOLO_AVALIADOR.md).
