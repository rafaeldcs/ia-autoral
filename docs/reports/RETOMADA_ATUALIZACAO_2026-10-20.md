# Retomada da atualização ao limpar o chat — 20/10/2026

O atualizador consultava versões a cada cinco minutos e registrava qualquer edição de formulário como uma marca permanente. Desfazer a edição não limpava essa marca; aparência já era uma exceção, mas o filtro de conversas não era. A reprodução foi feita em ambiente descartável, sem alterar conversas reais.

O cliente e o instalador passam para **0.3.11**. Uma atualização encontrada e adiada por trabalho pendente agora aguarda localmente, verificando a disponibilidade a cada segundo. Os controles comparam valores atuais com os originais. Apagar a mensagem, desfazer alterações ou reconhecer uma gravação bem-sucedida libera a atualização. O reconhecimento de gravação usa os valores enviados e preserva alterações feitas durante a requisição.

Permanecem os bloqueios de mensagens não enviadas, sincronização pendente, solicitações em execução ou aguardando reconciliação, formulários não salvos, diálogos e telas avançadas. O aviso de 15 segundos, adiamento por 30 minutos, certificado fixado, validação de hash/versão e recuperação da versão anterior permanecem.

## Evidências locais

- `scripts/client-update-smoke.py`: **39 verificações aprovadas**, com WebView2, TLS e troca real do executável. A versão de teste contém o código atual com número inferior. Escrever, apagar, manter um formulário alterado e depois desfazê-lo bloqueia e libera a atualização; ela retoma em até dez segundos e reabre o chat. Também foram executados os cenários de corrupção, versão inválida, rebaixamento, certificado incorreto, dispositivo revogado e recuperação após falha de inicialização.
- `scripts/chat-auto-smoke.py`: **29 verificações aprovadas**, incluindo os scripts exatos de disponibilidade do cliente, campos de texto, checkbox, radio e seleção, filtros, reset, modal, requisição, pedido aceito, checkpoint de recuperação e gravação real das orientações. Geração e pesquisa usam dublês explícitos neste ensaio.
- `scripts/chat-layout-smoke.py`: **65 verificações aprovadas**.
- `scripts/run-tests.py --allow-unavailable-symlinks`: **683 testes; 680 aprovados, zero falhas/erros; três indisponíveis por falta de privilégio de links simbólicos no Windows local**. O CI mantém a execução estrita.
- Instalador conectado: extração dos **15 arquivos**, cliente idêntico ao compilado, conexão protegida por DPAPI e preservação da configuração verificadas em diretório temporário.

Os relatórios detalhados e os pacotes com conexão ficam fora do Git. Não foi testado outro computador físico. Uma janela anterior já aberta permanece com o atualizador antigo até ser fechada; é necessário instalar esta versão uma vez quando ela já estiver presa. Isso não requer desligar o servidor.
