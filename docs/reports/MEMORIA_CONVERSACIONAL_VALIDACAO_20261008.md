# Validação da memória por conversas — 8 de outubro de 2026

Implementada memória explícita por projeto no chat: guardar, consultar e
desativar notas, com confirmação e origem visíveis. Mensagens e alteração de
memória são gravadas na mesma transação. Preferências entram como dados no
contexto Foundation, dentro do orçamento calculado pelo tokenizer; a resposta
informa notas usadas e omitidas. Não foram treinados pesos ou aprovados exemplos
automaticamente para treinamento. Nenhuma nova dependência externa.

## Software

- `python scripts/run-tests.py`: 589 aprovados, zero falhas, erros ou skips,
  em contêiner Linux offline verificado, sem montagem de dados privados.
- Doze casos novos: persistência, origem no histórico, duplicação, revogação,
  reativação, isolamento, código/citação sem promoção a memória, segredos,
  tamanho/quantidade, cancelamento/quota, rollback de escrita, contexto de nova
  conversa e orçamento de contexto. A geração nesses testes usa dublê explícito.
- Chromium real: chat/layout 65 verificações; marketing 8 fluxos; voz 19
  verificações; ferramentas 10 fluxos; Foundation 14 fluxos. Os modelos desses
  testes de interface são dublês; isso não mede qualidade de modelos ou voz.
- O primeiro roteiro de navegador tentou acessar a navegação fechada em viewport
  móvel. O roteiro foi corrigido para retornar ao desktop antes desse trecho;
  a repetição integral dos cinco roteiros passou.

## Inferência local real

Servidor central atualizado e reiniciado cooperativamente. Um projeto de
laboratório recebeu uma preferência sintética pelo chat. Em outra conversa, o
modelo registrado `unsloth/Qwen3.5-4B-GGUF`, revisão
`e87f176479d0855a907a41277aca2f8ee7a09523`, executou inferência local no runtime
Docker GGUF verificado e respondeu **Farol Violeta 73**. Após desativar a nota,
uma terceira conversa respondeu **Não informado.**

As evidências privadas incluem as mensagens, respostas, metadados e contexto
efetivamente enviado à inferência. A primeira geração recebeu a nota; a segunda
não recebeu a nota ou seu histórico. Ambas permaneceram sem aprovação para
treino e o manifesto de modelo permaneceu inalterado. As três conversas podem
ser vistas no projeto **Laboratório — memória por conversas** do servidor.

Esse ensaio verifica um exemplo sintético e dois resultados reais; não demonstra
generalização para todos os pedidos, domínio profissional ou equivalência a
modelos de fronteira. Memórias não substituem fontes, testes, autorização de
ações ou aprovação explícita de estilo no fluxo de marketing. Campanhas antigas
continuam no painel Marketing e não foram convertidas em conversas.

O código, os testes e este relatório são publicados juntos. A revisão exata e
o resultado de CI devem ser conferidos no GitHub antes de declarar a entrega
publicada e validada.
