# Publicação privada no GitHub

## Resultado da tentativa nesta conversa

O conector autenticou a conta `rafaeldcs`. As ações expostas permitiram leitura de perfil/repositórios, mas não criação de repositório, commit ou push. Não havia GitHub CLI autenticado neste ambiente para uma rota alternativa. **Nenhum repositório remoto foi criado e nenhum arquivo foi enviado ao GitHub.**

Foram preparados fonte, testes, workflow e scripts para publicar pelo computador do usuário. Destino proposto: `rafaeldcs/ia-local-autoral`, com visibilidade privada. Não é um endereço remoto cuja existência tenha sido confirmada.

## Publicação a partir do ZIP

1. Instale Git e GitHub CLI pelos canais oficiais no seu computador.
2. Na pasta extraída, configure a sua identidade Git real, caso ainda não esteja configurada.
3. Execute `gh auth login` e conclua a autenticação no seu próprio computador. Não compartilhe tokens.
4. Execute o dry-run e confira nome/conta/visibilidade.
5. Execute a publicação.

```powershell
.\scripts\publish-github.ps1 -DryRun
.\scripts\publish-github.ps1
```

Para outra conta pessoal/nome:

```powershell
.\scripts\publish-github.ps1 -Owner SUA_CONTA -Repository OUTRO_NOME
```

O script exige que o owner corresponda à conta autenticada. Publicação em organização é uma decisão posterior; o bootstrap não amplia permissões nem escolhe uma organização sozinho.

Ele recusa sobrescrever repositório existente e remote `origin` já configurado, inicializa o Git quando necessário, adiciona os diretórios-fonte esperados, verifica certos nomes/extensões sensíveis e usa:

```text
gh repo create OWNER/NAME --private --source=. --remote=origin --push
```

Esse filtro é um cuidado adicional, não um scanner infalível de segredos. Revise os arquivos antes de executar. Não coloque dados em `reports/` ou `docs/` para contornar `.gitignore`.

Se criação e push falharem parcialmente, verifique `gh repo view` e `git remote -v` antes de repetir. Não transforme o repositório em público sem revisão de código, dados e licença.

## Bundle opcional

A entrega também pode incluir um bundle Git com um commit local técnico, sem remoto. Ele preserva o histórico da versão produzida; a autoria técnica de bootstrap não usa sua identidade pessoal. O ZIP, por outro lado, contém apenas os arquivos e permite criar seu próprio commit local ao publicar.

## CI

`.github/workflows/ci.yml` contém testes Python em Linux/Windows e compilação do host .NET. Nenhum desses jobs rodou no GitHub durante a entrega. Resultados futuros devem ser verificados antes de considerar a branch aprovada. Actions depende do GitHub na etapa de desenvolvimento, não do funcionamento local do produto.

Referência oficial do comando: https://cli.github.com/manual/gh_repo_create
