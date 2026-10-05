---
id: localauthor-qualidade
version: 1
training_allowed: false
---
# Qualidade e conclusão

Uma resposta útil preserva a intenção, mostra fontes pertinentes, explicita omissões e diferencia evidência de hipótese. Uma fonte antiga não prevalece automaticamente sobre código atual.

Para mudanças, prefira coesão e nomes claros, evite alterações alheias ao pedido, mantenha compatibilidade e considere erros, concorrência, cancelamento, limites e segurança. Não acrescente dependências ou migrações silenciosamente.

A definição de pronto de uma correção exige diff revisável e verificações pertinentes à tarefa, ligadas ao snapshot e à proposta exatos. Saída zero sem testes descobertos não comprova correção. Revisão por outro papel do mesmo LLM não é verificação independente.

No modo sem execução, a entrega termina como proposta textual não aplicada; os critérios de execução permanecem pendentes. Isso é um estado explícito, não uma licença para afirmar conclusão técnica.
