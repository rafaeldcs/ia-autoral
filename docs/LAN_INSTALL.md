# LocalAuthor pela rede local — Windows x64

O computador atual executa a IA e armazena projetos, modelos e conversas. O cliente acessa esse mesmo workspace via HTTPS; não precisa de Python, SDK .NET, banco, GPU ou modelos próprios. O instalador contém .NET e o instalador offline do WebView2. Esta distribuição é para Windows x64; não foi criada versão para macOS, Linux ou Windows ARM.

## Outro computador

1. Copie `Instalar-LocalAuthor-Windows-x64.exe` para o outro computador e execute. Instalação por usuário, com atalho no menu Iniciar e entrada em Aplicativos instalados.
2. No servidor, use `Criar conexão` para gerar um arquivo `.localauthor` exclusivo para esse computador. Transfira-o em particular; ele concede acesso ao workspace inteiro.
3. Abra LocalAuthor no computador cliente, clique em **Conectar ao servidor** e importe o arquivo. Não digite o token local da IA.
4. Após importar, a conexão fica protegida por DPAPI para o usuário Windows atual. Remova a cópia de transporte quando não precisar mais dela. `Esquecer conexão` remove o vínculo salvo; `Revogar conexão`, no servidor, invalida a chave imediatamente para próximas requisições.

O instalador experimental não possui assinatura comercial de publicação. Windows pode exibir aviso de editor desconhecido. Compare o SHA-256 com o arquivo de entrega fornecido pelo servidor; não execute cópias de origem desconhecida.

## Servidor

- Executar **Liberar rede local** como administrador uma vez. A regra permite somente o executável LocalAuthor.Lan, TCP 8443, IP/interface configurados e clientes da mesma sub-rede. Não abre roteador, não usa UPnP e não modifica a categoria de rede do Windows.
- O supervisor inicia no login deste usuário Windows e reinicia processos ausentes. Não é serviço de boot anterior ao login. Não encerra nem substitui o backend já aberto.
- Manter o computador ligado e acordado. Reserve o IP no DHCP do roteador para evitar mudança de endereço; reserva e energia não foram alteradas automaticamente.
- Backend permanece em `127.0.0.1:8765`; entrada de rede separada em `https://IP-DO-SERVIDOR:8443`.
- Os arquivos de projetos são pastas **do servidor**. Não há sincronização automática das pastas do cliente.

Configuração e dados de acesso ficam em `%LOCALAPPDATA%\LocalAuthor\lan`. Binário e supervisor ficam em `%LOCALAPPDATA%\LocalAuthor\lan-runtime`. Modelos e banco existentes são preservados. Logs não contêm cabeçalhos de autorização nem corpos de requisição.

## Identidade e autorização

Cada dispositivo tem uma chave aleatória independente; o servidor armazena somente seu hash. O cliente confere o SHA-256 e a validade do certificado antes de enviar a chave, e trata erros de certificado no WebView2 apenas para o certificado autorizado. Nenhuma raiz de certificação é adicionada ao Windows. O certificado tem validade de um ano. Ao renovar certificado ou mudar o IP, atualize a configuração e emita novos arquivos de conexão; não ignore divergência de identidade.

As conexões desta versão são para **seus dispositivos pessoais**, com acesso ao mesmo workspace e operações da interface. Não são contas de equipe, isolamento por usuário ou permissões por projeto. Não entregue esses arquivos a usuários que não devam ter esse acesso. A chave original de administração local nunca é enviada ao cliente. Os controles existentes de proposta, revisão e sandbox continuam no backend.

O limite é quatro requisições simultâneas no gateway; geração neural continua na fila do backend. Resposta 429 pede nova tentativa. Capacidade em vários computadores reais ainda depende de teste na sua rede.

## Diagnóstico

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
