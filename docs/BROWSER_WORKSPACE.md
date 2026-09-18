# Navegador da IA no chat

## Uso

Escolha um projeto e clique em **Investigar site**, ou selecione o modo
**Navegar e investigar site** na conversa e envie um endereço HTTPS. O painel
mostra capturas reais produzidas pelo navegador do LocalAuthor, histórico,
ações disponíveis e hipóteses de finalidade. Em telas estreitas, ocupa a tela;
o botão de recolher retorna ao chat, sem encerrar a sessão.

**Investigar próximos links** solicita até cinco passos aos especialistas
neurais locais. Não transforma o restante da mensagem em um plano geral de
execução. **Atualizar captura**, **Rolar**, **Voltar** e os destinos observados
permitem conduzir a investigação. **Encerrar** cancela o trabalho e remove o
container. Cada sessão tem limite de 20 minutos e 60 observações; apenas uma
sessão fica ativa por servidor para limitar memória e CPU.

O histórico é separado por projeto e permanece após reiniciar o servidor.
Reiniciar não reabre páginas nem restaura credenciais. Sessões antigas podem ser
consultadas, mas ações exigem uma sessão viva e a observação mais recente.

## Login

Use **Entrar no site** quando um formulário compatível for detectado. Usuário
e senha viajam em memória pela API autenticada e pelo stdin do worker; não entram
no banco de mensagens, no manifesto da sessão ou na linha de comando. A captura
oculta inputs, textareas e conteúdo editável. Isso não anonimiza os demais dados
da página: o histórico autenticado é privado e fica fora do Git.

Em **Recursos de outros domínios**, autorize separadamente hosts de recursos
e hosts que podem receber autenticação. O site de origem é autorizado por padrão.
POST/OPTIONS só são liberados durante a tentativa explícita de login, para
endpoints terminados em login, signin, sign-in, session ou token nos hosts de
autenticação. Recursos autorizados apenas para leitura não ganham essa permissão.
Conexões bloqueadas aparecem como domínio e método, sem corpo, cookies ou senha.

A implementação reconhece formulários simples com um usuário, uma senha e um
botão de entrada inequívoco. Login em etapas, MFA, CAPTCHA, SSO com redirecionamento
externo e outros formatos não estão qualificados. Nunca se deve apresentar um
formulário enviado como autenticação comprovadamente bem-sucedida; confira a
captura resultante e a navegação posterior.

## Arquitetura e autorização

- `BrowserWorkspace` gerencia sessões e progresso por projeto, com APIs sob
  o mesmo token/origin check do servidor. Senhas não passam pela fila persistente.
- `live_browser.cjs` mantém Playwright/Chromium no container já existente
  `localauthor-functional-lab:1`. Não usa CUA/Codex para produzir as capturas.
- O adaptador fornece títulos, headings e controles visíveis aos especialistas
  autorais. O leitor de controles prevê categorias; a política propõe `OPEN_1`,
  `OPEN_2`, `RECORD` ou limites. Não há substituição de previsões pelo gabarito.
- A finalidade é uma hipótese de categoria com descrição fixa. Os pequenos
  modelos não compreendem pixels, relações completas de layout ou instruções
  arbitrárias do usuário. A tela é visualizada pelo usuário; o modelo recebe
  estrutura textual limitada, não visão neural equivalente à de modelos multimodais.
- Só destinos observados na mesma origem e botões de navegação reconhecidos
  pelo adaptador podem ser acionados. Formulários e nomes de mutação são recusados.
  O hash é conferido novamente antes da ação; alvos antigos são rejeitados.
- Rede pública HTTPS, DNS validado/fixado, allowlist de hosts, GET/HEAD de leitura,
  WebSockets e service workers bloqueados. Filtro de requisições não é prova de
  ausência de efeitos em qualquer servidor: até GET pode ser implementado com
  efeitos colaterais. Este recurso é experimental e voltado a investigação de QA.
- Container sem privilégios, capabilities removidas, seccomp e no-new-privileges,
  raiz somente leitura, 2 GB de RAM, 2 CPUs, 256 processos e saída própria.
  Falha de isolamento não gera alternativa de execução no host.

Os checkpoints precisam vir dos três cursos locais aprovados, permanecer na pasta
de modelos e corresponder aos hashes dos relatórios. Não há novos pesos externos,
API de IA, dependência Python ou instalação de navegador no host.

## Verificação desta entrega

- 217 testes de software passaram no Linux, sem skips.
- 19 verificações funcionais no navegador isolado, usando páginas fictícias e
  pesos autorais reais: capturas, navegação por link/botão, voltar, rolar, login,
  proposta de navegação do modelo, recusa de alvos antigos e controles de rede.
- A execução real em HML ShopAir abriu página pública, seguiu uma proposta do
  modelo e depois autenticou com a conta de QA, chegando ao painel de lojas.
  As primeiras tentativas bloqueadas foram preservadas; o host de autenticação
  separado exigiu autorização explícita. Capturas/recibos ficam fora do Git.
- A interface foi verificada no navegador, incluindo painel, histórico, estado
  de processamento e renderização da imagem retornada pelo LocalAuthor. Uma
  mensagem no chat abriu e capturou o YouTube no servidor principal. As larguras
  de 1.440 e 390 pixels foram verificadas sem overflow horizontal; o painel
  adapta entre visualização ao lado do chat e visualização em tela estreita.

As capturas reais também mostraram classificações incorretas de finalidade
(por exemplo, uma página inicial interpretada como busca). Isso permanece visível
como hipótese, não foi substituído por uma resposta escrita pelo Codex e impede
declarar o modelo qualificado para compreensão geral.

Esses resultados não certificam agir em qualquer site nem executar operações
arbitrárias. Sites novos, interfaces sem controles semânticos, regras de negócio,
iframes, downloads/uploads, compras e mutações não estão universalmente cobertos.
O instalador não precisa mudar para entregar HTML/JS pelo servidor atualizado;
esta entrega atualiza o código do servidor e a interface que ele serve.
