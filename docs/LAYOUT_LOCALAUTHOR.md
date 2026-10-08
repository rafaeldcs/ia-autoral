# Organização da interface LocalAuthor — cliente 0.3.7

A interface usa a organização solicitada pelo proprietário, inspirada no Codex, preservando a identidade e as funções reais do LocalAuthor. Não é uma reprodução de todas as capacidades do Codex.

## Onde encontrar cada área

- **Lateral:** nova conversa, projetos e conversas do projeto selecionado. “Pasta do projeto” expande o caminho completo. O botão de recolher amplia o chat; no celular, a lateral abre sobre a página.
- **Centro:** boas-vindas ou histórico; mensagem e modo de resposta ficam na caixa inferior. Texto e código são identificados automaticamente, sem seleção de formato. O aviso abaixo informa o funcionamento do modo selecionado.
- **Cabeçalho:** projeto atual, investigação de site, orientações do projeto e ferramentas.
- **Ferramentas:** links para marketing, modelos locais e ferramentas avançadas, cada um com descrição. Os exercícios de correção foram retirados do chat e ficam nesta janela.
- **Investigação:** painel próprio à direita em telas grandes e tela inteira no celular; Escape recolhe o painel quando não houver outro diálogo aberto.
- **Aplicativo Windows:** sem barra nativa superior. Em Ferramentas, a seção “Este computador” abre conexão, reconexão, esquecimento e publicação. Nas demais telas, use “Configurações do aplicativo” ou `Ctrl + ,`. A descoberta e a atualização funcionam sem abrir configurações; avisos são temporários.

Chat, marketing, modelos e ferramentas avançadas compartilham cores neutras, campos legíveis e hierarquia consistente. Nenhum modelo, corpus, projeto ou credencial é removido por esta alteração. Os modos e as rotas existentes permanecem distintos e explícitos.

Em **Ferramentas → Aparência**, escolha clara, escura ou conforme o sistema. A preferência visual é preservada neste navegador/aplicativo e acompanha as demais áreas do mesmo servidor. Não são armazenados token, mensagens ou senhas com essa preferência. A lista de projetos tem rolagem própria, para manter as conversas acessíveis mesmo com muitas pastas.

## Validação e atualização

A caixa de mensagem tem uma linha de controles e cresce automaticamente conforme o conteúdo. O contador aparece próximo ao limite; o botão de envio tem nome acessível e fica desabilitado quando a mensagem está vazia. Enter mantém uma nova linha, e Ctrl + Enter envia. A identificação automática usa sinais de código e JSON no servidor, com uma indicação visual correspondente no editor. O texto original é salvo sem alterar espaços, comentários, aspas, acentos ou quebras de linha; mensagens continuam sendo renderizadas como texto inerte. A detecção é conservadora e não garante reconhecer toda linguagem ou todo trecho ambíguo.

O campo de formato não é exibido. Um identificador oculto foi preservado para compatibilidade com clientes instalados que restauram rascunhos; o chat web envia sempre `input_format=auto`. A API também identifica o formato quando esse campo é omitido, mantendo suporte às indicações explícitas de clientes anteriores. Na área Modelos locais, conversar e criar imagem permanecem funções distintas; analisar código não exige mais um modo separado.

`scripts/chat-layout-smoke.py` executa verificações reais de navegador usando apenas projetos temporários e respostas do guia estruturado. Verifica persistência das preferências, histórico, texto inerte, preservação de rascunhos, foco, ferramentas, painel de investigação e dimensões de 320 a 1440 pixels. Não mede a inteligência do modelo.

O CI também executa as suítes existentes de Python, navegação avançada e foundation, e compila o cliente Windows. `scripts/chat-smoke.py` e `scripts/code-repair-chat-smoke.py` mantêm seus testes de modelos reais; agora abrem Ferramentas para acessar os exemplos.

Os arquivos web são servidos pelo servidor; reabrir/reconectar carrega a interface atualizada após atualizar o código do servidor. A retirada da barra nativa exige instalar/publicar o cliente 0.3.7, conforme `LAN_UPDATES.md`. Alterações no Git não atualizam automaticamente um servidor em outra máquina.

O conhecimento `INTERFACE_CLARA_PROJETOS_E_CONVERSAS.md` registra os critérios para consulta futura. A revisão de layout é supervisionada; não se apresenta esta alteração de interface como treinamento de pesos.

## Conferência da entrega em 08/10/2026

Foram executados 537 testes Python, 34 verificações do novo layout, os fluxos existentes das telas avançada e foundation, 30 verificações de atualização do cliente e 41 verificações de publicação/HTTPS. A validação de layout inclui 21 projetos, aparência persistente, foco, rascunho e dimensões móveis. Foundation usa dublês nos testes de geração; estes resultados não qualificam pesos reais.

O aplicativo Windows instalado foi atualizado para 0.3.6 e inspecionado. A conferência nele encontrou que o gateway da rede ainda bloqueava as rotas de modelos e dos novos arquivos de aparência. A lista explícita de rotas públicas foi corrigida; seis páginas/arquivos tiveram seu conteúdo conferido por hash no HTTPS real com certificado fixado. APIs privadas continuam exigindo autenticação. O teste de regressão está em `scripts/remote-publication-smoke.py`.

Os ensaios locais usam este computador e servidores temporários. Não foi realizado um ensaio em um segundo computador físico nesta entrega. As propostas da LocalAuthor foram corrigidas durante a revisão; o código da interface e o conhecimento consultável foram implementados e revisados pelo Codex.

## Complemento — conexão automática e cliente 0.3.7

Foram executadas 15 verificações de descoberta UDP/HTTPS com IP antigo e certificado fixado, 16 verificações de inicialização nativa e 32 de atualização, além da suíte Python com 537 testes aprovados. A inicialização nativa confere ausência da barra, botão de configurações dentro das ferramentas, abertura real do menu e rejeição de mensagens desconhecidas. A atualização confere aparência salva sem bloquear o reinício, rascunho preservado, substituição verificada e rollback. Os instaladores público e privado são compilados com o cliente 0.3.7; o teste do privado verifica configuração automática criptografada e preservação do vínculo na reinstalação.

O conhecimento `CLIENTE_AUTOMATICO_NA_REDE_LOCAL.md` registra os comportamentos para consulta central. A LocalAuthor propôs casos de teste, recebeu correções baseadas nos ensaios reais e reformulou cinco resultados esperados. Isso não é execução autônoma dos testes pelo modelo nem alteração de pesos. Não houve reinício físico do Windows, troca física de Wi-Fi ou teste em segundo computador nesta rodada.
## Conversa por voz

O microfone do compositor abre o início explícito da conversa por voz. O servidor transcreve com Whisper isolado e o cliente lê com uma voz local em português. Captura visível, pausas, cancelamento, áudio descartado e limites estão em [CONVERSA_POR_VOZ.md](CONVERSA_POR_VOZ.md). O modo textual Foundation também está disponível no chat principal. A sessão bloqueia reinício automático e mudança de projeto até ser encerrada.
