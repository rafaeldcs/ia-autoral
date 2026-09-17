# Arquitetura implementada

## Fronteiras reais

```text
Navegador local → UI estática PT-BR → API Python (loopback + token)
                                      ├─ memória SQLite/FTS5
                                      ├─ snapshots/propostas/revisão
                                      ├─ fila persistente de um worker
                                      ├─ pesquisa HTTPS opt-in → domínios autorizados
                                      ├─ laboratório CPU NumPy → checkpoints próprios
                                      └─ verificações opt-in → Docker local com imagem fixa

Host .NET opcional → mesma UI → API Python local (sem upstream externo)
```

O núcleo Python é uma implementação funcional de referência; não é apenas pseudocódigo. Sua escolha permitiu executar testes no ambiente disponível. A migração de domínio/aplicação/infraestrutura para C# e integração Roslyn previstas no plano original continuam pendentes.

## Módulos

| Arquivo/pasta | Responsabilidade |
|---|---|
| `config.py`, `util.py` | Configuração, token, hashes, timestamps e escrita por arquivo |
| `safety.py` | Caminhos, links, extensão, tamanho e detecção heurística de segredos |
| `store.py` | Esquema SQLite, fontes/versões/trechos/relações/FTS5/auditoria |
| `knowledge.py` | Indexação e recuperação com fontes; decisão simples de falta/desatualização |
| `research.py` | TLS/HTTP, allowlist, DNS/IP, robots, cache e extração limitada |
| `tasks.py` | Snapshots, propostas, diferenças, revisão, aplicação e recuperação |
| `jobs.py` | Fila SQLite, único worker, estados, cancelamento e interrupção |
| `runner.py` | Construção/execução opt-in de comandos fixos em Docker |
| `dataset.py` | Integridade/permissão/grupos/partições/deduplicação do corpus pequeno |
| `nn/` | Matemática, tokenizador, modelo, otimizador, checkpoint e treino |
| `application.py`, `server.py`, `cli.py` | Composição, API HTTP e comandos locais |
| `backup.py`, `diagnostics.py` | Backup/restauração e diagnóstico do ambiente |
| `code_tools.py` | Candidatos a símbolos por regras lexicais; NÃO substitui Roslyn |

## Memória

O banco preserva fontes e versões, e a busca seleciona os trechos da versão atual. Um hash evita reprocessar o mesmo conteúdo. Escopo global não é inserido silenciosamente em consultas de projeto; a inclusão precisa ser pedida. Relações apontam para trechos de evidência, com origem e estado. Não há embeddings ou expansão semântica treinada.

A decisão `needs_research` se baseia em ausência de hits ou validade temporal de material web. Não mede verdade, entendimento, completude semântica ou compatibilidade confiável de todas as versões. Tais mecanismos exigem avaliações posteriores.

## Tarefas e dados externos

As propostas atuais são manuais/importadas. Cada alteração tem caminho, hash do original e conteúdo novo. O modelo experimental não decide permissões, não emite patches autonomamente e não controla o runner. Feedback cria experiência; não treina nem substitui o modelo automaticamente.

A fila é persistente, com um worker; tarefas síncronas da API podem coexistir e são protegidas onde necessário. Não há escalonador avançado de memória/GPU nem promessa de teto global de RAM. O cancelamento é cooperativo, não uma interrupção instantânea de toda operação matemática.

## Modelo

Transformer causal pre-layernorm, atenção mascarada, MLP, posições aprendidas e embeddings compartilhados na saída. Treinamento CPU float64 de referência, autodiferenciação própria, AdamW e recorte de gradiente. NumPy fornece operações numéricas. Não há inferência de fornecedor, quantização, kernel CUDA, KV cache otimizado ou streaming de corpus grande.

Configuração do teste minúsculo: vocabulário 258, contexto 8, dimensão 8, duas cabeças, um bloco, expansão 4, 3.016 parâmetros. Limite de configuração do motor: 2 milhões de parâmetros, contexto 256 e limites adicionais de dimensão/vocabulário. Isso não implementa o candidato de 34 milhões descrito no plano.

O checkpoint preserva pesos, otimizador, tokenizador, estado aleatório e linhagem. O hash verifica integridade, não autenticidade de origem. A perda numérica e repetição correta de um padrão não são prova de competência em C#.

## Dados fora do Git

Banco, token, cache, workspaces, corpus, modelos e backups ficam fora da pasta-fonte. O limite de conteúdo do banco não limita automaticamente o tamanho físico de todos os históricos/workspaces. Retenção e quota global de disco são pendências.

## Conectividade

A operação local não precisa de GitHub. A pesquisa é a única saída funcional prevista e exige alteração explícita de `offline` e fontes permitidas. Instalar ferramentas, baixar dependências ou usar GitHub Actions envolve serviços externos na etapa de desenvolvimento; não se afirma que esse ZIP já contém todas as ferramentas para instalação offline.
