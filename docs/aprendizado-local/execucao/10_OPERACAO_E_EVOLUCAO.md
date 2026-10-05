# Operação contínua, memória e retomada

## Aprendizado por evento, não treino indiscriminado

A execução diária pode produzir experiências candidatas. Somente experiências autorizadas e verificadas entram em um dataset. Revisar conhecimento e recuperar uma solução antiga não exige alterar pesos; frequentemente é a escolha mais adequada para informações específicas ou que mudam.

Treinar novamente deve responder a uma hipótese: qual falha recorrente não foi resolvida por correção de código, atualização de documentos, recuperação melhor ou parâmetros adequados? Sem hipótese e avaliação, não iniciar outro ciclo.

## Registro privado persistente

Copie os templates de `estado/` para a área privada e preserve versões. Para cada tentativa, registre estado, revisão, modelo, dataset, comando real, evidências, consumo, decisões e próximo passo. Atualize o arquivo antes e depois de operações longas. O texto preenchido não executa nada: uma automação precisa de um runner implementado e autorizado.

Ao retomar, verificar primeiro se há processo/job em execução, se o checkpoint é íntegro e se a operação anterior terminou. Não reenviar uma tarefa apenas porque houve falha de conexão. O aplicativo já possui fila persistente e estados de interrupção, mas o novo treinador precisa do seu próprio protocolo de retomada.

## Orçamento e parada

Antes de cada ciclo, definir limites de tempo, GPU, RAM, armazenamento, passos, exemplos, tentativas de correção e configurações comparadas. Estimar apenas como planejamento, registrar o consumo real depois. O máximo de uma execução deve ser configurado no runner, não apenas descrito num Markdown.

Diante de NaN, checkpoint corrompido, direitos ausentes, violação crítica ou mudança inesperada do ambiente, interromper com estado explícito. Um erro de licença não pode ser contornado escolhendo silenciosamente outra origem. Um modelo menor pode validar engenharia, mas não representar qualificação de um maior.

## Pesquisa e atualização de conhecimento

Consultar primeiro memória local válida e documentos oficiais já disponíveis. Quando faltar informação e houver rede autorizada, pesquisar apenas o necessário; registrar URL, data, versão, trechos utilizados, hash e motivo. Não pesquisar novamente só porque a pergunta foi reformulada: verificar o conteúdo e sua validade. Também não reutilizar indefinidamente uma fonte vencida.

Guardar uma fonte não autoriza treinamento. A cópia privada de um material pode ter restrições de uso; registrar a decisão separadamente. Conteúdo de projetos diferentes não deve se misturar por conveniência de busca.

Para pesquisar, o executor precisa de ferramenta própria autorizada. O modo foundation atual não ganha navegador ou ferramenta de busca por ler esta instrução. A pesquisa da plataforma tem seus controles e deve permanecer separada do runtime de inferência.

## Ciclo proposto de manutenção

Revisar experiências quando houver volume útil e disponibilidade humana, não a cada resposta. Atualizar notas quando seus arquivos de referência mudarem. Executar regressões quando trocar código/runtime/modelo. Reavaliar direitos antes de cada exportação e antes de distribuição de derivados.

Frequências e horários só devem ser configurados depois da decisão do proprietário. Este pacote não agenda tarefas, não cria um serviço de treinamento e não liga autoaprendizado em segundo plano.

## Segurança e recuperação de dados

Preservar dados privados fora do Git. Fazer backups consistentes com serviço parado e ensaiar restauração. Pesos externos exigem inventário/backup próprios. Remover uma fonte precisa alcançar os derivados relevantes por política; não prometer esquecimento de um checkpoint já treinado sem método avaliado.

Revisar quotas: experiências e imagens podem atingir limites do runtime. Não apagar automaticamente os itens mais antigos se ainda são evidência de um modelo ativo. Arquivar com recibo e verificar integridade antes de remover qualquer cópia.

## Encerramento de cada sessão

Preencher o estado e o relatório com o nível efetivamente atingido, alterações, resultados e bloqueios. Identificar separadamente código comitado, instalação atualizada, modelo carregado, treino executado, avaliação aprovada e promoção realizada. O próximo executor deve conseguir continuar sem depender da memória desta conversa.

## Encerramento integral e retirada dos roteiros

Quando não houver pendência obrigatória e todas as evidências estiverem conferidas, seguir [99_CONFERENCIA_E_LIMPEZA.md](../99_CONFERENCIA_E_LIMPEZA.md). Migrar o conhecimento útil para seu destino durável, preservar relatórios/artefatos privados e retirar os arquivos temporários do Git em commit separado. Esta não é uma rotina periódica de exclusão e nunca remove dados do aprendizado. Enquanto houver bloqueio ou retomada pendente, manter o pacote.
