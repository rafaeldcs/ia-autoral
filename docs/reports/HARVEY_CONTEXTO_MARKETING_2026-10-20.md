# Correções de contexto e marketing — 20/10/2026

Esta entrega corrige a janela de trabalho do agente local e reforça a fidelidade das ofertas e dos recursos de produto. Usa os pesos existentes `unsloth/Qwen3.5-4B-GGUF`, na RTX 2060 de 6 GB, com perfil experimental de 8.192 tokens e saída de até 1.536. Não altera pesos nem promove automaticamente esse perfil no manifesto do servidor. As regras compartilhadas entram no chat da foundation; a validação de recursos também entra no workflow de marketing. Operação: [HARVEY_LOCAL.md](../HARVEY_LOCAL.md).

## Evidências observadas

| Verificação | Resultado |
| --- | --- |
| Suíte final do software | 704 testes: 701 passaram, zero falhas/erros, três skips de links simbólicos indisponíveis no Windows local |
| Motor original, ferramentas e documentos em Docker | Smoke aprovado, com modelos/juiz roteirizados explicitamente; inclui histórico somente leitura, `grep` em arquivo e detecção de conclusão natural com recursos sem suporte |
| Cinco regressões com inferência real, lote final v4 | Cinco aprovações provisórias pelo juiz local e **30/30 asserções independentes** específicas dos casos |
| Texto antigo prometendo demonstração gratuita | Continua reprovado pela verificação independente; original preservado |
| Autocorreção de funcionalidades não informadas | Quatro rascunhos iniciais foram rejeitados; a própria LocalAuthor reescreveu os quatro e concluiu sem as famílias ausentes detectadas |
| Documento longo | Chamada original com 15.481 tokens, janela ativa reduzida explicitamente para 6.629; tarefa e regras intactas, arquivo completo preservado por hash |
| Recuperação fora do trecho ativo | IA local recuperou `K8F4`, CTA `Solicitar conversa` e preço `R$ 49,00`, todos no meio do documento; não inventou gratuidade |

Os cinco casos cobrem preço desconhecido, gratuidade confirmada, demonstração paga, referência de concorrente e documento longo. São desenvolvimento interno, não um conjunto reservado de qualificação. Os critérios e documentos não foram alterados entre as versões do lote. O conjunto original de quatro tarefas também foi repetido durante a investigação, preservando suas falhas.

## O que mudou e por quê

O corte silencioso de 6.000 caracteres foi removido. O tokenizer real verifica a janela; um arquivo completo de cada chamada fica em montagem somente leitura, acompanhado de hashes e avisos de trechos/mensagens fora da janela. A IA pode buscar páginas, ranges ou reler o original. As recontagens têm limite explícito e entram no orçamento de vida do runtime. Instruções obrigatórias e a última ação que não caibam ainda falham de forma explícita. Não se apresenta contexto ilimitado.

A regressão longa revelou um defeito no `grep` upstream: o schema aceitava arquivo, mas a busca iterava `Path.glob` sobre o arquivo e retornava ausência falsa. O adaptador corrige essa divergência mantendo a busca original no diretório com filtro exato. A execução real do teste longo passou após a correção.

Instruções sozinhas não impediram todas as extrapolações de marketing. Foram acrescentados feedback verificável e controle conservador de famílias de recursos ausentes nas fontes. Candidatos rejeitados e corrigidos ficam em `grounding-checks.jsonl`. A IA recebe o erro e edita a própria resposta; o operador não substitui o anúncio por um texto pronto. O controle também é aplicado ao encerramento sem ferramenta, e pontuações originais do Harvey permanecem preservadas.

## Falhas que permanecem visíveis

Lotes intermediários tiveram falsas ausências de busca, anúncios com estoque/automação não informados e divergências do juiz. Um lote chegou a cinco aprovações do juiz, embora as verificações expandidas detectassem extrapolações em quatro anúncios. Por isso a autoavaliação não foi aceita como prova suficiente.

No piloto intermediário de quatro tarefas, o marketing corrigido passou, mas o juiz reprovou um roteiro de QA por não conter evidência de execução, embora fosse apresentado como planejado. Essa falha não foi apagada. A orientação do avaliador foi reforçada para não exigir provas de ações proibidas ou não solicitadas. O roteiro também exige revisão de conteúdo; esta entrega não certifica competência geral de QA.

Uma execução da suíte teve `ConnectionAbortedError` no teste HTTP de voz no Windows. O teste foi repetido isoladamente e passou; a suíte completa posterior também passou. O log e o relatório da execução interrompida permanecem privados, sem remoção do teste ou relaxamento da validação.

## Limites e reprodução

O juiz continua sendo o mesmo modelo e não é independente. As 30 asserções são verificações determinísticas estreitas, com vocabulário explícito, não compreensão universal de marketing. Presença de uma expressão na fonte não comprova que ela é afirmativa ou aplicável ao produto. Condições de publicação e revisão humana continuam necessárias. Não houve fine-tuning, nova capacidade neural universal ou conclusão das 2.010 tarefas jurídicas.

Os lotes, snapshots integrais do controlador, dados, textos e hashes individuais ficam no armazenamento privado de benchmarks do servidor. O lote jurídico antigo de 4.096 tokens foi interrompido entre tarefas para a comparação, preservando 15 reprovações e o restante pendente. Ensaios adicionais com documentos originais usam controlador congelado e reportam seus próprios estados; não se confundem com os cinco casos sintéticos aprovados.

Execute `scripts/run-tests.py`, o smoke de Docker e os comandos de regressão do guia para reproduzir o software. A execução real exige os pesos locais revisados, a imagem imutável e hardware compatível. O CI da revisão publicada é conferido separadamente; CI de software não homologa os pesos.
