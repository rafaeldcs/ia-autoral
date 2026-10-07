# Lição Durável: Evoluir interfaces sem acumular fluxos antigos

**Título:** Evoluir interfaces sem acumular fluxos antigos

**Contexto:**
Ao desenvolver o repositório Orbit, percebi que a rejeição da primeira correção002 — que duplicava navegação com botões sem ação — era um sinal claro de que a interface precisava de uma reorganização mais eficiente. Aprendi que a evolução de interfaces não deve ser apenas uma adição, mas uma substituição estratégica de componentes antigos, mantendo funções úteis acessíveis.

**Aprendizado:**
- **Substituir composição antiga:** Reorganize a interface com base no objetivo principal, mantendo elementos essenciais visíveis.
- **Navegação por estado e clique:** Use estados e cliques para navegar, evitando duplicação.
- **Tarefa principal padrão:** Priorize ações centrais, com operações secundárias sob demanda.
- **Rótulos claros e acessibilidade:** Garanta rótulos claros, suporte a teclado, foco e `aria-pressed`.
- **Estados de carregamento, vazio e erro:** Implemente estados claros para feedback ao usuário.
- **Permissões no servidor:** Verifique permissões antes de exibir conteúdo sensível.
- **Segredos desmontados:** Remova dados sensíveis ao sair do contexto de acesso.
- **Testes:** Teste em desktop/mobile, troca de projeto e regressão.

**Decisão de remover/substituir/manter:**
Antes de codificar, formule perguntas:
- Essa funcionalidade ainda é relevante?
- Pode ser reutilizada em outro contexto?
- A interface é intuitiva e acessível?

**Checklist verificável:**
- [ ] Reorganize a interface com base no objetivo principal.
- [ ] Mantenha elementos essenciais visíveis.
- [ ] Use estados e cliques para navegação.
- [ ] Garanta rótulos claros e acessibilidade.
- [ ] Teste em diferentes dispositivos e contextos.

**Exemplo hipotético de marketing:**
Um painel hipotético de marketing poderia ter campanhas, contas sociais, credenciais e estatísticas agrupados. Propõe-se que as campanhas sejam a vista padrão, com estatísticas em uma visão separada e contas sociais/definições em outra, com credenciais acessíveis sob demanda. Essa é uma proposta, não implementada ou testada em um dashboard real.


**Nota:**
Este é um exercício interno orientado, não uma prova de autonomia. Consulta/orientação supervisionada, pesos não treinados, prints e aceite revisados pelo supervisor.

**Referências:**
- [W3C ARIA Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/)
- [W3C ARIA Disclosure Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
