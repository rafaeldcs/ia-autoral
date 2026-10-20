# Compilar e testar respostas reais do chat

O laboratório opt-in `scripts/chat-code-replay.py` executa cinco artefatos registrados da LocalAuthor: classe e serviço C#, testes xUnit, componente TSX e SQL. O modelo propõe a correção; o controlador inspeciona a sandbox, executa as ferramentas e devolve diagnósticos. Isso não fornece um shell geral ao modo foundation nem aplica mudanças em um projeto de produção.

## Ambiente e limites

A execução usa somente uma imagem Docker local fixada por ID SHA-256, com SDK .NET 10, Node, dependências Next/React/TypeScript, Playwright/Chromium, cache NuGet e PostgreSQL 16 já preparados. Não baixa dependências. A imagem usada no ensaio de 20/10/2026 foi `sha256:21a5e8803b78de04a3d05b04de63c78d10def1cf3035858ba80956dc6ad46211`, disponível nesta instalação como `localauthor-code-repair-lab:1`. Esse ID não é uma distribuição pública nem garante presença em outro computador.

O teste C# tem alvo `net10.0`, SDK 10.0.401. Não é uma execução no runtime .NET 8. O ensaio também usou Node 22.18.0, Next 16.3.5 e PostgreSQL 16.15. Outra imagem precisa ter as ferramentas, caminhos e caches compatíveis; o controlador falha se estiverem ausentes.

Antes de iniciar o container, confere imagem, usuário 10001, rede `none`, raiz somente leitura, ausência de portas/dispositivos, capabilities removidas, `no-new-privileges`, limites de 4 GiB/2 CPUs/512 processos e um único mount somente leitura contendo o avaliador. O worker confirma UID, capabilities, seccomp, raiz e interface `lo` antes de ler o candidato. Código chega via stdin; compilação, navegador e banco usam `/tmp` descartável. Não há pasta do projeto, dados de produção, pesos, token ou socket Docker montados. Não existe fallback de execução no host.

O controlador tem prazo e limite de saída, preserva fontes e respostas originais, logs, TRX, capturas e hashes e remove apenas seu próprio container. O navegador e o servidor Next conversam somente por loopback dentro da sandbox; PostgreSQL usa socket Unix sem escuta TCP.

## Contrato e casos congelados

O candidato JSON tem `schema: 1` e `artifacts` com exatamente `Tarefa.cs`, `TarefaService.cs`, `GeneratedTests.cs`, `ListaTarefas.tsx` e `tarefas.sql`. Cada entrada contém a resposta original em `content`, seu `sha256` UTF-8 e `metadata` com origem `foundation_text`, `possibly_truncated: false` e procedência em `model`. O controlador extrai um único bloco sem corrigir o código. Experiência, conversa e número da resposta acompanham o recibo. Esses metadados permitem rastreabilidade; não são uma assinatura criptográfica do autor.

| Área | Execução real | Casos |
|---|---|---:|
| C# | Restore offline, build, xUnit com TRX: três testes do modelo e treze independentes | 16 |
| TSX | TypeScript estrito, build de produção Next, Chromium real | 9 |
| SQL | Criação real do banco e execução do script e das verificações no PostgreSQL | 13 |

Os casos C# cobrem título inválido, Unicode, estado inicial e conclusão, coleção inteira, ID duplicado/inexistente, cópia da lista e isolamento de instâncias. Os casos de navegador cobrem lista inicial, conclusão observável nas props, clique seletivo, repetição, teclado, largura de 320 px, lista vazia, HTML como texto e exceções. Tornar a conclusão observável é um critério funcional acrescentado antes da primeira execução; compilação sozinha não o verifica. SQL cobre identity, tipo, obrigatoriedade, padrão, valores inválidos, Unicode/aspas, IDs manuais, consulta original ordenada/filtrada, atualização inválida, rollback e IDs positivos.

O modo `mutations` cria cópias com três defeitos controlados do avaliador: conclusão C# sem efeito, atualização TSX para `false` e CHECK SQL permissivo. Exige compilação e a mesma quantidade de casos, com detecção de falha em **cada** área. Falha de infraestrutura ou compilação não conta como detecção comportamental. As cópias defeituosas não são respostas da IA e não substituem os originais.

```powershell
# Usar caminhos privados fora do Git. A saída deve ser uma pasta nova.
python scripts/chat-code-replay.py --candidate D:\Lab\candidate.json --output D:\Lab\run-01 --image sha256:ID_LOCAL_CONFERIDO
python scripts/chat-code-replay.py --candidate D:\Lab\candidate.json --output D:\Lab\controls-01 --image sha256:ID_LOCAL_CONFERIDO --mode mutations
```

Envie os diagnósticos e o código original ao modelo local, peça uma nova resposta completa e preserve-a como outro candidato. Repita a mesma suíte. Não remova casos, não conserte manualmente uma resposta e não conte uma saída impressa pelo modelo como teste executado.

## Resultado do ensaio real

Os originais do chat passaram em C# 16/16 e SQL 13/13. TypeScript e Next compilaram, mas o navegador passou em 5/9: o componente mudava o estado sem comunicá-lo ao usuário. Após receber o diagnóstico, o modelo local registrado produziu outra resposta TSX com estado acessível, botões concluídos desabilitados e indicação visual. Esse candidato passou nos 38 casos. Resposta, experiência, diferença, falha inicial e execução corrigida foram preservadas em armazenamento privado.

A repetição em outro container descartável passou novamente em 38/38 com os mesmos hashes de candidato e avaliador. Os três defeitos comportamentais controlados também foram detectados, mantendo os builds válidos. Uma invocação do operador inicialmente omitiu `--mode mutations` e executou o modo normal: foi preservada e excluída da evidência de mutação. A contraprova válida usa o modo explicitamente registrado como `mutations`.

São exemplos finitos de desenvolvimento com feedback conhecido, não uma avaliação cega, prova de autonomia geral ou garantia de ausência de erros. Não houve atualização de pesos. Os testes de controle do avaliador usam fixtures explicitamente identificadas e não comprovam capacidade do modelo; os resultados acima vêm de código real executado no Docker.
