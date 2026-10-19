# Leads e oportunidades no servidor local

O módulo `/leads` reúne contexto da empresa, entrada de contatos, triagem pela IA local, revisão humana e funil. Os dados ficam no banco privado do servidor; computadores pareados acessam esse mesmo servidor. O token local e os dispositivos pareados têm acesso de operador: esta interface não é um portal público para clientes.

O gateway nativo precisa incluir as rotas `/leads`, `/leads.js` e `/leads.css`. Atualizar somente o Python não altera um gateway compilado antigo. Os clientes pareados existentes carregam a tela do servidor atualizado; não precisam de um modelo próprio nem recebem uma cópia dos leads.

## Começar pelo aplicativo

1. Abra **Leads e oportunidades** nas ferramentas da conversa ou `/leads`. Selecione o projeto da empresa.
2. Em **Contexto da empresa**, cadastre marca, público, apresentação, convite, fatos e perguntas aprovadas. Cada fato exige fonte e conferência nos últimos 30 dias. O botão ShopAir preenche um exemplo editável, sem salvar ou aprovar uma campanha automaticamente.
3. Em **Adicionar contato**, registre mensagem, empresa, dados necessários e preferência de contato. Pesquisa pública fica separada de um pedido de atendimento; não concede consentimento.
4. Selecione o interessado e peça **Analisar com a IA local**. A fila processa um lead por vez, com contexto curto, sem incluir os campos de e-mail/telefone no prompt. Informações que a própria mensagem contenha continuam no texto local. A IA seleciona fatos e perguntas existentes; a aplicação compõe o rascunho com esses textos exatos. Ela não pode acrescentar parceiros, preços ou requisitos livres nessa saída.
5. Confira necessidade, evidências, perguntas e rascunho antes de aplicar. Se a análise estiver errada, abra **A análise precisa de correção?** e registre o motivo. A próxima tentativa desse lead recebe esse feedback como contexto; isso não treina os pesos.
6. Registre demonstração, proposta e resultado no funil. **Ganho** é uma anotação da equipe, não confirmação de pagamento. Os indicadores por campanha usam a atribuição do primeiro contato; mensagens posteriores preservam suas próprias origens no histórico.

Não há envio de mensagens neste módulo. Copiar um rascunho exige revisão da versão atual. Novas mensagens ou mudanças do contexto invalidam aprovações dependentes. Recusas explícitas bloqueiam a IA e são mantidas para e-mail/telefone conhecidos; um evento posterior não pode reativar silenciosamente o contato. A retomada com nova autorização não está implementada.

## Captura pelo site e rede local

```text
Visitante → backend do site → fila pública HTTPS
                                  ↑ busca autenticada e recibo
                         LocalAuthor nesta máquina
                                  ↓
                          inbox e revisão da equipe
```

O relay é um componente opcional para comunicação entre servidores. O formulário público continua no backend da loja. Não coloque a chave de escrita em JavaScript público e não exponha a porta 8765, o token local, a descoberta LAN ou a base de conversas à internet.

No servidor público, use o código versionado e um ambiente Python compatível com o projeto. O relay usa biblioteca padrão, sem SDK de IA ou nova dependência. Gere um ambiente privado uma única vez:

```bash
python ops/leads/init-relay.py --output /caminho/privado/relay.env
# Carregue o arquivo apenas no ambiente do serviço, sem imprimi-lo em logs.
set -a
. /caminho/privado/relay.env
set +a
PYTHONPATH=src python -m localauthor.lead_relay serve \
  --database /caminho/privado/queue.sqlite3 \
  --queue-id "$LOCALAUTHOR_RELAY_QUEUE_ID" --port 8848
```

Restrinja acesso ao arquivo privado e ao banco. O processo escuta somente `127.0.0.1`; coloque um proxy HTTPS público na frente. `ops/leads/Caddyfile.example` é um exemplo para adaptar ao domínio/DNS aprovado, não uma alteração já aplicada à ShopAir. O serviço precisa ser mantido em execução pelo gerenciador de processos da hospedagem.

Em **Conectar site**, na LocalAuthor, informe URL pública HTTPS, identidade da fila e chave de leitura. Ela fica protegida por DPAPI do usuário Windows do servidor, fora dos jobs e do contexto da IA. Salve a conexão ativa: o servidor consulta aproximadamente a cada 30 segundos enquanto estiver ligado. A configuração de rede precisa permitir acesso; o modo offline bloqueia a busca. **Pausar coleta** preserva dados e cancela cooperativamente a consulta ativa. Atualize a tela para conferir o último estado e recibos. Erro não é confirmado como entrega.

Para diagnóstico controlado também existe o comando `python -m localauthor.lead_relay pull --home <dados-locais> --project-id <projeto> --queue-id <fila> --url https://dominio/`; a chave de leitura deve estar em `LOCALAUTHOR_RELAY_READ_KEY`. `--watch` mantém a consulta; use somente um coletor por projeto. A URL pública precisa de certificado válido; DNS privado, IP literal, redirecionamentos e downgrade HTTP não são aceitos pelo transporte de produção.

## Contrato de integração

O backend envia `POST /events` ao relay com `Authorization: Bearer <chave-de-escrita>`, `Content-Type: application/json` e o evento abaixo. Conserve o mesmo `event_id` ao repetir a mesma entrega. O exemplo é inteiramente fictício:

```json
{
  "source": "website",
  "event_id": "formulario-sintetico-001",
  "company": "Loja de demonstração",
  "name": "",
  "email": "simulacao@example.test",
  "phone": "",
  "message": "Quero conhecer uma loja online para meu negócio.",
  "campaign": "demonstracao-outubro",
  "source_url": "https://example.com/",
  "permission": "reply_requested",
  "opt_out": false
}
```

`source`: `website`, `manual`, `research`, `meta` ou `whatsapp`. Essas duas últimas são origens declaradas pelo backend, não conectores implementados ou prova de conta conectada. A integração oficial precisa autenticar/verificar o evento do provedor antes de convertê-lo neste formato. `permission`: `unknown`, `reply_requested`, `marketing_opt_in` ou `denied`, conforme manifestação registrada; não inferir de um perfil público. `research` exige URL e `unknown`. Campos vazios usam `""`, não `null`. Telefone recebe normalização básica, não verificação de existência do número.

O relay oferece `/pending` e `/ack` somente à chave de leitura, diferente da de escrita. O coletor confirma por hash depois do commit local. Se cair antes do recibo, a próxima busca deduplica. Mesmo ID com conteúdo diferente gera conflito, sem sobrescrever o original. A fila fica vinculada a um projeto e não pode ser redirecionada a outro. Pausas do computador preservam eventos pendentes na hospedagem.

Uma integração que já tenha acesso local autorizado pode usar `POST /api/leads/ingest` com `{ "project_id": "...", "event": { ... } }` e o token do servidor; essa API não é uma rota anônima para incorporar em páginas públicas.

## Limites e operação

Até 5.000 contatos por projeto, 20.000 eventos na instância, 100 revisões de contexto por projeto e 64 MB lógicos por módulo/fila, respeitando também a quota configurada para conteúdo de leads. Os históricos não são apagados para aparentar espaço livre. Fila cheia interrompe novas entregas explicitamente; não significa que o evento foi aceito. Inclua o banco privado do relay, o banco da LocalAuthor e as configurações protegidas na política de backup da operação. O relay preserva eventos confirmados; retenção e exclusão administrativa precisam de procedimento próprio antes de grande volume.

O módulo não instala DNS, hospedagem, formulários no código da ShopAir, anúncios Meta, webhooks WhatsApp, disparos automáticos ou busca irrestrita de empresas. Ele recebe cadastros/pesquisas fornecidos e entradas de um backend configurado. A ativação pública depende de domínio, acesso à hospedagem e integração do formulário real.

## Verificação

Execute `PYTHONUTF8=1 python scripts/run-tests.py` no ambiente de teste. No Windows sem privilégio de symlinks, `--allow-unavailable-symlinks` registra esses três casos como indisponíveis, sem declarar cobertura completa. `python scripts/leads-ui-smoke.py` verifica a tela com dublê de inferência; `--browser-channel msedge` usa o Edge instalado. Os testes de relay fazem HTTP real de loopback, inclusive falha depois do commit e antes do recibo. Isso não prova implantação HTTPS pública nem conexão com Meta/WhatsApp.

O ensaio de modelo real precisa de manifesto/pesos locais e sandbox de inferência verificada; não substitua por dublês para declarar qualidade. Um acerto de classificação não comprova adequação das evidências ou perguntas, portanto a revisão humana permanece obrigatória. Não houve fine-tuning nem incorporação de modelos/código/datasets Harvey LAB. O estudo desse projeto orientou critérios, preservação de tentativas e avaliação por caso.
