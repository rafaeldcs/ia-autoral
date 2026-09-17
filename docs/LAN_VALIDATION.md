# Entrega da rede local — 17/09/2026

## Resultado

Criados três executáveis .NET 10.0.9 / Windows x64: gateway HTTPS, cliente Windows Forms/WebView2 e instalador com payload verificado por SHA-256. Build final sem erros. Removida a referência WPF não utilizada que produzia aviso no pacote WebView2.

O gateway de uso real foi instalado em `%LOCALAPPDATA%\LocalAuthor\lan-runtime` e está escutando exclusivamente em **192.168.1.240:8443**, com clientes restritos a **192.168.1.0/24**. O backend existente continua em **127.0.0.1:8765**. Um teste autenticado com validação TLS no IP da rede respondeu com sucesso a partir deste computador.

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

1. **Firewall:** sessão sem elevação e Wi-Fi classificado como público. Executar o atalho `Liberar rede local (Administrador)` no servidor. Ele cria regra apenas para o executável/porta/IP/interface e sub-rede especificados, sem abrir roteador ou mudar perfil de rede.
2. **Outro computador físico:** instalar o cliente e importar a conexão para concluir o teste real entre máquinas. O teste no IP LAN a partir deste PC não equivale a esse teste.
3. **Operação:** reservar IP no DHCP e manter o servidor acordado. Retorno automático após novo login não foi validado por reboot nesta rodada.
4. **Equipe:** os dispositivos acessam o mesmo workspace pessoal. Não foi implementado isolamento de contas de funcionários ou RBAC por projeto.

O download/instalação do compilador Inno Setup foi rejeitado pela revisão automática com mensagem “blocked by policy”. O bloqueio não foi contornado: a ferramenta não foi instalada ou executada. O instalador entregue foi criado em código próprio com o SDK .NET já existente. O instalador Microsoft WebView2 foi somente baixado, teve assinatura verificada e foi empacotado para uso quando necessário.
