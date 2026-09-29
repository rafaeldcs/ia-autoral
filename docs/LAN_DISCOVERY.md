# Descoberta automática do servidor

## Uso na própria máquina servidor (cliente 0.3.5)

Ao abrir pelo atalho ou pela inicialização do Windows, o cliente reconhece o servidor instalado no perfil Windows atual. Se ainda não houver conexão, cadastra um dispositivo local e guarda a credencial com DPAPI, sem pedir que o usuário crie ou importe um arquivo. Se a conexão já existir, preserva sua identidade e permissões. Uma conexão salva para outro servidor continua sendo respeitada; acesso revogado ou credencial corrompida não gera outra credencial silenciosamente.

Com `AutoDiscover=true`, esse acesso usa HTTPS em `127.0.0.1`, mantendo a autenticação e a verificação do certificado. O gateway atualizado aceita loopback apenas quando ambas as pontas são loopback. Assim, o uso no servidor não depende do endereço do Wi-Fi. Outros computadores continuam usando a descoberta autenticada na rede local.

O cliente inicia o supervisor instalado, aguarda até 60 segundos pela saúde do servidor e tenta novamente automaticamente se a inicialização demorar. Isso resolve a ordem variável em que o Windows abre cliente e servidor. Não instala um servidor novo em computadores clientes nem altera projetos, modelos ou conversas. Não há nova dependência de infraestrutura; esta mudança usa o supervisor, o gateway e o armazenamento protegido existentes. Atualize **cliente e gateway** para habilitar o acesso local.

Teste reproduzível: `python scripts/local-server-startup-smoke.py`. Usa servidor e perfil temporários, abre o chat nativo sem conexão importada e verifica reutilização, criptografia, revogação, corrupção e instalação incompleta. Não substitui um reinício físico do Windows.

## Uso em outros computadores

O cliente atualizado tenta primeiro o endereço salvo. Se ele não responder, envia uma consulta UDP na porta 38443 às interfaces IPv4 privadas disponíveis. O servidor responde apenas a dispositivos da sua sub-rede. A resposta indica a porta HTTPS; o endereço vem da origem do pacote. Não existe serviço externo de descoberta nem varredura de portas.

A consulta contém a identidade pública do certificado e um identificador aleatório da tentativa. Nenhuma chave de acesso é transmitida por UDP. Antes de enviar a autorização por HTTPS, o cliente verifica o certificado exato e sua validade. Respostas de outra identidade, identificadores de tentativa incorretos e certificados diferentes são rejeitados. Uma chave revogada continua revogada após descoberta.

O cliente verifica a conexão a cada 15 segundos e reage à mudança de endereço de rede. Ao encontrar o servidor, salva o novo endereço para o usuário Windows. Durante a reconexão, tenta preservar o texto ainda não enviado no chat e a seleção de projeto e conversa, se continuarem disponíveis. Isso não substitui salvar alterações em outras telas.

## Preparação

- No servidor, `AutoDiscover=true` habilita escuta nas interfaces atuais; a autorização de rede usa o endereço local e a sub-rede atuais de cada requisição.
- Execute **Liberar rede local (Administrador)** após atualizar. São necessárias as regras TCP 8443 e UDP 38443 para o executável registrado, restritas à sub-rede local.
- Instale o cliente atualizado. A reinstalação preserva a conexão existente; o instalador conectado configura automaticamente uma instalação nova.
- Mantenha servidor ligado, acordado e com a sessão que executa o supervisor iniciada.

## Limites

Cliente e servidor devem estar na mesma rede local. Se somente um deles mudar para outra internet, a descoberta não atravessa a internet. VPN e acesso remoto não estão configurados. Redes de convidados, isolamento Wi-Fi e bloqueios de broadcast podem impedir a descoberta. Esta versão usa IPv4 privado; não implementa descoberta IPv6.

A identidade acompanha o certificado, e não o IP. Renovação ou substituição do certificado exige atualizar o vínculo do cliente. Não aceite automaticamente uma identidade desconhecida.

## Verificação reproduzível

`dotnet run --project dotnet/LocalAuthor.DiscoveryChecks -c Release --no-launch-profile` exercita UDP e HTTPS reais, simulando endereço antigo e verificando identidade, revogação e mensagens inválidas. A execução automatizada na mesma máquina não comprova uma troca física de Wi-Fi ou a conexão em outro computador.
