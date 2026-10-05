# Especializar texto e código sem perder a base

## Pré-requisitos bloqueantes

Só executar após ENG-01 a ENG-06, licença e dataset aprovados, ambiente homologado e baseline real. O CLI foundation inspecionado não oferece treinamento. O comando `localauthor train` usa o Transformer NumPy e **não deve ser empregado para especializar Nemotron**. Referências R2/R3/R6.

A primeira hipótese de aprendizado é comportamental: seguir pedidos, responder em português, usar evidências, produzir código compatível e reconhecer o que não foi validado. Não tentar recriar pré-treinamento geral com os Markdown deste pacote.

## Escolher a receita compatível

Priorizar ajuste supervisionado; considerar LoRA quando os módulos e o runtime suportarem. Inspecionar a arquitetura e enumerar módulos/parametrizações antes de selecionar alvos. Não presumir que todo Nemotron use os mesmos nomes de projeções de um Transformer denso. A compatibilidade deve ser demonstrada para a revisão escolhida.

O `device_map=auto` usado para inferência não é uma receita genérica de treinamento distribuído. O executor deve configurar o dispositivo/estratégia no treinador compatível e testar o backward. Técnicas de quantização, offload e checkpoint de ativações exigem prova própria; não habilitar todas ao mesmo tempo sem identificar o efeito.

TRL/PEFT oferecem mecanismos de SFT e adaptação, mas sua existência não prova a compatibilidade com qualquer checkpoint. Consulte as versões fixadas, não apenas uma documentação `main` que muda. Referências T3/T4.

## Contrato entre inferência e treinamento

Tokenizador, template de chat, IDs especiais, política de término e formato das mensagens devem corresponder ao runtime. A implementação de referência aplica `enable_thinking=False`; não treinar um formato incompatível e esperar que a inferência corrija depois.

Treine a resposta desejada, não a reprodução indiscriminada de prompts, documentos e mensagens de sistema. Se usar máscara de assistant/completion, visualize pelo menos três amostras tokenizadas, incluindo multi-turno, código e resposta curta; confirme que há tokens-alvo válidos e que padding/contexto não recebem perda indevida. As máscaras dependem do formato e do chat template. Não use uma flag sem testar seu efeito. Referência T3.

O prompt atual diz que o modo não executa ferramentas. Exemplos de agentes com chamadas de ferramentas só entram depois de criar um contrato próprio e versionado; não misturar os dois comportamentos e ensinar a alegar execução sem recibo.

## Piloto curto obrigatório

Execute um piloto com um subconjunto autorizado de desenvolvimento, nunca a avaliação final. Defina previamente o limite de passos, disco e tempo; registre os valores efetivos. Um número pequeno de passos serve para teste técnico, não para comprovar competência.

Comprove: forward e backward válidos; gradientes finitos; loss finita; parâmetros treináveis contados; atualização das matrizes previstas; base preservada quando congelada; checkpoint salvo; interrupção cooperativa; retomada validada; inferência após recarga. Gere uma resposta antes/depois com o mesmo prompt e parâmetros, sem tratar diferença textual como prova de melhoria.

Armazene seed, estado aleatório, etapa do otimizador e revisão dos dados para retomada. Um checkpoint de otimizador de origem desconhecida não deve ser carregado como se fosse seguro; mantenha o estado de treino no perímetro confiável e o export de inferência em formato seguro.

## Configuração do experimento final

O executor deve criar e revisar a configuração real, não preencher valores fictícios. Registre tamanho de sequência, batch efetivo, acumulação, precisão, learning rate, schedule, epochs/passos máximos, weight decay, clipping, alvos/rank do adaptador e política de checkpoint. Determine isso no piloto e no orçamento medido; não copiar valores de outro modelo sem justificativa.

Uma busca pequena e previamente delimitada pode comparar duas ou três configurações. Escolha por validação e critérios congelados, sem abrir repetidamente o teste final. Se não houver sinal de ganho, revise dados/objetivo antes de aumentar o treinamento. Ao exceder o limite de tentativas ou detectar platô, concluir o experimento como inconclusivo/rejeitado e registrar próximo diagnóstico; não treinar indefinidamente.

Mantenha amostras de competências gerais autorizadas para medir regressões. Adaptar ao estilo do proprietário não pode ensinar a inventar testes, apagar licenças ou ignorar instruções de segurança.

## Export e uso pelo LocalAuthor

Treinar LoRA produz um adaptador dependente da base. O loader atual exige checkpoint completo e rejeita adaptador isolado. Quando a arquitetura suportar fusão, exporte para uma pasta nova; caso contrário, implemente primeiro um backend base+adaptador com verificações correspondentes. Não contornar o verificador removendo `adapter_config.json` e fingindo que o resultado é completo.

Recarregue o export em ambiente limpo, local-only, e compare saídas/métricas com o candidato antes do export dentro de tolerâncias documentadas. Um hash diferente não prova equivalência. A licença e a procedência da base permanecem no modelo derivado.

## Critério de saída

Experimento concluído com evidências de atualização, recarga e avaliação. Separar quatro resultados: treinamento executado; competência melhorou/não melhorou; candidato aprovado/rejeitado; instalação ativa alterada/não alterada. Apenas o primeiro não autoriza os demais.

Próxima etapa: [Avaliação e promoção](09_AVALIACAO_PROMOCAO_ROLLBACK.md). Referências externas T3/T4 em [Fontes](../FONTES_E_COMPATIBILIDADE.md).
