# Pessoas e projetos privados na LocalAuthor

Cada pessoa entra com seu usuário e senha. Os modelos continuam no mesmo servidor da rede local; projetos, pastas, conversas e permissões ficam organizados por perfil no banco desse servidor. Não é preciso instalar ou ensinar novamente o modelo em cada computador.

## Primeiro acesso no servidor

1. Abra o aplicativo LocalAuthor nesta máquina servidor. Ele continua procurando o servidor automaticamente.
2. Na tela **Organize o acesso da sua equipe**, informe seu nome, escolha um usuário e crie uma senha de 12 a 256 caracteres. Confirme a senha no próprio aplicativo.
3. O primeiro perfil será administrador e receberá os projetos e históricos existentes, preservando seus arquivos. Aguarde as tarefas em andamento terminarem caso a configuração avise que a fila está ocupada.
4. Entre em **Minha conta**, no rodapé da barra lateral, para cadastrar as outras pessoas em **Pessoas da equipe**.

Não há senha padrão nem perfis reais pré-cadastrados. A configuração inicial deve ocorrer na máquina servidor; computadores remotos aguardam essa etapa. O administrador escolhe uma senha inicial para cada pessoa, que pode trocá-la em Minha conta.

## Uso nos outros computadores

Instale o aplicativo conectado à mesma rede local e abra-o. O pareamento e a descoberta do endereço do servidor continuam funcionando. Cada pessoa entra com o usuário e a senha do seu perfil; o pareamento de um computador não concede acesso aos projetos de uma pessoa.

O usuário é um identificador de 3 a 32 caracteres, com letras sem acentos, números, ponto, hífen ou sublinhado. Uma sessão pessoal dura até 12 horas; sair, redefinir a senha, desativar ou mudar a permissão administrativa invalida as sessões correspondentes.

Para trocar de pessoa em um computador, use **Minha conta → Sair ou trocar de perfil**. Outras abas da mesma instalação são recarregadas para não continuar mostrando o perfil anterior. Rascunhos salvos pelo cliente atualizado só são restaurados para o perfil correspondente; rascunhos antigos sem autoria só migram para o proprietário do projeto.

## Criar e compartilhar projetos

**Adicionar projeto → Criar uma nova pasta no servidor** cria uma pasta exclusiva dentro do espaço daquela pessoa. O nome é um rótulo; não vira um caminho arbitrário. O endereço do espaço aparece em **Minha conta → Minha pasta no servidor**.

**Vincular uma pasta existente** permite registrar uma pasta própria. Pessoas da equipe só podem vincular pastas dentro do próprio espaço. O administrador também pode vincular outras pastas do servidor, desde que não pertençam a outro espaço nem se sobreponham a projetos registrados. Para trabalhar na mesma pasta, compartilhe o projeto existente.

Projetos novos são privados. O proprietário abre **Orientações do projeto → Gerenciar compartilhamento**, escolhe a pessoa e concede:

| Acesso | O que permite |
|---|---|
| Somente leitura | Consultar o projeto, suas fontes, conversas e resultados |
| Pode editar | Consultar, conversar, solicitar tarefas e alterar conteúdo do projeto |
| Proprietário | As ações anteriores e gerenciar o compartilhamento |

**Compartilhar inclui o histórico e as fontes do projeto.** O filtro **Minhas conversas** organiza a lista por quem iniciou a conversa; ele não torna secreta uma conversa dentro de um projeto compartilhado. O filtro de todas as conversas permite colaborar, com autores identificados. Mensagens anteriores à configuração aparecem como histórico anterior aos perfis.

**Remover acesso** impede novas consultas e operações. Permissões de tarefas na fila são verificadas novamente quando sua execução começa. Isso não cancela automaticamente um trabalho que já começou nem apaga cópias que alguém já tenha consultado.

O administrador gerencia pessoas, biblioteca global, modelos e manutenção. Ser administrador não dá acesso implícito aos projetos privados de outra pessoa pela aplicação. O operador com acesso à conta Windows e aos arquivos do servidor continua sendo um administrador de infraestrutura; estes perfis não substituem permissões do sistema operacional ou isolamento de execução.

## Atualizações, segurança e recuperação

O aplicativo Windows 0.3.8 preserva descoberta do servidor, verificação do certificado e atualizações pela rede. A senha de publicação de atualizações continua sendo uma credencial separada. Atualizar o GitHub não reinicia sozinho o servidor: publique/aplique o código conforme o [passo a passo da rede local](PASSO_A_PASSO_REDE_LOCAL.md), com revisão e validação, e distribua o cliente quando houver alterações nativas.

O transporte continua exigindo o dispositivo autorizado. APIs de projetos também exigem a sessão pessoal; informar um ID de projeto de outra pessoa não concede acesso. O teste de disponibilidade usado pelo aplicativo e pelo supervisor retorna somente que o servidor está pronto quando não há uma sessão pessoal; não revela estatísticas ou projetos.

As senhas são armazenadas como hashes scrypt com sal individual; sessões usam cookies HttpOnly, SameSite e Secure no HTTPS. Senhas e sessões não são enviadas ao modelo nem ficam em armazenamento web. Backups contêm hashes e dados privados: mantenha-os protegidos e fora do Git. A restauração preserva os perfis, mas revoga as sessões recuperadas, exigindo novo login.

Integrações que usavam apenas o token local para consultar projetos precisam agora de login e cookie de uma pessoa autorizada. Não adicione exceções de autenticação para automatizar projetos. A conta do serviço, o pareamento e a senha de publicação não substituem a autorização pessoal.

Para uma pessoa que perdeu a senha, outro administrador pode redefini-la em Minha conta. Não foi criado um mecanismo remoto de recuperação sem administrador. Preserve o acesso administrativo e backups privados do servidor.

## Validação e limites

Os testes de API usam SQLite e scrypt reais; os testes de interface usam identidades descartáveis em navegadores separados. A verificação do gateway usa HTTPS real e dois dispositivos pareados de laboratório nesta máquina. Um segundo computador físico não foi testado nesta entrega. A contribuição pontual do modelo local foi uma função de matriz de permissões, revisada e executada em sandbox antes da integração; isso não é um novo treinamento de pesos nem prova de autonomia geral.

Parâmetros de armazenamento de senha seguem a referência [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). A implantação não introduz serviços remotos de IA, telemetria ou novas dependências de infraestrutura.
