# Interface clara para projetos e conversas

Material revisado para consulta. Importar este texto não modifica pesos nem comprova autonomia do modelo.

Antes de desenhar, identifique as tarefas reais e sua frequência. No LocalAuthor, a tarefa principal é conversar em um projeto; manutenção de conexão, exemplos de laboratório e configuração são tarefas secundárias.

- Use uma única lateral para projetos e conversas do projeto selecionado. Mostre a seleção atual com texto e estado acessível. Nomes longos podem ser abreviados visualmente; mantenha o nome completo disponível.
- Reserve o centro para histórico e mensagem. Cada área controla sua própria rolagem; a caixa de mensagem permanece visível em janelas baixas.
- Agrupe ferramentas secundárias em um painel com nomes e descrições. Links navegam, botões executam ações. Nunca adicione um botão decorativo que pareça funcionar.
- Separe as evidências do navegador do histórico de chat. Capturas e interpretação têm origem e limites explícitos. No celular, abra um painel inteiro, com fechamento acessível.
- Mantenha os modos reais visíveis: guia estruturado, consulta de memória, investigação e modelo experimental são capacidades diferentes. Uma interface inspirada no Codex não concede capacidades do Codex.
- Preserve rascunho, formato e modo ao abrir ou fechar navegação e ferramentas. Uma sugestão preenche o campo para edição; não envia automaticamente.
- Na navegação móvel, mova o foco para dentro, mantenha Tab/Shift+Tab no painel, feche com Escape e devolva o foco ao botão de abertura. Diálogos têm título acessível, fechamento e foco restituído.
- Explique a primeira ação quando não houver projetos. Desabilite apenas as ações indisponíveis; nunca esconda uma falha ou transforme ausência de capacidade em sucesso.
- Renderize mensagens e código como texto inerte. Preserve acentos, aspas, comentários, espaços e quebras de linha; não use conteúdo recebido como HTML.
- Não peça ao usuário para escolher texto ou código. Identifique sinais fortes, como cercas Markdown, declarações de linguagem e JSON válido, mantendo prosa comum como texto. A classificação é uma indicação de apresentação: não executa, corrige nem reescreve o conteúdo e pode falhar em trechos ambíguos. O servidor confirma a classificação; clientes antigos continuam compatíveis.
- Mantenha a caixa de mensagem compacta quando vazia, crescendo com o conteúdo até um limite com rolagem própria. Use uma linha de controles, envio com nome acessível e contagem apenas próxima ao limite. Preserve Enter para nova linha e Ctrl + Enter para enviar. Desabilite enviar quando vazio, sem perder rascunhos ou apagar conteúdo acima do limite.
- Adote cores, espaçamento, campos e botões consistentes entre chat, marketing, modelos e ferramentas avançadas.
- Voz começa somente por uma ação explícita, com explicação do destino do áudio, captura visível, silêncio da resposta e encerramento acessíveis. Não sobreponha rascunhos. Desligue o microfone durante transcrição, geração e leitura; libere-o ao sair, ocultar a página ou falhar. Proteja sessões e contexto contra callbacks atrasados.
- Transcreva somente no servidor local autenticado, descarte áudio e use apenas síntese local. Voz não concede ferramentas nem permissão para executar ações. Teste silêncio, duração, rede/credencial, microfone negado, ausência de voz/modelo, concorrência, interrupção, histórico e preservação do texto. Declare dublês e diferencie fala sintética de microfone físico; não confunda inferência e consulta com treinamento.

## Verificação antes da entrega

Teste criar projeto, enviar uma orientação, salvar preferências, iniciar nova conversa e recuperar o histórico. Confira diálogos, painel do navegador e exemplos de código. Redimensione para 1440, 1280, 1024, 768, 390 e 320 pixels. Verifique ausência de rolagem horizontal, compositor dentro da janela, foco, rascunhos e exceções JavaScript. Inspecione capturas desktop e mobile; teste aprovado sem inspeção não garante composição visual boa.

Registre quais verificações usam modelo real, quais usam guia e quais usam dublês. Falha da infraestrutura bloqueia a execução correspondente; não execute código gerado no host como alternativa.
