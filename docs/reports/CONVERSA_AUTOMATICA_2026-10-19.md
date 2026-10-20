# Chat automático e instalador — 19/10/2026

O pedido de instalador estava sendo encaminhado ao modo fixo de orientação de projeto, produzindo um roteiro sem relação com a pergunta. A correção remove a escolha visível de modo e introduz seleção automática de recursos, com contexto da conversa e controles existentes. O [guia de uso](../CONVERSA_AUTOMATICA.md) descreve os comportamentos e limites.

## Entrega

- O chat consulta o catálogo do instalador publicado, responde com a versão real e oferece **Baixar instalador**. Pacote ausente ou corrompido não produz um link fictício. A conexão embutida não entra no contexto do modelo.
- Perguntas comuns seguem para o modelo local com histórico, fontes e preferências do projeto. Na ausência de modelo, a aplicação apresenta fontes disponíveis ou explica o recurso ausente; não simula conversa com um roteiro de Scrum/Kanban.
- Pedidos explícitos de leitura de fontes, pesquisa com endereço ou investigação de telas selecionam os recursos correspondentes. A aplicação pede o endereço quando falta escopo. Pesquisa respeita política de rede/offline, cache e fontes do pedido; não adiciona busca irrestrita na internet.
- O cliente Windows **0.3.10** salva o instalador pelo canal autenticado com certificado validado, tamanho e SHA-256 conferidos e substituição do destino só após verificação. O comando do navegador não aceita caminho, credencial ou URL arbitrária. O arquivo não é executado automaticamente.
- O gateway transmite o anexo e os metadados de integridade. O operador publica o pacote revisado com o utilitário local; modelos, conexões, instaladores e dados continuam fora do Git.
- Rascunhos antigos sem envio usam a escolha automática. Pedidos aceitos mantêm conteúdo e identificador originais. Foi corrigida a limpeza do texto ao concluir pedidos de modos antigos e conversas por voz, além da disputa entre troca de projeto e edição durante o salvamento.

## Validação local

- **683 testes Python: 680 aprovados, zero falhas/erros; três testes de links simbólicos indisponíveis por falta de privilégio do Windows.** São 19 casos novos para intenções, contexto, pacote real no armazenamento, corrupção, ausência, autenticação, HTTP e respostas sem pesquisa fictícia.
- **13 verificações no navegador** para seleção automática, pedido original com erro de digitação, download autenticado com bytes exatos, geração, pesquisa, conteúdo inerte, rascunhos e pedidos legados, bloqueio durante navegação e telas de 390/320 pixels. Geração e pesquisa nesse ensaio usam dublês explícitos.
- **20 verificações de recuperação**, mantendo fechamento/reabertura, queda real do renderizador descartável, edição offline, conflitos e respostas perdidas sem repetir tarefas aceitas.
- **35 verificações nativas**, incluindo download do instalador pelo fluxo real do cliente com TLS e perfil escolhido pelo formulário, atualização/reabertura, rascunho preservado e recuperação da versão anterior após falha.
- **65 verificações de layout**, **19 de voz**, testes de perfis, marketing, leads e interface foundation aprovados após as correções. Áudio e geração dos ensaios de interface usam dublês declarados.
- Gateway HTTPS: **11 verificações**. Fachada .NET: **16 verificações**. Cliente, gateway e instalador compilados localmente sem restaurar/baixar novos modelos.
- Instalador conectado 0.3.10: **15 arquivos extraídos com integridade**, configuração protegida por DPAPI e preservada na segunda configuração.

## Servidor em uso

Foi feito backup SQLite íntegro e reinício cooperativo, preservando **13 projetos e 2 perfis**. O pedido original foi executado no chat da própria LocalAuthor, em uma conversa de QA identificada, sem cadastrar outra pessoa. A resposta apresentou o instalador publicado 0.3.10 e a ação de download. O pacote completo de **376.387.612 bytes** foi transmitido pelo HTTPS autenticado e seu SHA-256 conferido.

Uma pergunta comum foi executada em seguida pela rota automática e respondida pelo modelo real local `gguf-docker`, com origem `foundation_text`. Isso confirma a chamada desse recurso no servidor; uma resposta não qualifica inteligência geral nem qualquer outra capacidade. Conversa completa, metadados, relatórios, imagens, recibos e artefatos permanecem privados.

A mudança é de orquestração e interface, sem treino dos pesos. Não concede publicação, deploy, execução arbitrária ou acesso a outros projetos. Não houve ensaio em segundo computador físico. O CI deve ser conferido no SHA exato publicado desta revisão.
