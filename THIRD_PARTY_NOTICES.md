# Autoria, infraestrutura e dependências

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
| Playwright/Chromium | Teste de navegador opcional | Não necessários para iniciar; não redistribuídos |
| GitHub Actions oficiais | CI remoto opcional | Workflow preparado, não executado nesta entrega |

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
