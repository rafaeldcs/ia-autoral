# Orbit — projetos, Git e entregas

C#/.NET 10, Next.js 16 e PostgreSQL. Quadros Scrum/Kanban, backlog, sprints,
gráficos de fluxo, equipe e auditoria. **Código e entregas** associa GitHub ao
projeto, relaciona commits às tarefas e acompanha pull, push e publicação.

O experimento original foi preservado. `README_EXPERIMENTO_LOCAL.md` é o registro
histórico e descreve a versão antiga; seus comandos não são o procedimento desta
entrega. Novos módulos foram propostos pelo Qwen3-8B local, com especificação,
revisão e montagem de trechos pelo Codex. Testes e infraestrutura são do Codex.
Veja `LOCAL_AI_PROVENANCE.json` e `STATUS_ENTREGA.md`; não houve alteração de pesos.

## Usar

1. Abra https://orbit.hml-app.shopair.com.br e entre na conta da equipe.
2. Crie projeto e tarefas. Escolha Scrum/Kanban em Configurar método.
3. Inclua a chave da tarefa no assunto do commit: `ORB-1 Corrige autenticação`.
4. Como administrador, abra Código e entregas, configure URL HTTPS terminada em
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

Commit/push em `apps/orbit` dispara `.github/workflows/orbit-hml.yml`. HML recebe
imagens por SHA, verifica saúde e restaura as anteriores se necessário. A troca
provoca breve reinício do Orbit; o worker retoma entregas sem iniciar novo deploy.
Banco separado, chaves persistentes, Git limitado a 512 MiB; não altera aplicações
ShopAir existentes. Inferência LocalAuthor permanece na máquina local.

Procedimento completo: [ops/PASSO_A_PASSO_HML.md](ops/PASSO_A_PASSO_HML.md).
