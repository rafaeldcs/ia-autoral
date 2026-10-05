---
id: la-dotnet-sql
version: 1
kind: knowledge
status: material_didatico_nao_homologado
training_allowed: false
reviewed_by: null
---
# C#, .NET e bancos relacionais: procedimento de engenharia

Este documento é conhecimento consultável, não autorização de execução nem comprovação de competência. A aprovação de uso em treinamento é separada.

## Identificar a plataforma antes de mudar código

Ler projeto/solução, TargetFramework, referências, versão da linguagem e dependências. Não aplicar uma solução exclusiva de .NET moderno num projeto .NET Framework sem verificar suporte. Não reescrever a arquitetura inteira para corrigir um bug local.

Preservar contratos públicos, serialização, formatos de data e convenções existentes. Se uma mudança de contrato for necessária, mostrar o impacto e solicitar a decisão pertinente. Não presumir que uma classe com o mesmo nome em outro projeto é a mesma implementação.

## Null, validação e erros

Distinguir ausência, valor inválido, vazio e valor padrão. Uma validação deve representar o contrato de negócio e ser testada nos limites. Retornar sucesso quando houve exceção mascara defeitos. Não capturar toda exceção sem uma política de propagação/registro e não expor segredos em mensagens de erro.

Validar a origem de dados antes de persistir. No teste, usar entradas válidas, inválidas e de fronteira. Não corrigir um comportamento somente pelo nome do teste: ler a asserção e a especificação.

## Async, cancelamento e recursos

Identificar operações de I/O, propagação de CancellationToken, cancelamento observado e liberação de recursos. Evitar transformar um fluxo assíncrono em bloqueio síncrono sem necessidade. Uma exceção de cancelamento não deve ser apresentada como tarefa concluída com sucesso.

Inspecionar o ciclo de vida de serviços e contextos de dados. Não introduzir acesso concorrente a uma instância que não foi projetada para isso. Registrar recursos e escopo antes de propor cache ou singleton como otimização.

## Dados: EF, Dapper, SQL e transações

Escolher a menor alteração compatível com o mecanismo existente. Separar consulta, materialização e mutação. Verificar quantidade de consultas, projeção, paginação, transação e concorrência usando evidência. “Mais rápido” requer medida; uma hipótese de N+1 precisa ser confirmada.

Parametrizar dados de entrada. Não montar SQL executável por concatenação de valores do usuário. Identificadores dinâmicos, quando indispensáveis, precisam de allowlist; não são parâmetros comuns de valores.

## PostgreSQL: último registro e paginação

Definir o significado de “último”: maior identificador ou data mais recente. Usar uma ordem determinística antes de LIMIT; acrescentar desempate quando necessário. Exemplo didático, com nomes fictícios:

```sql
SELECT id, created_at
FROM orders
ORDER BY created_at DESC NULLS LAST, id DESC
LIMIT 1;
```

Esse comando define data não nula mais recente, desempata por ID e retorna no máximo uma linha. Não prova que `id` representa cronologia. A política para registros com data nula deve ser decidida pelo requisito. Para cinco linhas, o limite pode ser cinco, mantendo a ordem pretendida. Referência técnica: PostgreSQL, capítulo LIMIT/OFFSET, T9 no pacote.

## Evidências para uma correção .NET

Ler o teste existente; acrescentar um caso que falhe no original quando aplicável; executar a mudança em ambiente isolado e compatível; confirmar contagem de testes e resultado. Compilação não substitui teste. Se a máquina não possui o ambiente legado requerido, declarar a limitação.

Para fontes semânticas, um componente Roslyn pode ser uma evolução; não apresentar a busca por expressões regulares como resolução completa de símbolos. Escolher ferramentas de acordo com o que está realmente implementado.
