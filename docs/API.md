# API local de referência

Base: `http://127.0.0.1:8765`. A UI pública local serve somente `/`, `/app.js` e `/styles.css`. Todos os endpoints `/api/` exigem `Authorization: Bearer TOKEN_LOCAL`. POST exige objeto JSON e `Content-Type: application/json`. Não há CORS, cookies ou autenticação externa. Limite de corpo: 2,5 MB.

Respostas usuais: 200 sucesso, 400 entrada/política inválida, 401 token ausente/inválido, 404 recurso ausente, 409 conflito, 500 erro interno. Identificadores devem vir das respostas reais; exemplos abaixo são formatos, não IDs utilizáveis.

| Método/rota | Contrato principal |
|---|---|
| GET `/api/health` | Status, offline, capacidade não qualificada, estatísticas |
| GET `/api/diagnostics` | Diagnóstico do computador onde o processo roda |
| GET/POST `/api/projects` | Listar; criar com `name`, `root` absoluto autorizado |
| GET `/api/sources?scope=global` | Fontes do escopo |
| POST `/api/import` | Nota: `scope`, `title`, `content`; arquivo: `scope` de projeto, `path` relativo |
| POST `/api/consult` | `query`, `scope`, `include_global` opcional; trechos com fontes |
| POST `/api/sources/delete` | `source_id`, `scope`; invalida derivados, não pesos |
| GET `/api/relations?scope=global` | Relações registradas |
| POST `/api/relations` | `scope`, `subject`, `predicate`, `object`, `chunk_id`, `status` opcional |
| POST `/api/symbols` | `project_id`, `path`; candidatos lexicais |
| GET/POST `/api/tasks` | Listar; criar snapshot com `project_id`, `instruction` |
| GET `/api/tasks/ID` | Estado, proposta, diferenças e verificações |
| GET `/api/tasks/ID/files` | Manifesto do snapshot e hashes |
| GET `/api/tasks/ID/file?path=Product.cs` | Conteúdo e hash no workspace |
| POST `/api/tasks/ID/proposal` | `changes`, `allow_test_changes` opcional |
| POST `/api/tasks/ID/apply` | `proposal_hash`, `accept_without_tests` opcional explícito |
| POST `/api/tasks/ID/reject` | `{}` rejeita sem aplicar original |
| POST `/api/tasks/ID/recover` | `{}` tenta recuperação de journal sem sobrescrever mudança posterior |
| POST `/api/tasks/ID/feedback` | `status`, `note`; experiência, não treino |
| POST `/api/tasks/ID/verify` | `kind`: `dotnet-build`, `dotnet-test`, `python-tests`; `project_file` relativo quando aplicável |
| POST `/api/jobs/index` | `project_id` |
| POST `/api/jobs/research` | `urls` (até cinco), `scope` |
| POST `/api/jobs/train` | `manifest` relativo a dados/corpus; `approved_dataset=true`; `steps`, `batch_size`, `tokenizer`, `config` opcionais |
| GET `/api/jobs` e `/api/jobs/ID` | Fila e estado |
| POST `/api/jobs/ID/cancel` | `{}` solicita cancelamento cooperativo |
| GET `/api/models` | Relatórios de experimentos locais; não catálogo de modelos externos |

## Proposta

```json
{
  "changes": [{
    "path": "Product.cs",
    "before_sha256": "HASH_DO_SNAPSHOT",
    "content": "CONTEUDO_COMPLETO_NOVO"
  }],
  "allow_test_changes": false
}
```

Para criar arquivo permitido novo, `before_sha256` deve ser `null`; a pré-condição é que o arquivo não exista. Deleção de arquivos não é suportada nesta versão. De um a oito arquivos por proposta. A revisão devolve `proposal_hash`; é esse valor que deve ser enviado em `apply`.

## Contratos importantes

`consult` retorna modo de recuperação e `generated_answer=null`. Um campo `needs_research` significa ausência/idade de fontes pela política simples, não julgamento geral de verdade. Notas importadas não são marcadas automaticamente como permitidas para treino.

A fila executa no próprio processo do aplicativo iniciado pelo operador. Não há serviço remoto nem trabalho que continue nesta conversa. `runner_enabled=true` significa que uma imagem foi configurada, não que o sandbox passou em auditoria ou que Docker realmente está funcionando.

Esta documentação acompanha o código; confirme campos detalhados em `server.py`, `application.py` e respectivos testes antes de desenvolver outro cliente. Não há OpenAPI gerado ou garantia de estabilidade de API na versão experimental.
