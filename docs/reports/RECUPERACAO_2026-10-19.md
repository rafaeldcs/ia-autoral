# Recuperação do chat e rascunhos — 19/10/2026

O chat principal agora salva o texto sem envio, mantém cópias locais e no servidor, recupera a seleção do perfil/projeto/conversa e consulta um diário de pedidos aceitos depois de reabrir. O [guia de uso](../RECUPERACAO_E_RASCUNHOS.md) explica os estados e limites.

## Implementação e revisão

- IndexedDB com confirmação da transação local e indicação de sincronização pendente; cópia SQLite por perfil, projeto e conversa, sem indexação ou treinamento do rascunho.
- Controle de revisão no servidor e cópias separadas por janela. Conflitos exigem comparação explícita; o texto nunca é interpretado como HTML.
- Checkpoint do conteúdo original antes do envio e registro transacional de identificador/digest/tarefa. Retentativas com o mesmo identificador recuperam a tarefa; conteúdo diferente é recusado. A criação da conversa também é idempotente.
- Metadados de resposta vinculam a mensagem ao pedido dentro da transação de gravação. Uma resposta confirmada prevalece mesmo se houver queda antes de atualizar o estado da fila.
- Reabertura consulta o estado. Pedidos desconhecidos, interrompidos ou com falha não são reenviados automaticamente. Uma nova tentativa após falha exige revisão, pois pode haver efeitos parciais.
- Rotas verificam perfil e acesso ao projeto. Um leitor não altera o rascunho. A identificação por nome continua organizacional, sem autenticação pessoal.
- Cliente 0.3.9 deixa a recuperação durável prevalecer sobre o mecanismo anterior em memória. Gateway inclui o novo arquivo de interface. Publicação em arquivo único inclui bibliotecas nativas do SQLite.

## Evidências locais

- Python 3.14/Windows: **664 testes, 661 aprovados, zero falhas/erros e três testes de links simbólicos indisponíveis por falta de privilégio do Windows**. Os 15 casos novos usam bancos reais, concorrência, reinício, permissões, conteúdo inválido, recibos e recuperação após gravação da resposta.
- Navegador real: **20 verificações aprovadas**, incluindo fechamento/reabertura, término real dos renderizadores do navegador temporário, edição sem servidor, sincronização posterior, conflito entre abas, perda da resposta HTTP após aceitação, reenvio explícito de pedido não aceito, não ressurreição de rascunho concluído, outra instalação sem armazenamento local e layout de 390 pixels. Sem erros JavaScript.
- HTTPS/gateway real: **11 verificações aprovadas**, com duas credenciais de dispositivos descartáveis, cookies separados, acesso ao rascunho/seleção e bloqueio a outro perfil.
- Fachada .NET: **16 verificações aprovadas**. Interfaces avançada, chat, foundation, voz, marketing, leads e perfis executadas novamente sem falhas.
- Atualizador nativo: **33 verificações aprovadas**, com atualização/reabertura autenticada pelos formulários reais, rascunho preservado, integridade e versão, recusa de servidor incorreto/revogação e retorno à versão anterior após falha.
- Instalador conectado 0.3.9: **14 arquivos extraídos com integridade**, incluindo o novo guia; conexão protegida por DPAPI e preservada numa segunda configuração.
- Ativação: backup SQLite íntegro e encerramento cooperativo do servidor. **13 projetos, 2 perfis e as mensagens existentes preservados**, novas tabelas presentes e arquivos servidos por HTTPS com certificado e hashes conferidos.

O teste inicial de queda usando `Page.crash` bloqueava a própria chamada CDP. O ensaio final termina somente os renderizadores enumerados pelo CDP do navegador descartável e aguarda o evento real de falha; passou sem intervenção. Os primeiros ensaios também identificaram botões habilitados antes de a seleção terminar e a necessidade de manter um registro vazio depois de concluir um envio, impedindo recuperar uma cópia antiga como atual. Ambos foram corrigidos sem remover as verificações.

O primeiro empacotamento manual do gateway omitiu a biblioteca nativa do SQLite. O pacote foi reconstruído e conferido em HTTPS; a opção de inclusão agora faz parte do projeto para publicações em arquivo único. Durante a atualização nativa, o driver de teste deixava de preencher o perfil porque comparava literalmente `/` com o endereço equivalente `/?`. Agora confere esquema, host, porta, caminho e ausência de parâmetros/fragmentos; mantém a automação enquanto cada WebView existe e reconecta quando o atualizador substitui o processo. Nenhum formulário ou validação de entrada foi contornado.

Relatórios completos, imagens, backups, bancos, conexões pareadas e executáveis privados permanecem fora do Git. O CI deve ser conferido no SHA publicado desta revisão, sem usar o resultado de uma revisão anterior como substituto.

O primeiro CI (`c03da1e`) identificou um clique durante a seleção inicial do projeto na interface móvel: a recuperação ainda podia substituir os botões após a tela se tornar visível. O chat agora só é exibido depois de resolver essa seleção. O teste de recuperação verifica esse limite enquanto a requisição ocorre, e os testes de interface foram repetidos. A falha original permanece registrada no CI; a conclusão exige conferir a revisão corrigida.

## Limites

Não é uma garantia de perda zero: vale a confirmação de salvamento; uma queda anterior a ela pode perder a edição ainda pendente. Outro computador recupera a última cópia confirmada pelo servidor. Cópias locais não sincronizadas dependem da instalação e origem do navegador. Voz em andamento e formulários das ferramentas avançadas não receberam esse checkpoint. O recurso não desfaz efeitos parciais de ferramentas, não repete jobs interrompidos e não reinicia loops sozinho.

Os testes de conversa usam respostas determinísticas declaradas; não demonstram melhora da inteligência ou dos pesos da IA. Não foi usado um segundo computador físico.
