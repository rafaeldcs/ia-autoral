# Estado real e critérios para concluir o ciclo local

## Base conferida

A inspeção de 05/10/2026 usou `dd8a1376ad89230461fd85b2fcb5b5507590dcec`. Os contratos abaixo vêm de `docs/FOUNDATION.md`, do CLI e do runtime consultados; os objetivos de evolução são propostas deste pacote. Referências R1–R7 em [Fontes](../FONTES_E_COMPATIBILIDADE.md).

| Capacidade | Na revisão inspecionada | O que falta comprovar localmente |
|---|---|---|
| Cadastro de modelo textual/visual | Manifesto local, hashes e revisão | Licença, compatibilidade e carregamento do checkpoint escolhido |
| Conversa com contexto | Histórico e recuperação lexical | Qualidade, referência correta e orçamento no modelo real |
| Markdown | Importação privada por projeto | Seleção, integridade, atualização e ausência de vazamento |
| Texto/código | Saída textual; sem execução geral de ferramentas | Qualidade por tarefa e um agente controlado, se implementado |
| Imagens | Pipeline visual distinto; 512 × 512, 20 passos, seed 31 | Qualidade, compatibilidade e execução real |
| Experiências | Persistência e revisão; exportação candidata | Curadoria completa, vínculos com fontes e validade |
| Treinamento foundation | Não implementado | Trainer, datasets, checkpoints, retomada e avaliação |
| LoRA isolado no runtime atual | Não aceito como modelo completo | Export completo compatível ou backend adicional revisado |
| Autoaprendizado/promoção | Não implementados | Fluxo com limites, evidências e aprovação |
| Entendimento/edição de imagens | Não implementados | Modelo/pipeline e contratos próprios; fora do mínimo v1 |

## Quatro resultados distintos

**N1 — Plataforma local homologada:** modelos reais geram texto e imagens na instalação escolhida; não há dependência de serviço externo de IA; identidade dos modelos e restrições estão registradas. Instalar pacotes não conclui N1.

**N2 — Conhecimento operacional validado:** as sete notas permitidas e notas privadas aprovadas são recuperadas no escopo certo; referências são verificáveis; experiência pode ser reutilizada quando válida, mas somente se essa recuperação estiver efetivamente implementada. Importar Markdown não modifica pesos.

**N3 — Especialização textual/código concluída:** existe dataset autorizado, piloto real, treino completo delimitado, checkpoint/adaptador diferente da base, recarga testada e avaliação comparativa. Um candidato pode terminar o treinamento e ser rejeitado. Rejeição é um resultado do experimento, não promoção.

**N4 — Especialização multimodal v1 concluída:** N3 mais geração visual aprovada no currículo. Fine-tuning visual é obrigatório somente se a lacuna de estilo/domínio foi definida e não atendida pela base. Sem essa necessidade, registrar explicitamente “geração visual homologada com pesos de base; especialização visual não realizada por decisão de escopo”. Não alegar treinamento de imagens nessa situação.

A meta deste pacote é chegar ao nível acordado com evidência, preservando níveis já concluídos. Não há atalho de N1 para N4 por renomear um checkpoint.

## Estados e evidências

Use `PENDENTE`, `EM_EXECUCAO`, `BLOQUEADO`, `FALHOU`, `CONCLUIDO` ou `NAO_APLICAVEL`. `NAO_APLICAVEL` precisa de justificativa aceita e não pode ocultar um requisito obrigatório.

Cada transição para `CONCLUIDO` exige: revisão de código, comando ou procedimento, horário, ambiente, código de saída quando aplicável, artefato verificável, hash e limitações. Revisão humana exige identidade real do revisor e decisão explícita.

## Critérios de aceite propostos para v1

Os limiares são metas de projeto, não padrões científicos nem garantias de suficiência. Devem ser aprovados e congelados antes da avaliação final.

- **Controles críticos:** nenhum acesso entre projetos, execução não autorizada, treinamento sem direitos ou relato falso de teste nos casos críticos preparados. Uma única falha crítica bloqueia promoção; sucesso finito não prova ausência universal de falhas.
- **Conhecimento:** em uma bateria interna de ao menos 30 consultas, atingir 90% de recuperação da evidência esperada; todas as referências emitidas devem ser verificadas separadamente. As perguntas finais serão diferentes.
- **Código:** em ao menos 30 tarefas finais de famílias diversas, atingir a meta pré-definida de resolução verificada e comparar com a base nas mesmas condições. Sugestão inicial: 80% para tarefas delimitadas, zero mudança fora do escopo e nenhuma regressão crítica.
- **Conversa:** em ao menos 30 casos, pelo menos 90% de atendimento ao requisito, incluindo português e preservação de identificadores; sem inventar fontes nos casos críticos.
- **Imagens:** em ao menos 20 briefs, cumprir todas as restrições obrigatórias e média de pelo menos 4/5 na rubrica humana. Não descartar falhas da contagem.
- **Operação:** retomada após interrupção e reversão para a versão anterior demonstradas em ambiente de teste.

Amostras pequenas servem para aceite interno delimitado. Registre numeradores, denominadores e incerteza; diferenças pequenas não justificam “melhor modelo” sem evidência adicional.

## Condição adicional para remover o pacote

Concluir um nível parcial continua sendo um resultado válido para uma sessão, mas não cumpre a solicitação de limpeza final. Somente a conclusão integral do escopo v1 aplicável libera [a conferência e limpeza](../99_CONFERENCIA_E_LIMPEZA.md). Itens opcionais só podem ser `NAO_APLICAVEL` com justificativa e decisão de escopo reais; requisitos obrigatórios bloqueados, falhos ou não verificados impedem a remoção. Uma aprovação não pode ser inventada pelo executor.
