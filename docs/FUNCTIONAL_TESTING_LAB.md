# Testes funcionais produzidos pelo modelo local

Este laboratório ensina uma habilidade restrita: produzir corpos curtos de testes Playwright para nove contratos conhecidos do Orbit. Os pesos próprios são efetivamente treinados; as respostas originais são preservadas e executadas sem reparos. Isso não qualifica o modelo para inventar uma suíte completa a partir de qualquer pedido em linguagem natural.

## Como a habilidade funciona

O chat mantém o modelo anterior para os pedidos existentes. Mensagens iniciadas por `Teste JS h:` usam o candidato funcional somente depois da aprovação de 36 execuções e da detecção de 36 defeitos controlados. O hash do checkpoint é conferido contra a certificação. Essa seleção acrescenta uma especialização; não substitui todo o conhecimento anterior.

Exemplo de pedido, incluindo uma quebra de linha ao final:

```text
Teste JS h: Projeto P43, tarefa T43: concluir, recarregar, status done.
```

A saída é um corpo de teste que depende dos auxiliares `h` do laboratório, e não um arquivo Playwright autossuficiente. Os exemplos exatos estão em `qa/functional-lab/course.py`. Os auxiliares em `prefix.js` executam ações e preparam dados; as asserções pontuadas fazem parte do trecho gerado pela IA. Os pedidos fora desses contratos não têm garantia de resultado. O chat gera propostas, não executa código automaticamente.

| Família | Verificação | Defeito controlado |
| --- | --- | --- |
| Login | `/me` 200 autenticado e 401 depois do logout | Aceitar usuário sem sessão |
| Senha de conta Orbit | 11, 12, 128 e 129 caracteres: 400, 201, 201, 400 | Aceitar todos os tamanhos |
| Permissões | Leitor recebe 403 e gestor 201 ao criar sprint | Permitir criação sem papel adequado |
| Fluxo da tarefa | Criar projeto/tarefa, concluir, recarregar e consultar `done` | Reverter conclusão para `todo` |
| Kanban | Duas criações simultâneas disputam uma vaga: 201 e 409 | Permitir exceder WIP |
| Estatística | Iniciar/concluir tarefa produz uma entrega | Retornar contagem errada |
| Celular | Quadro 390 × 844 sem rolagem horizontal | Forçar largura excessiva |
| Recuperação | Tarefa persiste após reiniciar API | Perder tarefa no reinício |
| Scrum | Criar, iniciar e encerrar sprint | Recusar encerramento |

São quatro variantes numéricas por família, totalizando 36 casos. Não são 36 famílias inéditas. Login e celular, por exemplo, têm grande sobreposição entre variantes. As criações e alterações usam a API real; recarga e celular também usam o navegador real. A senha de conta Orbit tem máximo de 128 caracteres; a senha de publicação LocalAuthor é outra regra, com máximo de 256. Este curso não deve confundir as duas.

## Aprendizado e avaliação

O treino autorizado usa 828 exemplos sintéticos novos, 810 exemplos antigos de revisão e 18 exemplos de validação. Os números 43, 47, 61 e 79 são reservados para os 36 casos finais. A seleção do checkpoint usa somente a validação, nunca a pontuação final. Os casos finais são variantes das famílias ensinadas; a avaliação mede essa generalização restrita.

Na execução de 17/09/2026, foram concluídos 6.000 passos e selecionado o passo 5.000 pela validação. O candidato produziu 36/36 respostas finais exatas. Na regressão de geração antiga, acertou 34/36: por isso ele não substitui o modelo geral. O hash selecionado é `0fca80a142b240c09f5736dfcc88b1678a5c83945802f61f8b5ba1c005175175`.

O avaliador aceita apenas os trechos exatos do contrato congelado. Uma implementação alternativa, mesmo válida, é rejeitada nesta versão. Isso é uma restrição explícita de execução, não um avaliador geral de programas. O código do avaliador, a escolha dos cenários, os auxiliares e as referências são de Codex. A IA produz apenas os trechos submetidos à avaliação; não planejou ou acionou toda a bateria autonomamente.

## Infraestrutura e isolamento

O laboratório incorpora os fontes reais do Orbit (.NET 10 e Next.js) e um PostgreSQL 16 descartável. A simulação profissional separada usa PostgreSQL 18. O build depende de Docker, repositórios de pacotes .NET/npm/Ubuntu e da imagem local `localauthor-testing-lab:1`; não usa APIs de IA ou pesos externos. O script copia apenas os fontes permitidos e mantém um manifesto de hashes no contexto de build.

Cada teste e cada mutante rodam em contêiner novo, não privilegiado, usuário 10001, raiz somente leitura, capacidades removidas, `no-new-privileges`, rede externa desativada e limites de CPU, memória e processos. Somente o trecho é montado, em leitura. Projeto, credenciais, banco real e socket Docker não entram no contêiner. Navegador, frontend, API e banco conversam apenas pelo loopback interno. Canários verificam as restrições antes de aceitar execução. Sem sandbox, não há execução alternativa no Windows.

A execução normal precisa conter um teste aprovado e nenhum ignorado. O mutante precisa falhar por uma asserção; um erro de inicialização ou uma suíte vazia não conta como detecção. Nove referências são executadas antes do candidato, na mesma imagem Docker imutável. Duplicação de casos, mudança de código, imagem diferente ou checkpoint alterado bloqueiam a ativação. A primeira tentativa de infraestrutura falhou por sintaxe no gancho SQL de mutação; foi preservada, corrigida e as nove referências foram repetidas antes de executar as respostas da IA.

## Reprodução

Com Python do projeto, Docker e os fontes do Orbit disponíveis:

```powershell
python scripts/build-functional-lab.py --orbit-root C:\caminho\jira-local-experimental
python scripts/train-functional-tests.py --orbit-root C:\caminho\jira-local-experimental
python scripts/evaluate-functional-tests.py --report C:\caminho\privado\report.json --references
python scripts/evaluate-functional-tests.py --report C:\caminho\privado\report.json
python scripts/activate-functional-tests.py --report C:\caminho\privado\report.json
python scripts/verify-functional-chat.py --orbit-root C:\caminho\jira-local-experimental
```

Os dados, pesos e evidências ficam fora do Git, em `%LOCALAPPDATA%\LocalAuthor`. A ativação recusa substituir uma certificação existente; é preciso preservar e revisar a anterior. O servidor precisa executar a versão do código que contém o seletor funcional. A verificação final do chat compara as respostas byte a byte com os trechos já executados, sem contar essa comparação como nova execução funcional.

## Limites da conclusão

“100%” só pode se referir aos casos enumerados e executados. Esta bateria não cobre todas as combinações de papéis, expiração de sessão, todas as estatísticas, toda acessibilidade, navegadores, equipamentos, falhas de rede ou volumes de produção. Asserção de largura de tela não substitui avaliação de usabilidade. Persistência após reiniciar API não é recuperação de desastre do banco.

Os quatro pedidos livres de xUnit/Playwright da auditoria inicial continuam sem respostas utilizáveis, mesmo depois de corrigir o limite de saída. Eles não foram reclassificados como aprovados por causa dos novos contratos `h`. O modelo ainda não demonstra competência geral ou autonomia equivalente ao Codex. Ver [auditoria inicial](LOCAL_MODEL_TESTING_AUDIT.md) e os resultados desta entrega em [verificação completa](FULL_VERIFICATION_20260917.md).
