# Aplicativo intuitivo com servidor central na rede local

Material para consulta, sem autorização de treino de pesos.

A tarefa principal é usar a IA. Não exponha infraestrutura em uma barra permanente no chat. Mova conexão, diagnóstico e publicação para configurações; mantenha descoberta, reconexão e atualização independentes da abertura desse painel. Mostre progresso e falhas acionáveis quando acontecerem.

Um IP não é a identidade do servidor. Guarde o vínculo autorizado por dispositivo, protegido por DPAPI no usuário Windows. Tente o IP salvo, procure o servidor da mesma identidade na sub-rede e confira o certificado antes de enviar autorização. Nunca autorize um servidor desconhecido porque respondeu primeiro, nunca envie a chave no broadcast e nunca regenere credenciais para contornar revogação.

Na máquina servidor, use a instalação local e loopback. Em outro computador, o instalador privado inclui o vínculo, sem exigir importar um arquivo. Não instale outro backend nem copie memória/modelos para cada cliente. Os pedidos continuam chegando ao servidor central.

Reaja à mudança de rede e também repita a verificação periodicamente; serialize tentativas. Recupere falha de carregamento da página mesmo quando a API estiver saudável. Preserve o rascunho e o escopo do projeto ao reconectar. Formulários não salvos em outras telas precisam de proteção separada.

Confira versão, tamanho e hash da atualização, usando o HTTPS autenticado do servidor. Espere o aplicativo ficar livre, avise antes de fechar e ofereça adiamento. Reinicie voluntariamente, mantenha backup e faça rollback se a nova versão não abrir. Aparência salva e seletores do chat não representam formulários pendentes.

Uma ponte web/nativa deve aceitar somente comandos explícitos de origem verificada. Abrir configurações não autoriza publicar, esquecer credenciais, executar processos ou ler arquivos. Não transfira segredos para JavaScript.

## Como verificar

Exercite inicialização lenta, ausência de vínculo, IP antigo, identidade falsa, nonce inválido, revogação e corrupção de credencial. Abra a tela nativa e confira ausência da barra e acesso real às configurações. Teste atualização automática, rascunho bloqueando reinício, download inválido e rollback. Registre quando os testes usam servidores temporários no mesmo computador: isso não comprova troca física de Wi-Fi nem um segundo computador.

Push no GitHub, publicação do executável cliente, atualização do backend e habilitação de pesos são operações diferentes. Não diga que toda alteração de Git ou todo conhecimento importado atualiza automaticamente o código e a inteligência da instalação.
