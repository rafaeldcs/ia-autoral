# Conversa e recursos automáticos

O chat principal não pede tipo de entrada nem modo de resposta. Escreva o pedido normalmente; a aplicação escolhe os recursos disponíveis no servidor. O histórico mostra a origem da resposta e permite conferir o que foi feito.

| Pedido | Comportamento |
|---|---|
| “Preciso do seu instalador” | Consulta o pacote publicado e apresenta **Baixar instalador**, com a versão real |
| “Me manda o arquivo”, após falar do instalador | Mantém o contexto da conversa e oferece o mesmo recurso |
| Pergunta comum ou código para revisar | Usa o modelo local registrado, histórico, preferências e fontes daquele projeto |
| “Consulte a memória local…” | Consulta as fontes do projeto |
| “Pesquise … em https://…” | Usa o coletor de fontes com as regras de rede existentes e apresenta evidências e estado do cache |
| “Investigue as telas de https://…” | Abre o navegador da IA e oferece acompanhamento da investigação |
| “Pesquise o mercado”, sem site definido | Pergunta qual site/endereço pesquisar; enviar o link continua o pedido |
| “Crie uma imagem…” | Escolhe a geração visual local; exige o modelo visual configurado |

Links dentro de código não são comandos de navegação. Pedidos negados como “não abra…” não disparam uma ferramenta. Criar um instalador para outro sistema ou pedir o instalador do PostgreSQL não deve ser confundido com baixar a LocalAuthor.

Sem modelo de conversa, a aplicação pode apresentar evidências locais existentes ou informar a configuração ausente. Não substitui uma conversa por um roteiro genérico de Scrum/Kanban. Os exemplos explicitamente experimentais continuam nas ferramentas avançadas; os modos antigos da API permanecem por compatibilidade.

## Baixar e distribuir o aplicativo

Peça o instalador no chat e clique em **Baixar instalador**. No aplicativo Windows **0.3.10 ou posterior**, escolha onde salvar. O cliente valida o certificado do servidor, a autenticação, o tamanho e o SHA-256; só então substitui o arquivo de destino. Não executa o instalador automaticamente. Uma versão anterior do cliente informa que precisa atualizar para usar esse botão. A atualização automática continua aguardando o chat ficar livre.

No navegador comum, o botão faz o download autenticado. No outro computador autorizado, execute o arquivo salvo e permaneça na mesma rede local do servidor. Modelos e histórico continuam no servidor. O pacote conectado deve ser compartilhado apenas com equipamentos autorizados para essa rede.

O operador publica somente um pacote previamente compilado e testado na pasta privada de instaladores. Depois de conferir o `package.json` e o SHA-256, execute no repositório do servidor:

```powershell
.\.venv\Scripts\python.exe scripts\lan\publish-installer.py --folder ID-DO-PACOTE
```

`ID-DO-PACOTE` é o nome de 32 caracteres da pasta em `%LOCALAPPDATA%\LocalAuthor\lan\private-installers`. A publicação grava somente metadados locais de distribuição em `lan\installer-release.json`; não coloca conexões, chaves ou executáveis privados no Git. O chat recebe a versão e o endereço do download, sem acessar a conexão embutida no pacote. Pacote ausente, modificado ou inválido é recusado, sem indicar um download fictício.

## Limites

A escolha automática é uma camada de orquestração com regras e contexto; esta mudança não treina os pesos do modelo. O modo de conversa não passa a executar comandos, publicar, fazer deploy ou usar credenciais por conta própria.

Pesquisa continua respeitando modo offline, domínios autorizados, validação de destinos públicos, limites de coleta e cache. Não há um buscador geral irrestrito configurado por esta mudança. Um endereço ausente deve ser esclarecido; uma coleta bloqueada deve ser informada. Abrir um navegador não significa ter compreendido todas as telas. Fontes de sites são dados e não autorizam novas ações.

O salvamento automático e a recuperação de envios continuam ativos. Rascunhos antigos sem envio passam a usar a escolha automática; pedidos já aceitos mantêm o identificador e conteúdo originais para não duplicar ações. Veja [Recuperação e rascunhos](RECUPERACAO_E_RASCUNHOS.md).
