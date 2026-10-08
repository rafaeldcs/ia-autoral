# Organização da interface LocalAuthor — cliente 0.3.6

A interface usa a organização solicitada pelo proprietário, inspirada no Codex, preservando a identidade e as funções reais do LocalAuthor. Não é uma reprodução de todas as capacidades do Codex.

## Onde encontrar cada área

- **Lateral:** nova conversa, projetos e conversas do projeto selecionado. “Pasta do projeto” expande o caminho completo. O botão de recolher amplia o chat; no celular, a lateral abre sobre a página.
- **Centro:** boas-vindas ou histórico; mensagem, formato e modo de resposta ficam na caixa inferior. O aviso abaixo informa o funcionamento do modo selecionado.
- **Cabeçalho:** projeto atual, investigação de site, orientações do projeto e ferramentas.
- **Ferramentas:** links para marketing, modelos locais e ferramentas avançadas, cada um com descrição. Os exercícios de correção foram retirados do chat e ficam nesta janela.
- **Investigação:** painel próprio à direita em telas grandes e tela inteira no celular; Escape recolhe o painel quando não houver outro diálogo aberto.
- **Aplicativo Windows:** “Conexão e atualizações” revela conexão, reconexão, esquecimento e publicação. O status e os avisos de atualização continuam visíveis.

Chat, marketing, modelos e ferramentas avançadas compartilham cores neutras, campos legíveis e hierarquia consistente. Nenhum modelo, corpus, projeto ou credencial é removido por esta alteração. Os modos e as rotas existentes permanecem distintos e explícitos.

Em **Ferramentas → Aparência**, escolha clara, escura ou conforme o sistema. A preferência visual é preservada neste navegador/aplicativo e acompanha as demais áreas do mesmo servidor. Não são armazenados token, mensagens ou senhas com essa preferência. A lista de projetos tem rolagem própria, para manter as conversas acessíveis mesmo com muitas pastas.

## Validação e atualização

`scripts/chat-layout-smoke.py` executa verificações reais de navegador usando apenas projetos temporários e respostas do guia estruturado. Verifica persistência das preferências, histórico, texto inerte, preservação de rascunhos, foco, ferramentas, painel de investigação e dimensões de 320 a 1440 pixels. Não mede a inteligência do modelo.

O CI também executa as suítes existentes de Python, navegação avançada e foundation, e compila o cliente Windows. `scripts/chat-smoke.py` e `scripts/code-repair-chat-smoke.py` mantêm seus testes de modelos reais; agora abrem Ferramentas para acessar os exemplos.

Os arquivos web são servidos pelo servidor; reabrir/reconectar carrega a interface atualizada após atualizar o código do servidor. A barra nativa exige instalar/publicar o cliente 0.3.6, conforme `LAN_UPDATES.md`. Alterações no Git não atualizam automaticamente um servidor em outra máquina.

O conhecimento `INTERFACE_CLARA_PROJETOS_E_CONVERSAS.md` registra os critérios para consulta futura. A revisão de layout é supervisionada; não se apresenta esta alteração de interface como treinamento de pesos.

## Conferência da entrega em 08/10/2026

Foram executados 537 testes Python, 34 verificações do novo layout, os fluxos existentes das telas avançada e foundation, 30 verificações de atualização do cliente e 41 verificações de publicação/HTTPS. A validação de layout inclui 21 projetos, aparência persistente, foco, rascunho e dimensões móveis. Foundation usa dublês nos testes de geração; estes resultados não qualificam pesos reais.

O aplicativo Windows instalado foi atualizado para 0.3.6 e inspecionado. A conferência nele encontrou que o gateway da rede ainda bloqueava as rotas de modelos e dos novos arquivos de aparência. A lista explícita de rotas públicas foi corrigida; seis páginas/arquivos tiveram seu conteúdo conferido por hash no HTTPS real com certificado fixado. APIs privadas continuam exigindo autenticação. O teste de regressão está em `scripts/remote-publication-smoke.py`.

Os ensaios locais usam este computador e servidores temporários. Não foi realizado um ensaio em um segundo computador físico nesta entrega. As propostas da LocalAuthor foram corrigidas durante a revisão; o código da interface e o conhecimento consultável foram implementados e revisados pelo Codex.
