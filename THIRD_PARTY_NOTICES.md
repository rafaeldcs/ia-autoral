# Autoria, infraestrutura e dependências

## Senha de publicação — 0.3.2

O gateway acrescenta Microsoft.Data.Sqlite 10.0.12 e suas dependências SQLitePCLRaw/SQLite para um banco local de autorização de publicação, sem serviço externo. O hash utiliza PBKDF2-HMAC-SHA256 da biblioteca padrão .NET, salt aleatório e 600.000 iterações. A senha original não é persistida. Referência do pacote: https://www.nuget.org/packages/Microsoft.Data.Sqlite/10.0.12 . O banco fica fora do repositório, separado dos projetos e dos modelos existentes.

## Distribuição LAN 0.2.0 (17/09/2026)

O pacote Windows LAN acrescenta gateway ASP.NET Core 10, cliente Windows Forms com Microsoft.Web.WebView2 1.0.4191.47 e instalador próprio .NET. Nesta distribuição binária, runtimes .NET 10.0.9 são incluídos pela publicação self-contained, juntamente com seus avisos e licenças; WebView2 possui SDK com avisos incluídos e instalador offline Evergreen da Microsoft com assinatura Authenticode validada. O runtime WebView2 é instalado somente se necessário. Esses componentes são infraestrutura; não contêm um modelo de IA pré-treinado usado pelo LocalAuthor.

As referências abaixo ao ZIP e a runtimes não redistribuídos descrevem o pacote-fonte original. O instalador LAN é um artefato distinto. O compilador Inno Setup não foi instalado nem utilizado: a instalação da ferramenta foi bloqueada pela revisão automática, e o instalador final foi desenvolvido com o SDK .NET existente. A publicação experimental não possui certificado comercial de assinatura de código.

Esta implementação foi elaborada com assistência do ChatGPT nesta conversa, a pedido de Rafael. Não foi copiado um repositório de IA para troca de marca. Isso não significa invenção de Transformer, BPE, AdamW, SQLite ou outras técnicas conhecidas, nem constitui garantia jurídica de exclusividade sobre o código. Antes de distribuir comercialmente, faça revisão de dependências/licenciamento e defina a licença do projeto.

## O que o projeto implementa

Lógica de memória, coleta/cache, políticas, fluxo de revisão, API, interface, diferenciação automática, Transformer, tokenizadores, otimização, checkpoints e treinamento. Não há arquivos de pesos pré-treinados ou integração com provedores de IA.

## Infraestrutura externa explicitamente utilizada

| Componente | Papel | Situação no ZIP |
|---|---|---|
| Python 3.11+ e biblioteca padrão | Runtime, HTTP, arquivos, TLS, SQLite | Instalado separadamente; não redistribuído |
| SQLite/FTS5 via `sqlite3` | Banco/busca textual | Biblioteca disponível no runtime Python; suporte FTS5 necessário |
| NumPy 2.3.5 | Arrays e operações matemáticas em CPU | Dependência opcional fixada; não redistribuída |
| .NET/ASP.NET Core 10 | Host opcional | Código de integração; SDK/runtime não redistribuídos |
| Git / GitHub CLI | Controle de versão e publicação opcional | Instalados separadamente |
| Docker | Execução restrita opt-in | Nenhuma imagem ou runtime incluído |
| Playwright 1.55.0 / Chromium ou Edge local | Teste de navegador opcional; requirements-dev.txt | Não necessários para iniciar; não redistribuídos |
| GitHub Actions oficiais | CI remoto opcional | CI inicial verificado; workflow ampliado desta continuação ainda não executado remotamente |

O código NumPy utilizado é infraestrutura de cálculo, não autograd de terceiros nem inteligência pronta. Não usamos PyTorch, TensorFlow, modelos Hugging Face, APIs de IA ou embeddings externos.

O repositório não contém CUDA ou Roslyn funcional. O diretório `native/` documenta a pendência; não equivale a implementar a GPU.

Referências conceituais, para consulta (não são chamadas pelo runtime):
- Transformer: Vaswani et al., Attention Is All You Need — https://arxiv.org/abs/1706.03762
- SQLite FTS5 — https://www.sqlite.org/fts5.html
- Python biblioteca padrão — https://docs.python.org/3/library/
- NumPy — https://numpy.org/doc/
- HTTP conditional requests — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests
- RFC 9309, robots.txt — https://www.rfc-editor.org/rfc/rfc9309.html
- GitHub CLI, criação de repositório — https://cli.github.com/manual/gh_repo_create

Nenhuma licença pública foi atribuída automaticamente a este projeto. Conteúdo utilizado para consulta não recebe automaticamente autorização para treinamento. Os testes numéricos usam padrões minúsculos de engenharia, não uma base de ensino de programação. O corpus produtivo ainda precisa ser criado e autorizado pelo responsável.
