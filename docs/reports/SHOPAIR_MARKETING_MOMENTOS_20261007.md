# ShopAir: ensino e avaliação de marketing por momento

Data: 07/10/2026. Entrega de documentação, consulta central e avaliação experimental. Não é homologação de gestão autônoma.

## Resultado entregue

[PDF de 40 páginas](../../output/pdf/SHOPAIR_MARKETING_GESTAO_MOMENTOS_20261007.pdf) e [conteúdo editável](../../marketing/shopair-momentos/README.md): 12 momentos, 8 canais, 8 comentários, 8 propostas de melhoria e 8 áreas de gestão. Há briefing, pesquisa de mercado, direção visual, textos, respostas, rotina, indicadores, hipóteses de produto, critérios de aceite e limites de execução.

Foram consultadas 19 fontes oficiais, com data e restrições de interpretação: ShopAir, plataformas de conteúdo, Sebrae, fornecedores concorrentes, ANPD e Qwen. Pesquisa geral não foi usada como resultado da ShopAir. Dados reais de clientes, retenção, orçamento, termos e contas sociais não foram fornecidos. As contas financeiras e de campanhas são simulações identificadas, com dados diferentes dos casos privados de avaliação.

Autoria explícita: a LocalAuthor produziu rascunhos de linguagem reais. O supervisor definiu o roteiro de gestão, pesquisou, avaliou e corrigiu conteúdo e arte. O registro editorial contém 40 alterações com hashes antes/depois e motivo. Não atribuir essas correções ao modelo como habilidade autônoma demonstrada. A revisão técnica não equivale à aprovação comercial do usuário.

## Inferência e ensino realmente executados

Modelo local: `Qwen/Qwen3-8B-GGUF`, revisão `7c41481f57cb95916b40956ab2f0b139b296d974`, pesos de hash `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`. Foi utilizada a infraestrutura Docker/GGUF local da LocalAuthor, com isolamento verificado, código e pesos somente para leitura e offload de GPU exigido pelo runtime. Não houve API externa de IA ou download de pesos.

Foram preservadas 60 conclusões reais do modelo, 32 erros anteriores à conclusão e 12 pedidos substituídos sem execução. Os erros incluem contexto insuficiente, tentativa de perfil fora do orçamento permitido e encerramento do worker; não são respostas corretas nem todos são falhas semânticas do modelo. Não houve truncamento nas conclusões registradas. Esses números não significam 60 tarefas aprovadas.

A primeira proposta inventou oferta gratuita, limites numéricos e confundiu a empresa de software com estoque de uma loja. O supervisor devolveu os erros e a LocalAuthor reescreveu. Planos grandes continuaram inventando ofertas, causas, prazos e funcionalidades; o roteiro final exigiu supervisão e composição em tarefas menores.

Foi investigada a orientação do fornecedor para evitar decodificação gulosa no modo de raciocínio. O perfil recomendado foi aplicado apenas em uma cópia privada do laboratório, mantendo pesos e imagem fixados, proteção de isolamento e limites existentes. Incluiu seis cenários novos, um substituto com números estruturados e três repetições do mesmo prompt para inspeção. O experimento não eliminou os erros nem demonstra causalmente a influência do sampler. Não houve promoção do perfil ou mudança na configuração de produção.

## Avaliação de capacidade, distinta dos testes de software

- Primeira amostra independente: 24 casos; 12 aprovados, 4 parciais e 8 reprovados por revisão externa semântica.
- Oito casos novos após feedback: 6 aprovados, 1 parcial e 1 reprovado. A resposta parcial ainda sugeria conformidade não demonstrada; a reprovada confundiu emissão fiscal com taxa fiscal.
- Duas transferências posteriores de linguagem também falharam: negativa sem evidência e resposta fora do assunto com garantia indevida.
- A correção do mesmo caso não foi contada como êxito independente. Um pedido que não chegou a gerar após o worker parar também não foi declarado aprovado.
- Na comparação privada de amostragem, uma entrada concatenada de moeda e quantidade foi invalidada por erro de elaboração do supervisor. O caso substituto com campos JSON claros calculou corretamente os valores, conferidos externamente.

Cálculos estruturados demonstraram respostas corretas em exemplos delimitados. Isso não compensa erros comerciais, garante ROI ou comprova capacidade de gerir qualquer empresa. Não usar número de arquivos, formato JSON, autodeclaração do modelo, testes unitários ou instruções registradas como certificado de inteligência.

**A LocalAuthor não está qualificada para gestão empresarial autônoma, publicação externa ou gastos sem revisão.** Os erros críticos foram rejeitados e as peças do caderno são conteúdo conjunto revisado, não um resultado integral autônomo da IA. Não houve postagem, anúncio, envio a terceiros, cobrança, mudança de produto ou deploy nesta atividade.

## Persistência no servidor central

A [lição original](../../knowledge/skills/GESTAO_MARKETING_POR_MOMENTO.md) foi importada oficialmente para consulta em três projetos, em versões preservadas. Houve desligamento cooperativo, backup anterior, verificação CRC, SHA da fonte e cópias ativas e retorno do servidor; o endpoint autenticado de projetos foi acessado após o reinício.

Seis feedbacks gerais foram armazenados como candidatos pela API de `ExperienceStore`, com backup SQLite anterior. Aceitação humana, direitos e treinamento permanecem falsos. A verificação técnica da importação não é qualificação do modelo. Os feedbacks não incluem respostas ou gabaritos dos casos privados. Consulta e memória de candidatos não alteram pesos e não garantem recuperação automática do conteúdo por todas as conversas.

Originais, prompts, gabaritos, recibos, diagnósticos, comparação de perfis e backups permanecem fora do Git. O pacote público contém somente propostas revisadas, dados didáticos novos, fontes, autoria e resultados sanitizados. Não indexar o pacote inteiro como corpus nem reutilizar temas publicados para alegar avaliação inédita. A infraestrutura e os pesos existentes permaneceram em seu estado anterior de produção.

## Verificação da entrega

- PDF reaberto, texto e coordenadas conferidos, todas as 40 páginas renderizadas e revisadas visualmente; páginas densas também inspecionadas em tamanho maior.
- Dezenove links HTTPS conferidos; contagens de cenários, hashes do PDF, registros editoriais e importação central consistentes.
- Fonte original e suas três cópias ativas têm o mesmo SHA; backups de conhecimento com CRC conferido; estados de direitos/treino preservados.
- `python scripts/run-tests.py`, no sandbox Linux offline inspecionado: 519 testes executados, 519 aprovados, zero falhas, erros ou ignorados; resultado completo.
- Esses 519 testes validam o software existente no snapshot da entrega, não o marketing real, a gestão da empresa ou novas funcionalidades de produto, que continuam propostas.

Conforme as instruções do repositório, entregar na `main`, sem force push, e conferir o CI da revisão publicada. O estado final do CI deve ser identificado pelo SHA publicado, sem confundir a avaliação semântica da IA com a suíte de software.

## Pendências que impedem autonomia

Corrigir com evidência e nova avaliação independente as confusões de termos e estados desconhecidos, a criação de ofertas e recursos e a comunicação de incidentes. Confirmar dados e objetivos reais com o responsável ShopAir, validar tarefas com gestores e medir um piloto autorizado antes de escalar. Integrações sociais, autorização de publicar/gastar, testes funcionais de novos módulos e treinamento dos pesos não foram realizados ou aprovados nesta entrega.
