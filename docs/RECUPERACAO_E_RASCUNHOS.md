# Recuperar o chat após fechar ou uma falha

A LocalAuthor salva automaticamente o texto do chat principal por **perfil, projeto e conversa**. Também registra qual conversa estava aberta. As mensagens concluídas continuam no histórico do servidor.

## Uso normal

1. Escolha seu nome e abra um projeto.
2. Digite normalmente. Abaixo do campo, acompanhe **Salvando rascunho…** e **Rascunho salvo**. Não é necessário enviar a mensagem para guardar o texto.
3. Ao reabrir e escolher o mesmo perfil, a aplicação procura o último projeto e conversa acessíveis e restaura o rascunho. Código, acentos, quebras de linha e comentários são preservados como texto.
4. **Descartar rascunho** pede confirmação e limpa apenas o rascunho atual. Não apaga mensagens enviadas.

O navegador/WebView guarda uma cópia em IndexedDB. O servidor guarda outra no banco privado `memory.sqlite3`. **Salvo neste computador; sincronização pendente** significa que a cópia local existe, mas o servidor ainda não confirmou a edição. Ao reconectar, a aplicação tenta sincronizar o rascunho; isso não envia uma mensagem para a IA.

## Outro computador e versões diferentes

A cópia confirmada pelo servidor pode ser recuperada em outro computador conectado ao mesmo servidor, ao selecionar o mesmo perfil. A cópia ainda não sincronizada pertence à instalação e ao endereço do navegador que a salvou; mudar IP, limpar dados do navegador ou trocar computador não transfere essa cópia automaticamente.

Se duas janelas alterarem o mesmo rascunho, a revisão no servidor impede uma substituição silenciosa. **Ver versões** apresenta o texto de cada cópia. **Usar esta versão** salva a escolha sem enviar a mensagem; as outras cópias locais são preservadas. Revise também o modo e qualquer pedido pendente antes de continuar. O limite é de 200 rascunhos ativos por perfil no servidor e 200 cópias locais ativas por perfil. O servidor aceita até 8.000 caracteres e 32.000 bytes por rascunho; o status informa quando não pode sincronizar.

## Um envio ficou sem resposta

Antes de enviar pelo chat principal, a aplicação salva o conteúdo e um identificador do pedido. O servidor registra esse identificador junto com a tarefa. Repetir o mesmo identificador e conteúdo devolve a tarefa existente; um conteúdo diferente com o mesmo identificador é recusado.

Ao reabrir, a aplicação **consulta**, sem reenviar:

- Se a resposta já está gravada, abre o resultado no histórico e limpa o checkpoint do envio.
- Se a tarefa está na fila ou executando, mostra **Consultar pedido** e **Parar tarefa**. O fechamento da janela não cancela a tarefa do servidor.
- Se o servidor não confirma o pedido, mantém o texto e oferece **Reenviar com segurança**. Esse botão explícito reutiliza o identificador e o conteúdo originais.
- Se houve falha, interrupção ou cancelamento, mantém o texto. Pode existir trabalho parcial: confira os resultados antes de usar **Preparar nova tentativa**, revisar a mensagem e enviar um pedido novo.

Uma tarefa interrompida durante a execução não é repetida automaticamente. O diário de pedidos evita duplicar uma submissão aceita; não promete transações únicas para todos os efeitos externos de uma ferramenta.

## Limites e dados

O limite de durabilidade é a confirmação de salvamento. Uma queda de energia antes de concluir a transação local pode perder a última edição ainda indicada como **Salvando**. Falta de espaço, banco indisponível e permissões revogadas aparecem no status. Faça backup do banco do servidor; a cópia local não substitui backup. A seleção mais recente considera os horários do computador e servidor, que devem estar corretos.

Este recurso cobre o campo e os envios do **chat principal**. Não promete recuperar gravação de voz em andamento, todos os formulários das ferramentas avançadas, sessões de sites externos ou desfazer automaticamente alterações de arquivos. Não retoma um loop da IA sozinho.

Rascunhos não são treinamento nem contexto enviado ao modelo antes do envio. São dados privados fora do Git. A identificação por nome serve para organização: quem pode escolher outro nome na instalação pareada pode abrir esse perfil. Consulte [Perfis e projetos](PERFIS_E_PROJETOS.md).

O cliente Windows **0.3.9** inclui a integração com a recuperação durável. O servidor e o gateway precisam estar atualizados juntos para servir o novo recurso. Feche e abra a aplicação para carregar a interface atual; atualizações dos clientes seguem o [procedimento da rede local](PASSO_A_PASSO_REDE_LOCAL.md).
