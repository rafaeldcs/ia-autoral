# Orbit — projetos, Git e entregas

C#/.NET 10, Next.js 16 e PostgreSQL. Quadros Scrum/Kanban, backlog, sprints,
gráficos de fluxo, equipe e auditoria. **Código e entregas** hospeda um repositório
Git privado por projeto e também pode associar GitHub para pull, push e publicação.

## Identidade visual

Login e barra lateral usam o mesmo componente `OrbitBrand`; o ícone da aba
compartilha o símbolo. A proposta, versões e processo da LocalAuthor estão em
[marketing/orbit/brand](../../marketing/orbit/brand/README.md).

## Repositório do próprio Orbit

Abra Código e entregas → **Repositório** e use **Criar repositório** como administrador
ou gestor. Abra **Clonar repositório** para copiar a URL e **Acesso Git** para criar
seu token pessoal; colaboradores podem
marcar Permitir push, leitores só podem gerar acesso de leitura. No Git, use seu
e-mail Orbit como usuário e o token como senha. Não coloque o token na URL.

Clone, faça commits localmente e envie para `main`. O Orbit guarda o histórico no
servidor, exibe arquivos/branches/commits e relaciona as chaves às tarefas. Token
expira em 30 dias e pode ser revogado em Acesso Git. **Arquivos**, **Histórico** e
**Acesso Git** mostram uma área por vez. O token do Orbit é independente
do token configurado em **GitHub e publicação**. Todos os usuários ativos do workspace podem ler;
não há ACL de membros independente por projeto nesta versão.

Limites: 20 MiB por requisição/push, 32 MiB por resposta Git, 512 MiB compartilhados
com os checkouts; prévia textual até 16 KB, 200 entradas por árvore, 100 branches,
20 commits e enumeração de objetos limitada. Para projetos maiores, clone para
consultar e dimensione armazenamento/limites com revisão. Force push e exclusão
de branches são recusados. Não há Git LFS, SSH Git, pull requests ou editor online.

Push para a hospedagem própria armazena o código; a receita de deploy já entregue
continua sendo disparada no GitHub. Novos repositórios precisam de pipeline revisado.

O experimento original foi preservado. `README_EXPERIMENTO_LOCAL.md` é o registro
histórico e descreve a versão antiga; seus comandos não são o procedimento desta
entrega. Novos módulos foram propostos pelo Qwen3-8B local, com especificação,
revisão e montagem de trechos pelo Codex. Testes e infraestrutura são do Codex.
Veja `LOCAL_AI_PROVENANCE.json` e `STATUS_ENTREGA.md`; não houve alteração de pesos.

## Usar

1. Abra https://orbit.hml-app.shopair.com.br e entre na conta da equipe.
2. Crie projeto e tarefas. Escolha Scrum/Kanban em Configurar método.
3. Inclua a chave da tarefa no assunto do commit: `ORB-1 Corrige autenticação`.
4. Como administrador, abra Código e entregas → **GitHub e publicação** →
   **Configurar conexão GitHub**, configure URL HTTPS terminada em
   `.git`, branch e token GitHub opcional. Token vazio preserva o salvo; a opção
   Remover token apaga a credencial. Data Protection protege o token no banco.
5. Administradores/gestores podem Atualizar código, Enviar commits e Publicar
   homologação. Confirme a revisão e acompanhe o histórico e o link do pipeline.
   Colaboradores/leitores podem consultar.

Pull exige árvore limpa e avanço direto; push nunca usa força. Desenvolvedores
criam commits em seus ambientes; esta versão não tem editor online. Papéis são
globais no workspace. Ative publicação automática após push para o próprio Orbit:
repositório `rafaeldcs/ia-autoral`, branch `codex/local-learning-execution`.
Outros repositórios permitem Git, mas exigem receita revisada para deploy.

Para push e acompanhamento de Actions pela interface, use token exclusivo do
repositório com Contents read/write e Actions read/write. Não reutilize login
ShopAir como token. CI usa chave SSH exclusiva e restrita, guardada em secrets.

## Validar e publicar

```text
docker build -f apps/orbit/ops/qa.Dockerfile -t orbit-ci-qa apps/orbit
python apps/orbit/ops/build_verified.py --image orbit-ci-qa --sha SHA_COMPLETO
```

Dependências são preparadas separadamente. Código roda apenas em sandbox Linux
verificado, sem rede/privilégios, com fontes somente leitura e limites de recursos.
Evidências ficam em `artifacts` (ignorado pelo Git) e no artifact do Actions.

Push na branch de trabalho dispara `.github/workflows/orbit-hml.yml`, inclusive
quando só a documentação mudou, para que todo SHA exibido no Git tenha pipeline.
HML recebe
imagens por SHA, verifica saúde e restaura as anteriores se necessário. A troca
provoca breve reinício do Orbit; o worker retoma entregas sem iniciar novo deploy.
Banco separado, chaves persistentes, Git limitado a 512 MiB; não altera aplicações
ShopAir existentes. Inferência LocalAuthor permanece na máquina local.

Procedimento completo: [ops/PASSO_A_PASSO_HML.md](ops/PASSO_A_PASSO_HML.md).

A UI direta na porta 3100 é o preview de desenvolvimento. Git nativo por HTTPS
usa o gateway configurado em `ops/Caddyfile`; para clone/push desta entrega,
use a URL mostrada no endereço HML acima.
