# Atualização automática do cliente Windows

## Instalador único e senha de publicação — 0.3.2

Use o mesmo instalador conectado em todos os computadores. Na primeira abertura conectada, enquanto o servidor ainda não tem senha, o aplicativo pede para criar e confirmar uma senha de 12 a 256 caracteres. O primeiro cadastro feito por um dispositivo pareado define a senha única do servidor. Faça esse cadastro antes de distribuir o instalador a outras pessoas. Se fechar a tela, pode continuar usando a IA; publicar permanece bloqueado até cadastrar a senha.

Em cada publicação, clique em **Publicar atualização…**, selecione o cliente compilado e testado, digite a senha e confirme a revisão. A senha não fica salva no cliente. As antigas permissões de administrador não dispensam a senha. Na reinstalação, a conexão anterior é preservada; a senha pertence ao servidor e não é cadastrada novamente em cada computador.

O banco `%LOCALAPPDATA%\LocalAuthor\lan\publication-auth.sqlite3` armazena somente salt aleatório, hash PBKDF2-HMAC-SHA256 com 600.000 iterações, data do cadastro e contadores de tentativas. Cinco erros por dispositivo provocam bloqueio de um minuto; existe também limite global. Cadastro e bloqueio sobrevivem ao reinício. O cadastro inicial é atômico e não pode sobrescrever uma senha já existente. Não há redefinição remota sem a intervenção do responsável pelo servidor nesta versão.

O transporte usa HTTPS com a identidade do servidor verificada. A senha é enviada somente para autorizar a publicação e não entra nos logs, no pacote ou na auditoria. Os controles de versão crescente, hash, tamanho, executável x64, envio interrompido e revogação do dispositivo continuam ativos. O servidor não executa o arquivo recebido. A tela não compila nem testa código automaticamente.

A partir da versão 0.3.0, o cliente verifica ao abrir e a cada cinco minutos se o servidor publicou uma versão nova. Clientes anteriores precisam instalar esta versão uma vez, pois não possuem atualizador. A reinstalação preserva a conexão salva.

O download usa o HTTPS do servidor pareado, valida seu certificado antes de enviar a autorização e confere SHA-256, tamanho e versão do executável. Não segue redirecionamentos nem aceita endereço de download fornecido no manifesto. Sem servidor acessível ou com download incompleto, o cliente continua na versão atual e tenta novamente depois.

O aplicativo avisa durante 15 segundos antes de reiniciar, com botão para adiar por 30 minutos. Aguarda o chat ficar livre, sem mensagem digitada ou geração em andamento. Formulários editados e telas avançadas impedem a reinicialização automática; volte ao chat e reconecte depois de salvar o trabalho. A seleção visual da conversa pode retornar ao padrão após reinício; projetos e conversas permanecem no servidor.

Um processo auxiliar aguarda a saída voluntária do aplicativo, verifica novamente o arquivo, substitui o executável e guarda a versão anterior ao lado dele. Abre a nova versão e aguarda confirmação de abertura da janela. Se ela não iniciar, tenta restaurar e abrir a anterior, bloqueando novas tentativas daquele mesmo pacote. Essa confirmação verifica a inicialização do aplicativo, não toda sua funcionalidade. A conexão protegida por DPAPI, modelos e dados do servidor não são substituídos.

O registro de cada tentativa fica em `%LOCALAPPDATA%\LocalAuthorClient\updates\<id>\state.json`. O estado `recovery-required` indica que a recuperação automática falhou; reinstale um instalador conhecido. As cópias `.previous` permitem recuperação manual. Arquivos antigos de atualização e backups são mantidos para diagnóstico nesta versão.

## Publicar uma versão no servidor

1. Atualize `Version` no projeto `dotnet/LocalAuthor.Client/LocalAuthor.Client.csproj`. Cada publicação diferente precisa de versão maior.
2. Compile e teste: `powershell -File scripts/build-lan.ps1`, `powershell -File scripts/test-client-update.ps1` e `python scripts/run-tests.py`. A suíte lê a versão atual do projeto do cliente e usa um cliente anterior de teste 0.2.99 e um executável 0.4.0 que falha intencionalmente; ajuste as versões dos cenários quando esses valores deixarem de representar versões anteriores e posteriores à produção.
3. Publique: `powershell -File scripts/lan/Publish-ClientUpdate.ps1`.

O script publica somente o executável público do cliente, sem chave ou instalador personalizado. Pacotes são identificados pelo hash; o manifesto atual é substituído após a cópia e conferência, preservando o manifesto anterior. A publicação fica em `%LOCALAPPDATA%\LocalAuthor\lan\client-releases`. O gateway atualizado atende apenas clientes autenticados, nas mesmas regras de rede das demais APIs. As próximas publicações não exigem reiniciar o gateway.

Esta alteração acrescenta distribuição de versões ao gateway existente e um modo auxiliar ao cliente; não introduz serviços externos. Atualiza o executável do cliente Windows x64 e seu runtime incluído. Não atualiza automaticamente o servidor, o WebView2 ou os pesos da IA. WebView2 Evergreen mantém seu próprio mecanismo de atualização.

Referência técnica: [substituição de arquivo com backup — Microsoft](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.replace?view=net-10.0).
## Correção do cadastro de senha — cliente 0.3.4

O botão **Salvar senha** agora envia JSON UTF-8 com tamanho declarado, compatível com o limite do gateway. Antes, `PostAsJsonAsync` enviava conteúdo sem `Content-Length`, recusado pelo servidor antes de gravar no SQLite. O problema foi reproduzido com o método .NET real em um servidor isolado e corrigido sem alterar a senha do servidor de uso.

Após salvar, o cliente confirma o estado no servidor e mostra **Senha de publicação salva e confirmada no servidor**, com o botão **Abrir minha IA**. Erros preservam os campos. O diálogo explica que a senha serve para publicar atualizações; **Agora não — abrir a IA** permite conversar sem cadastrá-la, mas a publicação continua protegida.

O instalador conectado e a atualização do cliente são versão 0.3.4. Uma janela antiga já aberta precisa ser fechada para a instalação local. O servidor da IA permanece ligado. Teste de regressão: `scripts/password-setup-smoke.py`, com senha aleatória Unicode apenas no servidor temporário; verifica cadastro, hash, recusa de sobrescrita e preservação da senha original. Evidências anteriores e posteriores: `reports/password-setup-before-fix.json` e `reports/password-setup-native.json`.
