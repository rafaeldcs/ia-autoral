# Perfis pessoais e projetos privados — validação inicial de 19/10/2026

> Registro histórico da primeira entrega, substituída depois pelo pedido de identificação somente por nome. A versão atual não pede usuário/senha e não oferece sigilo entre pessoas que podem selecionar o perfil de outra. Consulte [o guia atual](../PERFIS_E_PROJETOS.md). Os testes abaixo descrevem aquela primeira revisão, não certificam autenticação pessoal na versão por nome.

Solicitação: organizar o uso da mesma LocalAuthor por várias pessoas. Decisão do proprietário: projetos privados por padrão, com compartilhamento explícito. A entrega preserva uma única instalação de modelos no servidor e acrescenta identidade pessoal, propriedade de projetos e autorização na API.

## Comportamento entregue

- Primeiro administrador configurado interativamente no servidor, recebendo os projetos e históricos existentes. Nenhuma senha padrão ou pessoa real foi cadastrada automaticamente.
- Administração de pessoas, login, saída, troca/redefinição de senha, desativação e revogação de sessões; proteção do último administrador ativo.
- Pastas gerenciadas por pessoa, bloqueio de vínculo sobreposto ou em outro espaço, projetos próprios e compartilhados identificados na navegação.
- Compartilhamento somente pelo proprietário: leitura, edição e remoção. Ser administrador não concede leitura implícita de projetos privados.
- Autoria de conversas/mensagens e filtro pessoal. Compartilhamento inclui todo o histórico e as fontes do projeto; o filtro pessoal não é uma barreira de privacidade dentro de um projeto compartilhado.
- Autorização por projeto para conversas, tarefas, jobs, fontes, navegador, mídia, voz, marketing e leads. A execução de jobs revalida o autor e suas permissões ao começar.
- Sessões HttpOnly e Secure no HTTPS, transporte pareado separado da pessoa e nenhum compartilhamento de cookies entre requisições do cliente HTTP do gateway. Fachada .NET opcional também encaminha cookies e a identificação esperada da aba.
- Disponibilidade mínima acessível ao dispositivo antes do login, sem estatísticas privadas, para preservar descoberta, inicialização do servidor e clientes anteriores.
- Cliente/instalador Windows 0.3.8: proteção de rascunhos por perfil e adiamento de atualização enquanto há diálogo ou login aberto. A interface mantém compatibilidade com clientes antigos que marcavam campos de login como alterações pendentes.
- Restauração de backup mantém pessoas e hashes, mas revoga sessões recuperadas. A verificação de fila para manutenção usa leitura local do SQLite, sem exceção HTTP de autenticação.

## Participação do modelo local

A LocalAuthor foi acionada em conversa própria para propor a função pura `can_access_project`. A primeira proposta não rejeitou subclasses de texto: **113/120 casos passaram, sete falharam**. A devolutiva descreveu o problema e solicitou uma correção. A segunda proposta passou em **120/120 casos**, incluindo tipos inválidos, permissões desconhecidas e ausência de acesso administrativo implícito.

Os candidatos foram executados primeiro em sandbox Docker verificada, sem rede, com raiz somente leitura, usuário não privilegiado, sem volumes ou capabilities, limites de CPU/memória/processos e canários de isolamento. Só a versão aprovada foi integrada. A camada completa de autenticação, persistência, interface, gateway e revisão foi implementada pelo agente de desenvolvimento; não se atribui esse trabalho inteiro ao modelo local.

O caminho de um manifesto privado do modelo foi corrigido para sua localização física existente, verificando os hashes do inventário. Os pesos não foram substituídos, baixados ou treinados nesta atividade. A conversa e os recibos completos ficam privados no servidor e passam ao primeiro proprietário quando os perfis forem configurados.

## Execuções locais

| Verificação | Evidência observada |
|---|---|
| Suíte Python, Windows/Python 3.14.7 | 644 testes: 641 aprovados, zero falhas/erros, três não executados por privilégio de links simbólicos |
| Identidade/API com SQLite e scrypt reais | 16 testes dentro da suíte; sessão, ACL, IDs de outra pessoa, redefinição, expiração, restauração e revalidação da fila |
| Navegador: perfis em contextos separados | 17 verificações aprovadas, incluindo leitura/edição/revogação, troca em várias abas e larguras 320/390 |
| Layout principal | 65 verificações aprovadas |
| Outras interfaces | Avançada: 10 fluxos; foundation: 15; marketing: oito; leads: nove; voz: 19 verificações aprovadas |
| Gateway nativo, TLS e dois dispositivos de laboratório | 10 verificações aprovadas, com sessões independentes, cabeçalhos de origem controlados pelo gateway e disponibilidade antes do login |
| Fachada .NET opcional | Build e 16 verificações reais aprovadas, incluindo encaminhamento/revogação de sessão e indisponibilidade do backend |
| Atualizador nativo | 33 verificações aprovadas: autenticação pelos formulários reais, rascunho preservado, atualização e reabertura, integridade, versão, certificado, downgrade, revogação e rollback |
| Instalador conectado | Extração de 13 arquivos com hashes conferidos; conexão criada protegida por DPAPI e preservada em nova execução |
| Ativação neste servidor | Encerramento cooperativo, backup SQLite íntegro, novo hash do gateway verificado, HTTPS real e 13 projetos preservados; zero perfis reais criados pelo executor |

Os testes de voz e interfaces de geração usam dublês explícitos onde indicado pelos seus relatórios; não qualificam qualidade de áudio, texto ou imagem. O teste pontual do modelo local qualifica somente a função e os casos descritos. A geração de marketing anterior permanece fora do escopo desta mudança.

## Problemas encontrados e correções

Uma resposta antiga da lista podia sobrescrever o filtro de conversas escolhido mais recentemente; foi acrescentado controle de versão da consulta. Cancelar a captura de voz no Windows podia registrar uma conexão abortada como erro interno; a interrupção de transporte agora é tratada normalmente. O preenchimento da autenticação podia bloquear atualizações em clientes antigos; a interface restaura o estado de edição anterior ao login, preservando alterações legítimas já pendentes.

O ensaio nativo exigiu atualizar o driver de teste para preencher os formulários reais e reconectar ao WebView substituído pelo atualizador. A depuração é habilitada exclusivamente nos subprocessos descartáveis do ensaio e vinculada ao loopback; não foi habilitada no aplicativo do usuário. Tentativas anteriores e seus erros foram preservados nos registros privados.

A manutenção inicialmente recusou emitir Ctrl+C porque havia um processo de inferência Docker anexado ao console. Após conferir o vínculo ao backend, imagem e ausência de rede, e confirmar a fila ociosa, o runtime local foi parado. O encerramento cooperativo do backend então passou, sem forçar o processo que mantém o banco. O modelo pode ser recarregado pelo fluxo normal quando necessário.

## Distribuição e limites

O servidor desta máquina foi atualizado e o cliente 0.3.8 publicado no canal local de atualizações. O instalador privado conectado foi renovado, preservando a conexão e uma cópia anterior para recuperação. Binários, credenciais, backups, screenshots e relatórios completos ficam fora do Git.

A revisão de código acompanha este relatório; o CI é executado no commit publicado e deve ser conferido pelo SHA desse commit. Os três casos de links simbólicos precisam de execução no CI ou em ambiente com o privilégio necessário. Não se declara cobertura universal ou que todos os computadores físicos foram homologados: o teste de rede usou dois dispositivos lógicos nesta máquina, e um segundo computador físico permanece sem ensaio.

O proprietário ainda precisa criar seu primeiro perfil no aplicativo do servidor e cadastrar as demais pessoas. O guia de uso está em [PERFIS_E_PROJETOS.md](../PERFIS_E_PROJETOS.md). Revogar acesso bloqueia novas operações e o início de jobs, mas não cancela automaticamente uma execução já iniciada ou recupera conteúdo que já foi lido. Administradores do Windows continuam confiáveis no nível de infraestrutura; os perfis da aplicação não isolam o sistema operacional.
