# Conversação e voz — 20/10/2026

O modelo local respondeu a nove pedidos antes do ajuste e a doze pedidos na tentativa final, incluindo variações novas, com os mesmos pesos Qwen3.5 4B Q8, revisão `e87f176479d0855a907a41277aca2f8ee7a09523`, contexto 4096 e saída máxima 1536 tokens, em RTX 2060 6 GB. Não houve download, API de IA externa ou treinamento de pesos. O script conserva os resultados em pastas privadas distintas.

## Comportamento observado

| Caso | Antes | Depois |
| --- | --- | --- |
| “Obrigado, ajudou muito!” | Explicação sobre não haver novos pedidos ou fontes para verificar | “De nada! Fico feliz em ter sido útil.” |
| “Valeu, até amanhã!” | Explicação sobre não haver nada para executar | “Fico feliz que tenha sido útil!”; ainda não retribuiu explicitamente o “até amanhã” |
| Pedido para simplificar, sem assunto anterior | Resposta extensa com nota técnica sobre memória | Acolhimento breve e pergunta sobre a dúvida |
| Agradecimento junto de pergunta sobre API | Explicação em duas frases | Explicação em duas frases; não descartou a pergunta |
| Agradecimento em inglês | Pedido burocrático de nova tarefa | “You're welcome! How can I assist you further?” |
| Pergunta de continuação | Aurora/Kanban | Aurora/Kanban, com histórico incluído |
| Pergunta sobre ter executado código/treinado | Negou ações não realizadas | Continuou negando ações não realizadas |

Revisão interna desses exemplos, sem avaliador semântico independente. Isso não comprova qualidade universal de conversa. As tentativas intermediárias foram preservadas: uma delas repetia a frase de exemplo em contexto inadequado e desrespeitou o idioma solicitado; a orientação final retirou a frase pronta e voltou a responder nos idiomas pedidos. As três variações adicionais verificaram outro agradecimento, espanhol e uma pergunta comum sobre DNS. Mesmo após o ajuste, o modelo pode repetir ofertas de ajuda, deixar de retribuir uma despedida explicitamente e dar respostas que precisem de revisão.

## Continuação com perfis de trabalho

Uma checagem adicional com histórico de uma tarefa e perfis desenvolvimento/marketing encontrou uma falha: o modelo agradecia, mas retomava o planejamento sem novo pedido. A correção seleciona um contexto menor para expressões sociais inequívocas: não inclui a tarefa anterior, as fontes ou a orientação operacional; preserva as preferências explicitamente guardadas. O modelo continua gerando a resposta. Não há resposta de agradecimento pré-gravada nem execução de ferramentas.

Pedidos mistos (“Obrigado! Qual foi a pergunta anterior?”), código, aprovações e expressões não reconhecidas mantêm o fluxo normal de contexto. Novos testes verificam essa distinção, as preferências e a contabilização de omissões. O histórico salvo continua intacto. Os ensaios privados preservam os seis resultados que revelaram a falha e a repetição após a correção.

Na repetição, oito pedidos reais cobriram agradecimento, saudação, simplificação e pergunta de continuação nos dois perfis. Os dois agradecimentos passaram a receber somente “De nada! Fico feliz em ter sido útil.”; as saudações deixaram de retomar planejamento. Os doze pedidos gerais também foram repetidos; Aurora/Kanban foi recuperado com duas mensagens de histórico no pedido misto. A verificação da seleção de preferências guardadas é contratual; não foi feita nova avaliação semântica de todos os tipos de preferência.

## Voz real e interface

Três arquivos sintéticos produzidos pela voz Maria Desktop do Windows foram enviados ao Whisper small q5_1 registrado, em contêiner verificado sem rede. As transcrições foram respondidas pelo modelo real, mantendo os turnos anteriores no contexto.

- “Bom dia! Tudo bem?” → “Bom dia. Tudo bem.” → “Bom dia! Tudo bem por aqui, e com você?”
- Projeto Aurora com Kanban → reconhecimento incorreto de Kanban como **Cambam**. Não houve correção automática disfarçada.
- Pergunta seguinte sobre nome e método → resposta manteve Aurora e o termo incorretamente reconhecido.

Transcrição: 7,75–7,96 segundos por fala. Geração dos três turnos de áudio: 0,81–1,74 segundo por turno, com o modelo já carregado. Carregamento inicial: 25,78 segundos. Esses tempos excluem captura, pausa de envio, transferência e duração da leitura. Não há garantia de latência em outro equipamento ou com múltiplas pessoas.

O teste Chromium/Edge usa microfone sintético real e dublês declarados de transcrição, modelo e leitura: 23 verificações passaram, incluindo repetição automática do ciclo, contexto, interrupção da leitura, callbacks duplicados e de sessão antiga, leitor travado, cancelamento, permissão negada, microfone liberado e tela estreita. Esse teste de integração da interface não comprova qualidade dos modelos nem testa um microfone físico.

Um ensaio separado no Edge usou reconhecimento, modelo e voz reais, sem substituir suas respostas ou eventos de conclusão. A voz selecionada foi Microsoft Daniel em português, marcada como local pelo navegador. A resposta terminou e o microfone reabriu. Os primeiros ciclos mediram aproximadamente 78 segundos, incluindo uma gravação sintética em repetição que atingia o teto de 30 segundos. O roteiro foi corrigido para acrescentar uma pausa de dois segundos à entrada sintética, permitindo que o detector real de silêncio encerrasse a fala naturalmente. Isso é ajuste da bancada, não redução artificial da latência do produto.

Na repetição do primeiro ajuste foram completados dois turnos reais e três aberturas de escuta, em 68,91 segundos no total. O segundo turno incluiu duas mensagens anteriores no contexto. Da abertura do microfone ao início da leitura, foram aproximadamente 43 segundos no primeiro turno e 14 segundos no segundo. A entrada sintética repetiu a mesma saudação; a continuidade com informações diferentes foi verificada separadamente nos três áudios Aurora/Kanban. Não houve erro JavaScript no ciclo real. O evento de conclusão do leitor comprova a execução do fluxo, sem avaliar a qualidade acústica ou gravar o som de saída do navegador. Com a seleção de contexto social, saudações simples podem omitir esse histórico deliberadamente; ele continua disponível para perguntas de continuação.

Validação final: 708 testes executados, 705 passaram, zero falhas/erros e três testes de symlink não executados por privilégio do Windows. A correção de contexto social acrescentou três testes. O ensaio de layout passou em 65 verificações. O primeiro ensaio da suíte detectou excesso de tamanho da orientação; a orientação foi compactada e o teste original permaneceu inalterado. Os registros anteriores foram preservados.

Foi acrescentado “Interromper e falar”. Uma leitura sem conclusão também deixa de prender a sessão indefinidamente. Ouvir e falar continuam alternados, sem escuta simultânea e sem barge-in automático.

## Repetição e limites

Execute `scripts/voice-ui-smoke.py` para a interface e `scripts/conversation-real-check.py --help` para os ensaios reais com modelos já registrados. `scripts/voice-real-smoke.py --run-real --home CAMINHO --audio WAV_SINTETICO --output PASTA_NOVA` percorre a interface e os motores reais com microfone sintético; por padrão verifica duas respostas e o retorno à escuta. Não execute simultaneamente dois ensaios que carreguem o modelo na GPU de 6 GB. Áudio sintético e resultados devem ficar fora do Git. O relatório privado preserva as respostas completas e hashes dos arquivos de entrada. Corrija reconhecimento incorreto por texto no chat; não trate transcrição como evidência de compreensão perfeita.

O cliente instalado carrega a interface do servidor. Esta alteração web/Python não muda o instalador nem os modelos; exige recarregar a janela e reiniciar o backend para aplicar o novo prompt. Não foi realizado teste em outro computador nesta entrega.
