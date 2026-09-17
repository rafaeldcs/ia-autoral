# Segurança — fronteiras e limites da versão 0.1

## Modelo de ameaça

Este é um protótipo **local, de usuário único**, para um operador que controla a máquina. Não é um serviço multiusuário nem uma sandbox certificada. Não exponha a porta por túnel, proxy público ou encaminhamento de roteador. Não use dados reais de clientes antes de revisão e testes no seu ambiente.

Controles implementados:

- Bind explícito em 127.0.0.1, token local comparado em tempo constante, verificação de Host/Origin/Sec-Fetch-Site, ausência de CORS e Content Security Policy.
- Caminhos relativos canônicos, rejeição de traversal, symlinks/junctions conhecidos, hardlinks e caminhos reservados; allowlist de extensões; limite de bytes/arquivos; bloqueio de diretórios gerados e segredos óbvios.
- Separação de escopos no banco; fontes externas são dados, não autorização. Nenhum texto da memória pode modificar permissões.
- Verificação de hashes antes de aplicar. Aprovação vinculada ao conteúdo da proposta. O original permanece intacto enquanto a proposta está somente no workspace.
- Journal e gravação atômica por arquivo. Recuperação após interrupção protege edições posteriores detectadas por hash.
- Coletor HTTPS com allowlist exata, bloqueio de IPs não públicos, conexão ao IP validado com SNI/TLS, validação de redirecionamentos, sem proxy ambiente e sem JavaScript.
- Checkpoints NPZ sem pickle, com tamanho, nomes, formato, tipos, shapes, finitude e digest verificados.
- Backup fora da pasta de dados, servidor parado; restauração em destino vazio, validação de hashes/caminhos e rotação de token. A restauração força offline e runner desativado.

## Limitações importantes

1. Validações de caminho não garantem proteção contra um processo hostil do mesmo usuário que altere diretórios entre checagem e abertura. ACLs/usuário separado e auditoria de condições de corrida ainda são necessários.
2. A detecção de segredos é **heurística**. Pode haver falsos positivos e dados sensíveis não detectados. Revisão humana continua obrigatória.
3. Um conjunto de arquivos não é atualizado em uma única transação atômica do filesystem. O journal permite recuperar cenários cobertos pelos testes, mas não prova tolerância a toda queda física/corrupção do disco.
4. O servidor de referência usa `http.server`/ThreadingHTTPServer da biblioteca padrão. Foi delimitado para loopback; hardening para tráfego hostil, quotas totais e análise de carga estão pendentes.
5. O token em HTTP local não oferece confidencialidade contra software hostil com acesso à máquina. Permissões Windows devem ser verificadas; `chmod` POSIX não substitui ACL NTFS.
6. Conteúdo externo e arquivos do projeto podem induzir erro humano ou prompt injection. A versão atual não libera geração autônoma; uma integração futura do modelo deve manter o mesmo validador independente.
7. Excluir uma fonte do banco não apaga sua influência de pesos já treinados. O software informa `weights_unlearned=false`.
8. A cópia isolada de arquivos é um workspace, não isolamento de processos. O runner nunca executa código no host como fallback.
9. Testes unitários de segurança não são pentest ou auditoria independente. A continuação Windows verificou junctions/hardlinks e recuperação; três testes de symlink ficaram sem privilégio. Container, rede hostil, ACLs e GPU continuam sem auditoria real. Veja `docs/PROGRESS_WINDOWS.md`.

## Executor de verificações

Vem desativado (`docker_image` vazio). Para habilitá-lo, o operador deve fornecer uma **imagem local confiável fixada por digest**, contendo as ferramentas e dependências offline. O programa não faz pull automaticamente.

O comando utiliza rede desabilitada, rootfs read-only, usuário não root, remoção de capabilities, no-new-privileges, limite de processos/memória/CPU, tmpfs limitado e montagem read-only do snapshot. Os arquivos são copiados dentro do container para uma área temporária antes do comando fixo. Não monta o socket Docker dentro do container.

Para .NET, a imagem precisa de SDK e feed local `/opt/localai/offline-nuget`; o bootstrap tenta restore exclusivamente desse feed. Para Python, precisa de Python e as dependências necessárias aos testes. A imagem deve conter `/bin/sh`, `cp` e `mkdir`.

Essas opções foram verificadas na montagem do comando, **não mediante execução real de Docker nesta sessão**. Mesmo containers dependem do kernel/runtime; para código realmente hostil, revise isolamento reforçado/VM e comportamento no Windows antes de habilitar.

O sucesso de `dotnet-build` não é aceito como sucesso de testes. Mesmo `dotnet-test`/`python-tests` com exit code zero não provam que houve casos relevantes: cobertura e teste independente confiável permanecem pendentes. Não trate scripts/testes do próprio projeto como avaliador inviolável.

## Relato de problema

Registre um relatório privado, removendo tokens, credenciais, código de terceiros e dados pessoais. Inclua versão, passos reproduzíveis e resultado esperado. O projeto não configura envio remoto de relatórios. Faça backups em outro dispositivo; uma pasta no mesmo SSD não protege de falha física.
