# LocalAuthor — instalar, ensinar e atualizar na rede local

Guia da versão 0.3.7 · Windows x64 · atualizado em 08/10/2026.

O aplicativo não exibe mais uma barra de conexão acima do chat. O IP e as ações manuais ficam em **Ferramentas e configurações → Este computador**. Descoberta, reconexão e atualizações continuam automáticas em computadores pareados; os avisos de atualização aparecem apenas quando necessários. Em uma instalação nova na rede, use o instalador privado conectado, que já inclui o vínculo autorizado. Não há etapa de selecionar arquivo de conexão.

## 1. Como sua instalação funciona

**Este computador é o servidor.** Ele executa a IA e guarda a memória, os modelos, os projetos e as conversas. Os outros computadores são clientes que abrem esse mesmo servidor pela rede local.

Não instale um segundo servidor em cada computador. Instale somente o aplicativo cliente já conectado. Assim, você não começa uma IA vazia em cada máquina.

| O que mudou | Como chega aos outros computadores |
| --- | --- |
| Nota, fonte, projeto ou conversa salva no servidor | Os clientes consultam a mesma base. Reabra a tela ou a conversa para atualizar a visualização. |
| Modelo treinado, avaliado e habilitado no servidor | Os pedidos seguintes usam o modelo habilitado para aquele recurso. Não é necessário distribuir pesos aos clientes. |
| Código Python ou páginas da IA alterados no GitHub | Atualizar a cópia do projeto no servidor, validar e reiniciar o backend. Depois, reconectar os clientes. |
| Serviço HTTPS/descoberta alterado | Compilar e atualizar o gateway instalado no servidor; reaplicar a regra de firewall se o caminho do executável mudar. |
| Aplicativo Windows alterado | Compilar com versão maior e publicar o executável no servidor. Os clientes baixam, fecham e reabrem automaticamente quando estiverem livres. |

**Dar push no GitHub não implanta o código automaticamente.** O GitHub guarda o código; os dados e o aprendizado privado permanecem no servidor. Hoje não existe um serviço que observe o GitHub e instale sozinho as mudanças.

## 2. Preparar o servidor para uso diário

1. Ligue este computador e entre no usuário Windows que possui a instalação.
2. Abra **LocalAuthor**, pelo atalho da área de trabalho. Na versão 0.3.5 ele reconhece o servidor local, liga os serviços e aguarda a conexão sem pedir arquivo.
3. Espere o chat abrir com seus projetos. Neste computador, a conexão usa `https://127.0.0.1:8443` quando a descoberta automática está habilitada.
4. Mantenha o computador ligado, acordado e conectado à rede local enquanto os demais usam a IA.
5. Para acesso de outros computadores, o firewall do servidor precisa permitir TCP 8443 e UDP 38443 para o gateway LocalAuthor, somente na sub-rede local.

Se ainda não liberou o firewall: no **servidor**, abra PowerShell como administrador, com o mesmo usuário da instalação, e execute:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\LocalAuthor\lan-runtime\Enable-Firewall.ps1"
```

Essa etapa exige administrador. Não precisa abrir portas no roteador. A liberação só precisa ser repetida quando a configuração/caminho do gateway mudar.

## 3. Instalar em outro computador da mesma rede

1. No servidor, use o arquivo **Instalar-LocalAuthor-Conectado.exe** entregue junto deste guia. Ele já está vinculado a este servidor.
2. Copie esse executável por um meio privado para o outro computador, como pendrive ou pasta de rede com acesso restrito.
3. Conecte o outro computador à mesma rede local do servidor. Evite Wi-Fi de convidados, que pode impedir comunicação entre aparelhos.
4. Execute o instalador e mantenha marcada a opção **Abrir LocalAuthor ao entrar no Windows**, se desejar.
5. Abra **LocalAuthor** pelo menu Iniciar. A conexão já estará configurada; **não é necessário selecionar um arquivo de conexão**.
6. Confirme que aparecem os mesmos projetos. Abra uma conversa existente para confirmar que está no servidor certo.

O cliente não precisa de Python, SDK .NET, modelos ou banco próprio. O pacote inclui o runtime .NET e o instalador do WebView2. É para Windows x64; não serve como instalador completo de um servidor novo.

O mesmo instalador conectado pode ser usado nos seus computadores. Essas cópias compartilham uma autorização: revogá-la desconecta todas. Para revogar máquinas separadamente, gere um instalador por máquina, conforme a seção 8.

**Mantenha o instalador conectado privado.** Ele contém uma autorização de acesso ao seu servidor, mas não a senha de publicação. Não envie esse executável ao GitHub, a um release público ou a pessoas que não devam acessar o workspace.

Uma reinstalação preserva a conexão que já estiver salva. Se uma máquina usada anteriormente continuar apontando para outro servidor, confirme que não há trabalho pendente, use **Esquecer conexão**, feche o aplicativo e execute este instalador conectado novamente. Isso remove apenas o vínculo local, não os projetos do servidor.

## 4. Ensinar a partir de outro computador

### Guardar conhecimento para consulta

1. No aplicativo conectado, abra **Ferramentas avançadas**.
2. Em **Memória e consulta**, escolha o escopo correto: um projeto ou **Biblioteca global**.
3. Em **Adicionar conhecimento**, preencha título e conteúdo; clique em **Guardar nota**.
4. Consulte um termo específico da nota e confira a fonte retornada.
5. Em outro computador, abra a mesma tela, escolha o mesmo escopo e repita a consulta. Para consultar notas globais dentro de um projeto, marque **Incluir biblioteca global neste projeto**.

O conteúdo é gravado no servidor, mesmo quando a ação parte de outro computador. Não precisa exportar/importar esse conhecimento entre clientes. A tela de outro cliente pode precisar ser reaberta para carregar a alteração; não há atualização instantânea de todas as telas abertas.

Conversas também ficam centralizadas, mas **conversar, guardar notas e investigar um site não significa treinar automaticamente os pesos do modelo**. Notas alimentam a consulta; históricos e evidências pertencem ao contexto e escopo em que foram salvos.

### Treinar o modelo

1. Prepare no servidor um conjunto de exemplos autorizado, com manifesto e separação de treino, validação e teste. Siga `docs/DATASET.md` no repositório.
2. Pelo aplicativo de qualquer cliente conectado, abra **Ferramentas avançadas → Laboratório**.
3. Informe o manifesto relativo à pasta `corpus` **do servidor**, revise a autorização e inicie o experimento CPU.
4. Acompanhe **Atividade**. O trabalho roda no servidor; os resultados e checkpoints ficam nele.
5. Avalie o candidato em casos que não foram usados para ensiná-lo. O responsável técnico deve habilitar somente o candidato aprovado, pelo fluxo do recurso correspondente.
6. Depois de habilitado, valide o mesmo recurso a partir de dois clientes conectados.

O laboratório não promove automaticamente qualquer treinamento concluído para todos os modos do chat. A seleção de candidatos é específica de cada recurso; não existe botão geral de promoção automática nesta versão. Instalar o cliente ou concluir um treino não comprova domínio de qualquer tarefa.

## 5. Atualizar o aplicativo Windows de todos os clientes

Esta é a atualização da janela/aplicativo instalado. Para atualizar o servidor e o código do GitHub, veja a seção 6.

1. Obtenha do responsável técnico o **LocalAuthor.Client.exe** compilado e testado, com versão maior que a publicada. Na entrega atual, ele acompanha o instalador e o guia.
2. Em **qualquer computador conectado ao servidor**, abra LocalAuthor e clique em **Publicar atualização…**.
3. Selecione **LocalAuthor.Client.exe**. Não selecione `Instalar-LocalAuthor-Conectado.exe`: o arquivo publicado é o cliente, não o instalador.
4. Digite a senha de publicação do servidor, confira versão/tamanho apresentados e confirme.
5. Deixe os demais aplicativos abertos e conectados. Eles verificam ao abrir e a cada cinco minutos.
6. Quando há uma versão maior, o aplicativo baixa e verifica o pacote, avisa com contagem de 15 segundos, fecha, instala e abre novamente.

Para não interromper o trabalho, texto não enviado, geração ativa, formulários editados ou telas avançadas podem adiar a reinicialização. Salve o trabalho, volte ao chat e reconecte. O botão **Adiar atualização** posterga por 30 minutos. Uma máquina desligada recebe a atualização quando voltar a abrir o aplicativo com o servidor acessível.

Se a mesma versão e o mesmo pacote já estiverem publicados, não é necessário publicar novamente. Um pacote diferente precisa de número de versão maior. Clientes muito antigos, anteriores a 0.3.0, precisam executar o instalador uma vez para receber o atualizador.

Na primeira configuração do servidor, a senha de publicação deve ser cadastrada antes de distribuir o instalador. Ela exige de 12 a 256 caracteres. A senha não é gravada nos instaladores nem enviada ao GitHub; o servidor guarda sua verificação no banco. Quem possui a senha e um cliente autorizado pode publicar.

## 6. Atualizei o GitHub: como aplicar na rede

Esta manutenção é feita **uma vez no servidor**, pelo responsável técnico. Não execute `git pull` em cada cliente. Reserve um período sem treinamento, investigação ou edição em andamento e tenha um backup consistente dos dados do servidor e dos projetos, além do código Git. Bancos SQLite em uso exigem backup consistente; uma cópia avulsa enquanto estão sendo escritos não garante recuperação.

### A. Trazer e validar o código no servidor

Na instalação atual, abra PowerShell na pasta do projeto:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Desktop\ia-autoral'
git status --short
git pull --ff-only origin main
```

Se houver alterações locais, conflito ou falha no pull, pare e revise. Não force, não descarte arquivos e não apague dados para continuar. Confirme que está atualizando a pasta usada pelo servidor: ela consta como `SourceRoot` em `%LOCALAPPDATA%\LocalAuthor\lan\runtime.json`.

Se a versão mudar dependências Python, atualize o ambiente conforme o projeto. Na configuração atual:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[training]'
.\.venv\Scripts\python.exe scripts/run-tests.py --allow-unavailable-symlinks
```

A opção final permite somente três testes de symlink indisponíveis sem privilégio no Windows; não significa cobertura integral. Erros/falhas nos demais testes precisam ser corrigidos. Instalação de dependências e obtenção do código podem precisar de internet; o uso cotidiano da IA permanece na LAN.

### B. Atualizar a parte que mudou

- **Somente Python/UI:** depois de validar, reinicie o Windows do servidor em uma janela combinada, entre no mesmo usuário e abra LocalAuthor. O backend passa a carregar o código atualizado. Nos clientes, salve o trabalho e clique em **Reconectar** para carregar as páginas novas. Reiniciar o servidor interrompe o acesso de todos durante esse período.
- **Gateway HTTPS/descoberta:** compile com o primeiro comando abaixo e execute o segundo para atualizar o gateway instalado. Ele preserva certificado/dispositivos, guarda as configurações anteriores e reinicia o gateway/supervisor. Depois, reaplique o firewall da seção 2, pois o caminho do binário muda. Se o Python também mudou, faça igualmente o reinício descrito acima.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-lan.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lan/Update-Discovery.ps1
```

- **Cliente Windows:** o código da release deve trazer `Version` maior em `dotnet/LocalAuthor.Client/LocalAuthor.Client.csproj` e a versão correspondente no projeto do instalador. Compile, execute as verificações abaixo e publique pela seção 5. Nunca reutilize a versão para outro binário.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-lan.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test-client-update.ps1
.\.venv\Scripts\python.exe scripts/local-server-startup-smoke.py
```

O arquivo para publicação é `build\lan-client\LocalAuthor.Client.exe`. Os comandos PowerShell de compilação/teste devem terminar sem erro; não prossiga se algum falhar. A manutenção exige as dependências de desenvolvimento já usadas neste servidor, incluindo SDK .NET; essas ferramentas não são necessárias nos computadores clientes.

Também é possível publicar diretamente no servidor, com a permissão local do responsável:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lan/Publish-ClientUpdate.ps1
```

Esse comando é administrativo local e escreve a publicação no servidor. A publicação remota pelo aplicativo exige a senha. Não compartilhe a pasta de dados do servidor com permissão de escrita para substituir essa autenticação.

### C. Conferir a entrega

1. No servidor, confirme que o chat abre e os projetos continuam presentes.
2. Em um cliente da LAN, confirme a conexão, abra o mesmo projeto e consulte uma nota conhecida.
3. Se publicou o cliente, espere a atualização e confirme a versão nas propriedades do executável instalado: `%LOCALAPPDATA%\Programs\LocalAuthorClient\LocalAuthor.Client.exe`.
4. Gere um novo instalador conectado, seção 8, para que futuras instalações já comecem na versão nova.
5. Não envie `models`, corpus privado, banco, senhas, tokens, certificados privados ou instaladores conectados ao GitHub.

## 7. Mudança de Wi-Fi ou internet

- No próprio servidor, o cliente atualizado usa loopback e não depende do IP da rede.
- Nos outros computadores, a identidade salva permite procurar o mesmo servidor na LAN quando o IP mudar.
- Servidor e clientes precisam estar na mesma rede local, sem bloqueio entre dispositivos. Redes corporativas/VLANs ou Wi-Fi de convidados podem impedir a descoberta.
- Mudar somente o cliente para outra casa/rede não dá acesso ao servidor pela internet. Esta entrega não configura VPN nem acesso externo.
- Servidor desligado não responde nem entrega atualizações. Não existe cópia autônoma da IA no cliente.

## 8. Gerar o próximo instalador conectado

No servidor, após compilar/testar a versão desejada:

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Desktop\ia-autoral'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-paired-installer.ps1 -DeviceName 'Computadores pessoais da rede local'
```

O comando mostra a pasta privada em `%LOCALAPPDATA%\LocalAuthor\lan\private-installers`. Transfira somente o instalador conectado, o guia e os hashes de entrega; não precisa enviar o arquivo interno de conexão. Para autorizações independentes, repita usando nomes como `Notebook pessoal` e `PC escritorio`.

O instalador genérico `dist\lan\Instalar-LocalAuthor-Windows-x64.exe` não inclui a autorização desta rede. Ele reconhece uma instalação de servidor local, mas sozinho não deixa um cliente novo de outra máquina já pareado. Para o fluxo sem arquivo, use o **Conectado**.

## 9. Se algo não atualizar

| Sintoma | Verificação |
| --- | --- |
| Cliente novo pede arquivo | Verifique se foi instalado o pacote **Conectado**, se a instalação terminou e se está usando o mesmo usuário Windows. |
| Servidor não encontrado | Abra LocalAuthor no servidor; confira mesma LAN, firewall e ausência de isolamento Wi-Fi. |
| GitHub mudou, mas a tela continua antiga | Confira pull na pasta correta, reinício do backend e reconexão dos clientes. |
| Aplicativo não reinicia para atualizar | Confirme versão maior publicada, conexão ativa e ausência de rascunhos/formulários ou geração em andamento. |
| Conhecimento não aparece | Confira servidor, escopo/projeto, gravação da nota e opção de incluir biblioteca global. |
| Treino terminou, mas o comportamento não mudou | Confira avaliação e habilitação do candidato no recurso correspondente; conclusão do treino não é promoção automática. |
| Erro de certificado ou acesso revogado | Corrija o vínculo com o responsável pelo servidor. Não desative TLS nem aceite qualquer servidor encontrado. |

Diagnósticos ficam em `%LOCALAPPDATA%\LocalAuthor\lan` no servidor e `%LOCALAPPDATA%\LocalAuthorClient\updates` em cada cliente. Não publique os dados dessas pastas sem revisar seu conteúdo.

## 10. Alcance da validação

Os testes automatizados usam processos, HTTPS e clientes nativos reais em perfis isolados nesta máquina, incluindo fechamento/reabertura e recuperação de atualização. Eles não substituem instalar em um segundo computador físico. Faça a confirmação da seção 3 no equipamento de destino. Aprendizado centralizado não significa que todos os comportamentos possíveis da IA foram testados.
