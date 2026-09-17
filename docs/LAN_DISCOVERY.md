# Descoberta automática do servidor

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
