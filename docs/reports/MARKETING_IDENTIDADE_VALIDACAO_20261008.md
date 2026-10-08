# Marketing com identidade e preferências — validação de 08/10/2026

A campanha antes recebia marca, público e objetivo, mas não tinha uma etapa
obrigatória para conhecer o histórico e confirmar o gosto do usuário. Agora há
perfil de marca, investigação pelo navegador da LocalAuthor, análise pelo modelo
local, revisão dessa análise e escolha humana da direção. A geração e a revisão
editorial recebem a identidade e o feedback aprovados.

## Evidências executadas

- `python scripts/run-tests.py`: 577 testes passaram em Docker Linux verificado,
  sem rede, usuário sem privilégios e sem skips. Não é teste de qualidade do modelo.
- `scripts/marketing-ui-smoke.py`: oito fluxos com navegador e API reais, coletor
  e modelo explicitamente substituídos por dublês. Inclui persistência, bloqueio
  antes da escolha, geração, revogação após feedback e isolamento entre projetos.
- Regressões de interface: voz (19 verificações), conversas (62), ferramentas
  avançadas e Foundation passaram; JavaScript sem erros nos fluxos executados.
- Investigação externa real: o navegador próprio da LocalAuthor abriu o perfil
  indicado, registrou sua captura e forneceu descrições acessíveis para o modelo
  local Qwen3.5-4B. Nenhuma captura do navegador do supervisor foi usada como entrada.
- Pesquisa real do site do produto e de documentação oficial do canal, com estados
  de coleta registrados separadamente. A documentação não virou referência criativa
  aprovada nem dados de desempenho da conta.
- A primeira análise real repetiu uma pergunta já respondida e confundiu temas do
  canal com a marca. Saída preservada; regras e casos negativos acrescentados. A
  análise seguinte passou pelo contrato e pela revisão local, formulando perguntas
  sobre gosto, referências e objetivo. A direção continuou sem aprovação; nenhum
  anúncio foi gerado/publicado nem verba gasta nesta avaliação real.
- Conhecimento original importado para consulta em três projetos centrais, com
  backup e hashes conferidos. Pesos não alterados e treino não autorizado.

## Limites observados

Recursos de imagem/CSS e requisições não permitidas do Instagram foram bloqueados
na investigação isolada. A leitura foi parcial. Esta avaliação não inclui login,
Insights, desempenho comercial nem análise dos pixels das artes. Descrições
acessíveis não substituem um modelo de visão. A revisão pelo mesmo modelo é feedback,
não certificação de autonomia. Sem preferência confirmada pelo usuário, o sistema
deve perguntar e aguardar; testes verdes não autorizam adivinhar seu gosto.

Originais, jobs, capturas, configurações e relatórios completos permanecem na pasta
privada de entrega do operador, fora do Git. O CI verifica separadamente a revisão
publicada; seu resultado deve ser conferido pelo SHA do commit.
