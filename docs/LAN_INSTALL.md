# LocalAuthor pela rede local — Windows x64

O computador atual executa a IA e armazena projetos, modelos e conversas. O cliente acessa esse mesmo workspace via HTTPS; não precisa de Python, SDK .NET, banco, GPU ou modelos próprios. O instalador contém .NET e o instalador offline do WebView2. Esta distribuição é para Windows x64; não foi criada versão para macOS, Linux ou Windows ARM.

## Outro computador

### Instalador já conectado

Na versão 0.3.2, use o mesmo instalador conectado em todos os computadores. Na primeira abertura, cadastre a senha única de publicação no servidor. Essa senha será exigida sempre que publicar uma atualização; o instalador não contém a senha. Reinstalações preservam a conexão existente.

O instalador personalizado `Instalar-LocalAuthor-Conectado.exe` já inclui o endereço do servidor, sua identidade TLS e uma autorização própria. Basta copiar o executável para o computador desejado, instalar e abrir LocalAuthor pelo menu Iniciar. A conexão é gravada com DPAPI para o usuário Windows no destino; não é necessário importar arquivo. A instalação pode ocorrer sem acesso ao servidor; a identidade e a autorização são verificadas quando o aplicativo conecta.

Uma reinstalação preserva uma conexão existente. Essa versão é privada e fica fora do repositório e da pasta compartilhável: `%LOCALAPPDATA%\LocalAuthor\lan\private-installers`. Quem possui o executável tem a autorização embutida, mesmo que a configuração instalada seja protegida por DPAPI. Para revogação independente, gere um instalador por computador. Cópias do mesmo instalador compartilham a mesma autorização.

Construção após preparar o payload: `powershell -File scripts/build-paired-installer.ps1 -DeviceName "Meu notebook"`. A compilação cria uma chave independente no servidor e usa intermediários fora do projeto; falha de compilação revoga a autorização recém-criada. Nenhuma chave é escrita no código-fonte. O instalador genérico abaixo permanece disponível sem credenciais.

### Instalador genérico

1. Copie `Instalar-LocalAuthor-Windows-x64.exe` para o outro computador e execute. Instalação por usuário, com atalho no menu Iniciar e entrada em Aplicativos instalados.
2. No servidor, use `Criar conexão` para gerar um arquivo `.localauthor` exclusivo para esse computador. Transfira-o em particular; ele concede acesso ao workspace inteiro.
3. Abra LocalAuthor no computador cliente, clique em **Conectar ao servidor** e importe o arquivo. Não digite o token local da IA.
4. Após importar, a conexão fica protegida por DPAPI para o usuário Windows atual. Remova a cópia de transporte quando não precisar mais dela. `Esquecer conexão` remove o vínculo salvo; `Revogar conexão`, no servidor, invalida a chave imediatamente para próximas requisições.

O instalador experimental não possui assinatura comercial de publicação. Windows pode exibir aviso de editor desconhecido. Compare o SHA-256 com o arquivo de entrega fornecido pelo servidor; não execute cópias de origem desconhecida.

## Servidor

### Um clique neste computador

Abra **LocalAuthor Servidor**, na área de trabalho ou no menu Iniciar. Ele inicia o supervisor existente em segundo plano e mostra **Servidor pronto** quando a API da IA e o gateway HTTPS respondem. Se já estiverem ligados, os processos existentes são preservados. **Abrir minha IA** abre o cliente instalado. Fechar essa janela não desliga os serviços.

O servidor continua configurado para iniciar no login do Windows. Não é necessário abrir PowerShell nem digitar comandos no uso diário. Mantenha o computador ligado e na rede local; o estado verde confirma respostas neste computador, não substitui o teste de acesso no segundo PC ou a configuração de firewall.

O aplicativo é instalado em `%LOCALAPPDATA%\Programs\LocalAuthorServer` e usa a configuração já existente em `LocalAuthor\lan`. Ele não cria outro banco nem move modelos. Em um computador ainda sem servidor configurado, informa que é necessário preparar o servidor primeiro. Não é um instalador completo para um novo servidor.

Construção/instalação para manutenção: `powershell -File scripts/build-server-launcher.ps1 -Install`. O build é Windows x64, .NET 10 self-contained, sem pacote novo ou dependência de WebView2 no painel do servidor. O build LAN passa a gerar esse aplicativo e a instalação do servidor cria os atalhos quando o binário está disponível.

Verificação real: duas aberturas do executável instalado confirmaram API autenticada e certificado HTTPS fixado, preservando os mesmos PIDs antes e depois do fechamento da janela. Evidências: `reports/server-launcher-smoke.json` e `reports/server-launcher-native-1.png`. Não foi reiniciado o Windows nem interrompido o servidor de uso para simular uma partida a frio.

## Abertura com o Windows — cliente 0.3.3

O instalador marca por padrão **Abrir LocalAuthor ao entrar no Windows**. A abertura ocorre no login do usuário Windows, não antes da tela de login. O registro é por usuário e não exige administrador. Se o servidor ou a rede ainda não estiverem prontos, o cliente mantém as tentativas de reconexão.

Uma instalação existente recebe essa configuração ao abrir a versão 0.3.3 no local padrão, inclusive após atualização automática. A preferência de desativar no instalador é preservada; não são alterados os bloqueios definidos pelo Windows em Aplicativos de inicialização. Executáveis de teste e cópias temporárias não se registram. A desinstalação remove a entrada de inicialização.

Referência: [Microsoft — Run e RunOnce](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys).

## Configuração do servidor

- Executar **Liberar rede local** como administrador após esta atualização. Com descoberta automática, as regras permitem somente o executável LocalAuthor.Lan, TCP 8443 e UDP 38443, para clientes da sub-rede local. Não abre roteador, não usa UPnP e não modifica a categoria de rede do Windows.
- O supervisor inicia no login deste usuário Windows e reinicia processos ausentes. Não é serviço de boot anterior ao login. Não encerra nem substitui o backend já aberto.
- Manter o computador ligado e acordado. O cliente atualizado procura o servidor quando o endereço muda; reservar IP no roteador é opcional. Energia não foi alterada automaticamente.
- Backend permanece em `127.0.0.1:8765`; entrada de rede separada em `https://IP-DO-SERVIDOR:8443`.
- Os arquivos de projetos são pastas **do servidor**. Não há sincronização automática das pastas do cliente.

Configuração e dados de acesso ficam em `%LOCALAPPDATA%\LocalAuthor\lan`. Binário e supervisor ficam em `%LOCALAPPDATA%\LocalAuthor\lan-runtime`. Modelos e banco existentes são preservados. Logs não contêm cabeçalhos de autorização nem corpos de requisição.

## Identidade e autorização

Cada dispositivo tem uma chave aleatória independente; o servidor armazena somente seu hash. O cliente confere o SHA-256 e a validade do certificado antes de enviar a chave, e trata erros de certificado no WebView2 apenas para o certificado autorizado. Nenhuma raiz de certificação é adicionada ao Windows. O certificado tem validade de um ano. Ao renovar o certificado, emita novas conexões; não ignore divergência de identidade. A mudança de IP não exige novo certificado ou nova autorização com a descoberta habilitada.

O aplicativo tenta o último endereço e procura o mesmo servidor na rede local se ele não responder. Repete as tentativas enquanto estiver aberto. Cliente e servidor precisam estar na mesma rede, sem isolamento entre dispositivos. Mudar apenas o cliente para outra internet não cria acesso remoto. Consulte `docs/LAN_DISCOVERY.md`.

As conexões desta versão são para **seus dispositivos pessoais**, com acesso ao mesmo workspace e operações da interface. Não são contas de equipe, isolamento por usuário ou permissões por projeto. Não entregue esses arquivos a usuários que não devam ter esse acesso. A chave original de administração local nunca é enviada ao cliente. Os controles existentes de proposta, revisão e sandbox continuam no backend.

O limite é quatro requisições simultâneas no gateway; geração neural continua na fila do backend. Resposta 429 pede nova tentativa. Capacidade em vários computadores reais ainda depende de teste na sua rede.

## Diagnóstico

Clientes a partir da versão 0.3.0 buscam atualizações publicadas no servidor a cada cinco minutos. O aplicativo avisa, aguarda o chat ficar livre, fecha, instala e abre novamente. Existe botão para adiar a reinicialização. Clientes anteriores precisam instalar esta versão uma vez. Veja `LAN_UPDATES.md` incluído no pacote.

- Falha de conexão: conferir servidor ligado, mesma rede, IP, firewall e ausência de isolamento de clientes no Wi-Fi convidado.
- Acesso revogado: gerar nova conexão, importar no cliente.
- Identidade divergente ou certificado vencido: verificar a configuração no servidor, emitir nova conexão; não desabilitar TLS.
- IA desligada: gateway responde 503. O supervisor tenta iniciar o backend a cada 30 segundos.
- Modelo experimental: instalar em outro computador não altera sua capacidade de programação ou seus resultados de treino.
- Desinstalação do cliente preserva dados do servidor e a configuração pessoal. Use Esquecer conexão antes se quiser remover a credencial local.

## Dependências e construção

Nova arquitetura: gateway ASP.NET Core 10, cliente Windows Forms/WebView2 e instalador .NET. SDK WebView2 1.0.4191.47; runtimes .NET incluídos conforme a publicação self-contained; WebView2 offline obtido de Microsoft e assinatura Authenticode verificada. Sem dependência de IA externa.

Construção: `powershell -File scripts/build-lan.ps1`. Fontes oficiais: https://learn.microsoft.com/en-us/dotnet/core/deploying/single-file/overview e https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/evergreen-vs-fixed-version . Atualizações de segurança dos runtimes .NET incluídos exigem reconstruir e redistribuir o cliente. WebView2 Evergreen recebe suas próprias atualizações quando houver conectividade.

Consulte `docs/LAN_VALIDATION.md` para resultados executados e pendências. O acesso em um segundo computador físico só está comprovado depois da conexão nesse equipamento.
