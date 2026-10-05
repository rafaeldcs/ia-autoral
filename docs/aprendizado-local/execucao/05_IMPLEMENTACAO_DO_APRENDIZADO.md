# Implementações que o executor local precisa concluir

## Não existe um comando pronto para esta etapa

Este é um **backlog executável por um agente de desenvolvimento**, não uma lista de capacidades já disponíveis. Os nomes de módulos a seguir são propostas; inspecione a revisão local, reutilize o que tiver sido implementado e registre os nomes finais. Não declare um arquivo existente sem verificar seu conteúdo.

Preserve `src/localauthor/foundation/` como integração de inferência e o laboratório `nn/` como experimento distinto. Treinamento pesado deve operar em processo/ambiente separado, sem travar ou substituir a instalação ativa. Referências R2–R7 em [Fontes](../FONTES_E_COMPATIBILIDADE.md).

## P0 — Evidência, dados e execução real antes de prometer aprendizado

| ID | Implementação proposta | Critério de aceite e teste de falha |
|---|---|---|
| ENG-01 | Manifesto de experimento: revisão do código, modelo, dataset, tokenizer, seed, versões, limites, estado e aprovações | Rejeitar campo obrigatório ausente, revisão mutada e retomada com dataset diferente |
| ENG-02 | Conversor do JSONL exportado para dataset de treinamento, com conteúdo integral e licença de cada dependência | Rejeitar fonte não autorizada, exemplo vazio, Unicode inválido, ID repetido e truncamento não declarado |
| ENG-03 | Separação por famílias/projetos, deduplicação exata e similaridade revisada; índice de procedência | Alterar nomes de variáveis ou seed não permite atravessar partições; histórico não transporta gabarito de teste |
| ENG-04 | Avaliador de modelo real, sem fallback para dublês; manifesto das tarefas e resultados | Modelo ausente, resposta vazia, teste omitido ou erro de ferramenta nunca contam como acerto |
| ENG-05 | Trainer textual compatível com a arquitetura realmente escolhida | Piloto comprova parâmetros treináveis, gradientes finitos, alteração apenas nos pesos esperados, checkpoint e recarga |
| ENG-06 | Export de candidato e promoção/reversão com revisão e hashes | Candidato não sobrescreve base; falha no meio não deixa dois manifestos ativos conflitantes |

ENG-01 a ENG-04 precedem o treinamento final. Fazer o trainer primeiro e decidir os dados depois favorece resultados não auditáveis.

## P1 — Aprendizado operacional e eixo visual

**ENG-07 — Conhecimento versionado.** Acrescentar atualização, remoção e importação idempotente com identidade de fonte, hash e escopo. Vincular experiências às versões de código/documentos. A alteração de uma fonte deve marcar os derivados pertinentes como desatualizados. Testar revogação e isolamento entre projetos. Não treinar novamente toda vez que uma nota mudar.

**ENG-08 — Experiências reutilizáveis.** Recuperar apenas experiências relevantes e aprovadas para consulta, com data, validade, evidência e indicação de divergência de código. Uma experiência aprovada para uso não tem automaticamente direitos de treinamento. Rejeitar experiência cujo código de referência mudou de forma incompatível. Não recuperar todos os resultados antigos como fatos.

**ENG-09 — Operações visuais configuráveis.** Tornar dimensões, seed, passos e parâmetros do pipeline opções limitadas e registradas, com validação por arquitetura. O runtime de referência tem perfil fixo. Testar tamanho inválido, descrição longa, cancelamento e arquivo de saída ausente. Não chamar uma imagem criada por um dublê de resultado visual aprendido.

**ENG-10 — Trainer visual separado.** Somente quando a necessidade e o dataset visual forem aprovados. Aceitar pares de imagem e legenda com direitos, verificar integridade, controlar recortes e exportar resultado compatível. Testar recarga e inferência no mesmo pipeline previsto para produção; LoRA visual não é um adaptador textual.

**ENG-11 — Processo de experimento resiliente.** Persistir estado e checkpoints sem escrever no ambiente ativo; retomada deve verificar dados, versão e estado do otimizador. Limitar tempo, espaço, passos e tentativas. Cancelamento solicitado precisa de resultado rastreável, não encerramento forçado silencioso.

## P2 — Agente geral e modalidades adicionais

**ENG-12 — Agente de programação controlado.** Separar planejador/modelo e executor isolado. Começar por leitura de arquivos e busca; acrescentar propostas tipadas, build/testes em sandbox e revisão. Usar allowlist de ferramentas, argumentos validados, escopo de projeto, limites e evidências. Não permitir shell livre nem alterar a sandbox para fazer um caso passar.

**ENG-13 — Compreensão/edição de imagens.** É outra capacidade: exige entrada de imagem validada, modelo ou pipeline próprio, autorização e preservação do original. Só entrar no ciclo depois do mínimo v1. Áudio e vídeo também não são consequência automática deste pacote.

## Contrato do treinador textual proposto

Entradas mínimas: manifesto de experimento, base local imutável, tokenizador local, dataset autorizado e partição de validação, configuração de treinamento e diretório novo de saída. O treinador não recebe o gabarito final. Não deve usar strings de IDs remotos como fallback.

Saídas mínimas: configuração resolvida, lista/count de parâmetros treináveis, métricas por passo/avaliação, checkpoints seguros, estado de retomada privado e relatório do término. O status precisa distinguir `concluido`, `cancelado`, `falhou` e `bloqueado`.

Comprove que o treino altera as matrizes previstas. Para LoRA, a base congelada deve permanecer intacta. Para treino completo, o manifesto deve declarar que a base é copiada para um candidato e que todos os parâmetros pertinentes podem mudar. Não compare só o hash do arquivo se o serializador pode alterar metadados; verifique também os tensores selecionados.

## Testes a implementar antes da execução longa

Casos mínimos: falta de direitos; fonte revogada; código do checkpoint não revisado; gabarito no histórico; amostra com saída truncada; máscara de resposta vazia; NaN/Inf; checkpoint incompleto; retomada divergente; cancelamento; modelo ausente; pipeline visual incompatível; nenhuma ferramenta executada; zero testes descobertos; promoção sem aprovação; rollback após erro.

Use dublês para contratos e falhas, identificados como tal. Acrescente uma suíte opt-in de modelos reais separada. A suíte normal deve continuar rápida e honesta. Não marcar a suíte real como passada quando estiver desabilitada.

## Entrega de cada incremento

Implemente, execute os testes, leia o diff e registre a revisão. Aplique em cópia de laboratório antes de ativar. Documente o comando real a partir do `--help` implementado; apenas então ele pode ser usado nos documentos 07/08. Se houver bloqueio de GPU, conclua testes de contrato independentes, mas não qualifique a inferência ou o treino real.
