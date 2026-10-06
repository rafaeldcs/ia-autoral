# Operar o Orbit na homologação ShopAir

## Trabalho diário

Abra https://orbit.hml-app.shopair.com.br. A conta Orbit é independente da conta
ShopAir. A conta inicial é provisionada antes de abrir a rota pública; depois,
o endpoint de primeiro administrador é desabilitado. Crie a equipe na aplicação.

Administrador configura GitHub/branch na aba Código e entregas. Token protegido
no banco; vazio preserva o salvo e Remover token limpa a credencial. Não apague
as chaves de Data Protection: perder essas chaves torna tokens guardados ilegíveis.

Desenvolva no computador de trabalho, faça pull antes de editar, resolva conflitos,
revise, teste no sandbox, faça commit e push. Alterações de `apps/orbit` disparam
**Orbit HML**. Aguarde testes e saúde, não apenas o início do job. Git, Actions e
`/api/health` precisam identificar a mesma revisão.

## CI e servidor

Secrets `ORBIT_HML_DEPLOY_KEY` e `ORBIT_HML_KNOWN_HOSTS` são exclusivos da receita.
No servidor, a chave usa `restrict` e comando forçado: apenas `deploy SHA_COMPLETO`.
Nunca copie chave de administrador para o workflow. O controlador root-owned em
`/usr/local/libexec/orbit-hml-deploy.py` recebe apenas imagens API/Web permitidas;
não executa scripts enviados no pacote.

Destino `/opt/orbit-hml`: `compose.yml`, `Caddyfile`, `.env`, `runtime.json`, `data/`
e backups. Preserve permissões e sigilo. Banco: volume `orbit-hml_db`; chaves:
`data/keys`; Git: `data/repos`, mount de 512 MiB sem execução registrado no fstab.
Gateway somente em `127.0.0.1:8089`, atrás de HTTPS do host. Um worker/instância API.

## Atualizar

1. Faça pull no ambiente de desenvolvimento e resolva conflitos.
2. Peça propostas pequenas à IA local; preserve respostas e devolva os erros.
3. Revise interfaces reais, permissões e testes no sandbox verificado.
4. Faça commit e push para `codex/local-learning-execution`.
5. Confira o workflow Orbit HML e seu artifact de validação.
6. Confira `/api/health`: status ok, PostgreSQL e SHA da entrega.
7. Abra o sistema e consulte o histórico do projeto.

O servidor recusa commit antigo se o topo da branch mudou. Aguarde a revisão nova;
não contorne a regra com force push. Publicação automática após push pela interface
também exige token do repositório com Contents/Actions read/write.

## Recuperar

Sem testes aprovados, não há envio. Sem saúde da revisão nova, imagens anteriores
são restauradas e verificadas. Há backup do banco antes da troca. Migrações devem
ser aditivas e compatíveis; restauração do banco exige decisão do administrador,
conferência do backup e manutenção, não é automática.

Na HML: `docker compose --project-directory /opt/orbit-hml ps` e logs apenas do
Orbit. Não divulgue env/runtime/cookies/tokens/backups. Nunca use prune global;
o controlador retém somente atual/anterior das imagens Orbit. Backups precisam
de retenção/revisão conforme o uso; armazenamento infinito não é prometido.

Falta de espaço, credencial ou conexão deve ser resolvida antes de reenfileirar.
Git interrompido fica em falha para conferência. Fase de entrega interrompida pelo
update é retomada sem rerun. Sem comandos arbitrários, push forçado ou publicação
automática de outros projetos sem receita revisada. Inferência/ensino do modelo
continua no servidor LocalAuthor da rede do proprietário.
