# Entrega da rede local — 17/09/2026

## Instalação local e acesso direto — 0.3.4

A instalação principal foi atualizada de 0.3.3 para 0.3.4 pelo instalador conectado. A configuração DPAPI existente foi preservada byte a byte. O executável instalado abriu o chat no teste nativo com conexão salva, autenticação e certificado verificados, sem seleção de arquivo. Evidências: `reports/password-fix-local-install.json` e `reports/saved-connection-local-check.json`.

A Área de Trabalho deste computador passou a ter um único atalho de uso do LocalAuthor, apontando para `%LOCALAPPDATA%\Programs\LocalAuthorClient\LocalAuthor.Client.exe`, sem argumentos de teste. O servidor continua acessível pelo menu Iniciar. Materiais de entrega e relatórios antigos foram retirados da Área de Trabalho e preservados em `%LOCALAPPDATA%\LocalAuthor\desktop-archive\20260917`; projetos e modelos não foram movidos. O instalador conectado atual continua em `%LOCALAPPDATA%\LocalAuthor\lan\private-installers`, fora do Git.

Esta verificação confirma o acesso automático nesta máquina. A descoberta requer o vínculo autorizado já fornecido pelo instalador e a presença do servidor na mesma rede; não comprova operação em outro computador físico ou em outra rede pela internet.

## Inicialização com Windows — 0.3.3

O instalador único configura por padrão a abertura do cliente no login do usuário atual, via HKCU Run, com caminho entre aspas e argumento `--startup`. O cliente atualizado registra essa preferência na instalação padrão quando ainda não há escolha anterior; executáveis temporários não se registram. A opção desmarcada no instalador é preservada nas atualizações e a desinstalação remove a entrada. Nenhuma política de inicialização bloqueada pelo Windows é alterada.

**4 verificações de inicialização aprovadas** em `reports/startup-smoke.json`: registro em chave isolada, preservação da escolha de desativar, preservação de entradas de outros aplicativos e execução real do comando registrado, a partir de um caminho com espaços, abrindo o chat nativo. Passaram também **30 verificações de atualização**, **6 de instalação** e **150 testes Python**, com 3 testes de symlink indisponíveis por privilégio do Windows.

O cliente foi instalado neste computador em `%LOCALAPPDATA%\Programs\LocalAuthorClient`; a conexão foi configurada e a entrada real de inicialização foi conferida. Relatório `reports/startup-local-install.json`. A versão 0.3.3 foi publicada para os clientes. Não foi realizado reboot/logout; o teste executou o comando de inicialização diretamente.

## Instalador único e senha central — 0.3.2

A versão 0.3.2 substitui a divisão entre instaladores de cliente e administrador. Todo dispositivo pareado pode abrir a tela de publicação, mas deve apresentar a senha central em cada envio. As permissões antigas de `publisher` não a dispensam. O primeiro cadastro cria um único registro em `publication-auth.sqlite3`, com salt de 32 bytes, PBKDF2-HMAC-SHA256 de 600.000 iterações e hash de 32 bytes; a senha original não é persistida. O banco real foi deixado aguardando a senha escolhida pelo usuário.

**34 verificações de senha e publicação aprovadas**: cadastro simultâneo com vencedor único, impossibilidade de sobrescrever cadastro, hash conferido independentemente por Python, bloqueio sem senha inclusive para administrador antigo, publicação nativa com senha, tentativas incorretas, persistência após reinício, expiração do bloqueio e regressões de upload/revogação. Relatório `reports/remote-publication-smoke.json`. A primeira execução da suíte encontrou um handle SQLite do próprio teste não fechado; a conexão foi fechada explicitamente e a execução final passou.

Também passaram **30 verificações de atualização automática**, **23 de integração LAN**, **6 do instalador único** e **150 testes Python**, com 3 testes de symlink indisponíveis por privilégio do Windows. A versão foi publicada localmente pelo operador do servidor para deixar o cadastro real vazio; sua distribuição HTTPS foi verificada. Não houve teste em segundo computador físico. O hash da senha é mantido no servidor; modelos e backend existentes foram preservados.

## Publicação remota — cliente 0.3.1

Adicionado botão nativo **Publicar atualização**, autorizado pela permissão `publisher` no cadastro do servidor. Dispositivos legados permanecem clientes comuns. A tela mostra executável, versão, tamanho e hash e solicita confirmação da revisão. O gateway recebe o binário por HTTPS, valida limites e metadados sem executá-lo, serializa publicações e verifica novamente a autorização antes de ativar a versão. A permissão não pode ser concedida pela API do cliente.

**22 verificações aprovadas** em `reports/remote-publication-smoke.json`, incluindo interface nativa conforme permissão, publicação pelo código do cliente, isolamento de papéis, metadados inválidos, interrupção e limpeza do envio, idempotência, bloqueio de downgrade, auditoria e revogação durante upload. **8 verificações do instalador administrador aprovadas**, incluindo ativação sobre conexão do mesmo servidor com backup e recusa de substituição de outro servidor. Instalador comum: **6 verificações aprovadas**.

A versão 0.3.1 foi publicada no gateway real usando o fluxo HTTPS do cliente administrativo; o download autenticado e seu hash foram conferidos. Isso foi feito nesta máquina, pelo endereço LAN, e não comprova acesso a partir de outro computador físico. Relatórios: `reports/remote-production-publication.json` e `reports/published-client-update.json`.

Regressão desta versão: **30 verificações de atualização**, **23 de integração LAN**, **12 de descoberta** e **150 testes Python aprovados**, com 3 testes de symlink indisponíveis por privilégio do Windows. Backend e modelos existentes preservados. Reaplicar o atalho administrativo de firewall após a troca do executável do gateway continua necessário.

## Atualização automática do cliente 0.3.0

Implementada distribuição autenticada de versões pelo gateway, com download fixo no servidor pareado, validação de tamanho/SHA-256/versão, substituição com backup e reabertura automática. A versão anterior é recuperada se a nova não confirmar a abertura. Rascunhos e geração em andamento adiam o reinício; o usuário recebe aviso de 15 segundos e pode adiar por 30 minutos.

**30 verificações de atualização aprovadas** em `reports/client-update-smoke.json`: publicação idempotente, recusa de downgrade, autenticação, bloqueio de caminhos indevidos, rascunho preservado na janela nativa, encerramento/reabertura reais, binário instalado e backup conferidos, corrupção/versão incorreta/identidade divergente recusadas, recuperação com reabertura real da versão anterior e revogação. Os testes usam servidor e pastas temporárias, com cliente anterior 0.2.99 e executável de falha 0.4.0. Eles não representam um teste entre dois computadores físicos.

Regressão: **23 verificações de integração LAN**, **6 do instalador conectado** e **150 testes Python aprovados**, com 3 testes de symlink indisponíveis por privilégio do Windows. Guia de operação: `docs/LAN_UPDATES.md`. Clientes sem atualizador precisam instalar esta versão uma vez; atualizações futuras exigem compilar, testar e publicar uma versão maior no servidor.

Durante a construção da suíte, foi corrigido o encerramento do backend temporário (`Application.close`) e removida a dependência do publicador em `Get-FileHash`, indisponível no ambiente de subprocesso usado pelo teste. A execução final passou; resets de conexão do backend temporário durante encerramento dos navegadores não alteraram as verificações.

## Atualização: descoberta automática

Gateway em execução com `AutoDiscover=true`, HTTPS TCP 8443 e descoberta UDP 38443. A escuta acompanha interfaces IPv4; cada requisição continua restrita às sub-redes privadas conectadas. O backend existente foi preservado. O firewall deve ser atualizado pelo atalho administrativo para permitir ambas as portas ao executável atual.

Validação desta atualização: **12 verificações UDP/TLS aprovadas**, **23 de integração aprovadas**, **6 do instalador conectado aprovadas** e **150 testes Python aprovados**, com 3 testes de symlink indisponíveis por privilégio do Windows. Um teste adicional abriu o chat no cliente nativo partindo do endereço obsoleto `https://127.0.0.2:8443`, localizando e autenticando o servidor real automaticamente. Relatórios: `reports/discovery-checks.json`, `reports/discovery-client-smoke.json`, `reports/discovery-core-tests.json`, `reports/lan-smoke.json` e `reports/paired-installer-smoke.json`.

O instalador conectado foi reconstruído com o cliente atualizado e mantém a configuração automática sem importação. Não foi realizada troca física de Wi-Fi, reboot nem teste em segundo computador. Redes distintas pela internet continuam exigindo uma solução de acesso remoto, não incluída nesta entrega. Detalhes em `docs/LAN_DISCOVERY.md`.

## Instalador pré-configurado

A variante privada do instalador provisiona `connection.bin` com DPAPI no computador de destino. O cliente carrega essa conexão ao abrir. A validação da conexão é compartilhada pelo cliente e instalador; a verificação de identidade TLS e autenticação continua obrigatória. Configurações existentes são preservadas. Nenhuma mudança no gateway em execução foi necessária.

`scripts/paired-installer-smoke.py`: **6 verificações aprovadas** — provisionamento sem seleção de arquivo, proteção DPAPI com recuperação correta, preservação na reinstalação, abertura real do chat pelo cliente nativo usando somente configuração salva, validação de TLS/autenticação e ausência da autorização no instalador genérico. O teste usou configuração de cliente temporária, fez somente consultas ao servidor existente e não equivale à validação em segundo computador físico.

Regressão Python: **150 aprovados e 3 testes de symlink indisponíveis**, 153 no total, em `reports/paired-core-tests.json`. Resultado do novo fluxo: `reports/paired-installer-smoke.json`. O instalador personalizado e intermediários com a autorização ficam em `%LOCALAPPDATA%\LocalAuthor\lan\private-installers`, fora do Git. A revogação identifica cada instalador; reutilizar a mesma cópia em vários computadores compartilha a autorização.

## Resultado

Criados três executáveis .NET 10.0.9 / Windows x64: gateway HTTPS, cliente Windows Forms/WebView2 e instalador com payload verificado por SHA-256. Build final sem erros. Removida a referência WPF não utilizada que produzia aviso no pacote WebView2.

Na entrega inicial, o gateway usava exclusivamente **192.168.1.240:8443**, com clientes restritos a **192.168.1.0/24**. A atualização acima substitui essa configuração fixa pela descoberta nas interfaces atuais. O backend existente continua em **127.0.0.1:8765**. Um teste autenticado com validação TLS no IP da rede respondeu com sucesso a partir deste computador.

Não houve substituição dos pesos, alteração do banco ou reinício do backend existente. Guias Python novos de rodadas anteriores ainda dependem de reinício normal do backend. O supervisor foi registrado em HKCU Run: inicia após login deste usuário, verifica a cada 30 segundos e inicia processos ausentes; não é serviço de boot.

## Testes executados

`scripts/lan-smoke.py`: **23 verificações de integração**, servidor e projeto temporários:

- Autenticação HTTPS real, UI e conversa pelo gateway.
- Chave ausente/incorreta recusada; token original do backend não serve como chave LAN.
- Host, Origin e requisição cross-site indevidos recusados; OPTIONS sem CORS.
- Certificado desconhecido recusado pelo TLS padrão.
- Geração real do modelo próprio através da fila e gateway, com resposta esperada.
- Chave do dispositivo bloqueada quando enviada literalmente como mensagem.
- Extração do instalador e conferência de hashes de todos os arquivos do payload.
- Execução do cliente extraído, verificação do certificado, login automático e abertura do chat no WebView2 real.
- Certificado com pin divergente recusado pelo aplicativo.
- Revogação sem reinício e preservação do acesso do segundo dispositivo.
- Backend encerrado retorna 503 após drenagem das conexões keep-alive.

Evidências: `reports/lan-smoke.json`, `reports/lan-desktop.json`, `reports/lan-desktop.png`. Projetos e chaves destes testes são temporários. O Windows já tinha WebView2: **instalação do runtime em máquina limpa não foi exercitada**, embora o instalador offline assinado esteja incluído. A extração foi testada em pasta temporária; criação do atalho/menu e desinstalação do cliente devem ser confirmadas na instalação pelo usuário. O instalador customizado não tem assinatura comercial.

`scripts/run-tests.py --allow-unavailable-symlinks --report reports/lan-core-tests.json`: **150 aprovados, zero falhas e três testes de symlink indisponíveis por privilégio do Windows**, 153 no total. Não representam cobertura integral do Windows.

O teste inicial tentou verificar backend desligado antes do fim das conexões keep-alive. Foi corrigido para aguardar o timeout real de 15 segundos; o servidor não foi alterado para esconder o resultado. O backend temporário pode registrar reset de conexão 10054 ao fechar o navegador, sem falha das verificações.

## Pendências externas concretas

1. **Firewall:** sessão sem elevação e Wi-Fi classificado como público. Executar o atalho `Liberar rede local (Administrador)` no servidor. Ele permite TCP 8443 e UDP 38443 somente ao executável registrado e à sub-rede local, sem abrir roteador ou mudar perfil de rede.
2. **Outro computador físico:** instalar o cliente pelo instalador conectado para concluir o teste real entre máquinas. O teste no IP LAN a partir deste PC não equivale a esse teste.
3. **Operação:** manter o servidor acordado. Reserva de IP é opcional com descoberta ativa. Retorno automático após novo login não foi validado por reboot nesta rodada.
4. **Equipe:** os dispositivos acessam o mesmo workspace pessoal. Não foi implementado isolamento de contas de funcionários ou RBAC por projeto.

O download/instalação do compilador Inno Setup foi rejeitado pela revisão automática com mensagem “blocked by policy”. O bloqueio não foi contornado: a ferramenta não foi instalada ou executada. O instalador entregue foi criado em código próprio com o SDK .NET já existente. O instalador Microsoft WebView2 foi somente baixado, teve assinatura verificada e foi empacotado para uso quando necessário.
