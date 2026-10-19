# Perfis somente por nome — revisão do fluxo em 19/10/2026

Esta revisão atende à alteração explícita do proprietário: **não pedir usuário nem senha, identificar o perfil pelo nome informado**. Substitui o fluxo de autenticação pessoal da entrega inicial. O [guia atual](../PERFIS_E_PROJETOS.md) descreve o uso.

## Resultado

A entrada pergunta quem está usando a LocalAuthor. Um nome novo cria um espaço de pessoa da equipe; um nome existente abre o mesmo perfil. Há uma lista de nomes já cadastrados e a ação **Meu perfil → Trocar perfil**. O primeiro perfil, criado no servidor, organiza os projetos e históricos antigos e pode preparar outros nomes antecipadamente.

O nome é normalizado para comparação, respeitando maiúsculas/minúsculas e espaços repetidos, sem duplicar um perfil acidentalmente. Desativação e nomes duplicados em registros antigos produzem mensagens explícitas. Perfis com senha da primeira versão podem ser selecionados pelo nome, preservando seus IDs, projetos e histórico. Campos antigos permanecem no banco e em rotas de compatibilidade; a interface não pede essas credenciais, e novos perfis não têm senha.

Os projetos continuam organizados por perfil selecionado, com pastas separadas, autoria, filtro de conversas e compartilhamento de leitura/edição. **Isso não garante sigilo entre pessoas: qualquer dispositivo pareado pode escolher o nome de outro perfil, inclusive um administrador.** As funções administrativas e as permissões por projeto organizam o trabalho; não autenticam a pessoa. Esta consequência aparece na tela de entrada, no painel de perfil e no guia.

O pareamento de dispositivo, TLS, validação do certificado e a senha específica de publicação de atualizações permanecem separados. A senha de publicação não é uma senha de entrada no perfil. Não foram adicionadas exceções para dispositivos não pareados.

## Validação

- Suíte Windows/Python 3.14.7: **649 testes, 646 aprovados, zero falhas/erros e três casos de links simbólicos não executados por falta do privilégio do Windows**. São 21 testes de identidade/compatibilidade, incluindo a seleção intencional de outro nome sem senha, demonstrando que o recurso é organizacional.
- Interface por nome: **18 verificações**, sem campos de usuário/senha no perfil, com criação, seleção de um nome existente, troca em várias abas, projetos por espaço, compartilhamento, desativação e layout 320/390.
- Gateway HTTPS real: **10 verificações**, com dois dispositivos lógicos, cookies separados, APIs no perfil selecionado, cabeçalhos de origem controlados pelo gateway e dispositivo obrigatório.
- Atualizador nativo: **33 verificações**, preenchendo os formulários reais por nome, com atualização/reabertura, rascunho preservado, integridade, versão, certificado, revogação e recuperação da versão anterior.
- Fachada .NET: **16 verificações** com criação/seleção por nome, cookies, troca de perfil e indisponibilidade do backend.
- Interfaces existentes: avançada, layout do chat, foundation, voz, marketing e leads executados novamente com a seleção por nome. Geração e áudio usam dublês explícitos onde indicado; esses ensaios não qualificam os modelos.
- Instalador conectado 0.3.8: 13 arquivos extraídos com integridade, configuração protegida por DPAPI e preservação da conexão existente.
- Servidor real: encerramento cooperativo, backup íntegro e **13 projetos preservados**. A interface em execução foi conferida com zero campos de usuário/senha na seleção de perfil. Nenhuma pessoa real foi criada automaticamente pelo executor.

O teste foundation revelou que o helper esperava visibilidade do controle de perfil dentro de um menu recolhido no celular, mesmo com o perfil carregado. A espera agora verifica a inicialização do controle; a seleção efetiva continua sendo feita pelo formulário real. O teste também aguarda a navegação de saída terminar. Nenhuma autenticação, política de projeto ou asserção de conteúdo foi contornada para corrigir essa espera.

## Distribuição e limites

O servidor foi atualizado e o instalador privado foi renovado com o guia corrigido. O executável cliente continua em 0.3.8, pois a nova seleção é servida pelo servidor; esse cliente já preserva contexto de perfil em rascunhos e é distribuído pelo canal local. Nenhuma atualização foi forçada sobre uma janela do usuário com possível trabalho não salvo.

Relatórios completos, imagens, bancos de teste, backups e instaladores permanecem privados e fora do Git. O CI deve ser conferido no commit exato desta revisão; o resultado da revisão anterior não substitui essa conferência. Um segundo computador físico não foi testado. Não houve novo treino ou mudança nos pesos da IA; a função pontual de permissões anteriormente proposta e avaliada pela LocalAuthor continua com a mesma implementação.
