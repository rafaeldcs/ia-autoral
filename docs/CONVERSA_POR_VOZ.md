# Conversa por voz na rede local

Escolha um projeto no chat, clique no **microfone → Começar conversa** e permita o microfone quando solicitado. Uma pausa de aproximadamente 1,5 segundo envia a fala. A LocalAuthor responde, lê a resposta e volta a ouvir. **Encerrar voz** libera o microfone e solicita cancelamento da transcrição/geração. **Silenciar resposta** mantém a conversa com respostas escritas.

Durante a leitura, **Interromper e falar** interrompe a voz e abre uma nova captura. O leitor tem um prazo limitado; se não avisar que terminou, a sessão encerra com mensagem e preserva a resposta escrita, sem abrir o microfone inesperadamente. O botão não interrompe uma geração ainda em andamento; use **Encerrar voz** para solicitar seu cancelamento.

O modelo recebe orientações de conversação: acolher cumprimentos e agradecimentos brevemente, respeitar despedidas, simplificar explicações quando houver confusão e responder à pergunta mesmo que ela venha junto de um agradecimento. Essas orientações e o histórico melhoram o comportamento sem alterar pesos. A simpatia continua sujeita à qualidade do modelo local.

Saudações e agradecimentos simples reconhecidos usam um contexto menor, para não retomar uma tarefa antiga por engano. Preferências declaradas do projeto continuam disponíveis. Uma pergunta junto do agradecimento mantém histórico, fontes e orientações do projeto. Nenhuma mensagem é apagada; os metadados registram as omissões. Expressões não reconhecidas usam o fluxo normal de contexto.

Rascunhos digitados não são substituídos: envie ou guarde a mensagem antes de começar. O microfone fica desligado durante transcrição, geração e leitura. Trocar a página ou deixá-la em segundo plano encerra a voz. A captura nunca começa automaticamente ao abrir o aplicativo.

## Processamento e privacidade

- O cliente captura o microfone e lê com uma voz local em português do Windows. Voz remota é recusada. Se faltar uma voz local, instale o recurso de fala nas configurações de idioma do Windows.
- O servidor reconhece a fala com Whisper small q5_1 multilíngue em CPU num contêiner sem rede e responde com o modelo textual local registrado na Foundation. Clientes não precisam de pesos ou Docker.
- O perfil persistente conserva os pesos do Whisper entre falas e processa WAV em memória. O servidor HTTP do decoder fica somente no loopback interno do contêiner, sem porta publicada, rede externa ou histórico de transcrição entre pedidos. Logs Docker são desabilitados nesse perfil. O perfil antigo continua compatível e usa WAV temporário no `/tmp`.
- Áudio só atravessa a conexão autenticada com seu servidor. Não é salvo no banco, na fila ou no navegador. Cancelamento/falha remove o runtime persistente afetado; uma nova fala cria outro. Troca do manifesto e encerramento do servidor também liberam o decoder.
- Transcrição e resposta ficam no histórico do projeto. Registrar uma experiência não autoriza treinamento. Voz não concede permissão para executar código, publicar, pagar ou alterar sistemas. Não fale senhas ou dados privados.

Histórico e fontes entram no limite real de contexto; não há memória ilimitada. A conversa também funciona por texto no modo **Conversar com a IA local**.

## Limites

Cada fala tem até 30 segundos. O cliente envia WAV PCM mono de 16 kHz. O servidor verifica formato, tamanho, duração e silêncio. Dez segundos sem fala encerram a captura. Ruído, sotaques e nomes técnicos podem causar erros: confira o chat, interrompa a voz e corrija por texto.

É uma conversa contínua por turnos: ouvir → transcrever → gerar → ler → ouvir. Não é áudio simultâneo nem resposta em tempo real com latência garantida. No ensaio de 20/10/2026, a transcrição levou aproximadamente oito segundos e confundiu “Kanban” com “Cambam”; a resposta preservou esse erro. O microfone físico e o reconhecimento desse termo não foram homologados.

Uma transcrição por vez usa quatro CPUs no perfil antigo. O persistente permite quatro ou seis threads/CPUs explicitamente registrados, mantendo o teto de 2 GiB de RAM. O servidor desta entrega tem seis núcleos físicos e recebeu o perfil de seis CPUs. A decodificação tem prazo de 90 segundos. Ausência de modelo/Docker, servidor ocupado, microfone negado ou voz local ausente geram aviso e encerram a sessão. Não há reenvio automático após falha nem serviço remoto de contingência. A primeira resposta pode demorar mais ao carregar o modelo. Respostas longas são lidas parcialmente com aviso; o leitor não corta o texto armazenado. Reinícios automáticos aguardam a conversa por voz terminar.

Ao começar a voz e permitir o microfone, o cliente também solicita o aquecimento do modelo textual pela fila existente. A captura é conectada antes de aguardar a resposta dessa solicitação, preservando as primeiras palavras. Esse job não gera mensagens, executa código ou guarda áudio; exige acesso de escrita ao projeto e tem as permissões rechecadas na execução. O modelo pode carregar enquanto a fala é reconhecida. A pausa de envio permanece em 1,5 segundo.

No perfil persistente, falas com até oito segundos usam uma janela de encoder de 15,36 segundos; falas maiores mantêm a janela completa de 30 segundos. Nenhuma amostra é cortada e a busca do decoder continua com beam/best-of 5. Os testes de qualidade incluíram termos técnicos e uma fala de 28 segundos; isso não garante acerto universal nem corrige automaticamente o erro conhecido Kanban/Cambam.

## Preparar um servidor novo

Esta máquina foi preparada pelo operador. O aplicativo não baixa modelos, imagens ou pacotes automaticamente.

1. Prepare as imagens locais de compilação e runtime descritas em `FOUNDATION.md` e confira suas identidades.
2. Adquira e revise explicitamente o [Whisper.cpp](https://github.com/ggml-org/whisper.cpp), revisão `d1be6fde11ac6e0407606b4e42fe72d34add8037` (v1.9.5), e o modelo do [repositório oficial de conversão](https://huggingface.co/ggerganov/whisper.cpp), revisão `5359861c739e955e79d9a303bcbc70fb988958b1`. Licença MIT; aquisição e pesos ficam fora do Git.
3. Arquivo: `ggml-small-q5_1.bin`, 190.085.487 bytes, SHA-256 `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`.
4. Compile `qa/voice/Dockerfile` com `--network=none --pull=false`, passando o código revisado como contexto `whisper_source`. A imagem não inclui pesos. Confira a identidade da imagem final.
5. Registre arquivos já adquiridos pelo comando abaixo. O registro recusa sobrescrita, verifica o modelo e cria um volume próprio.

```powershell
python scripts/register-voice.py --home "D:\LocalAuthor" --model "D:\Modelos\ggml-small-q5_1.bin" --image-id "sha256:HASH_CONFERIDO_DA_IMAGEM" --accept-mit-license
```

Para o perfil persistente, compile `qa/voice/Dockerfile.persistent` com o mesmo código fonte e bases locais conferidas, passando `--build-arg VOICE_BASE=IMAGEM_LOCAL_CONFERIDA`. Nenhum download é feito pelo aplicativo. O binário `whisper-server` da mesma revisão é uma dependência nova; a licença está incluída na imagem. Ao registrar em um servidor novo, acrescente `--persistent --threads 6` (ou `4` num servidor menor). Use o hash dessa imagem persistente, nunca o do worker antigo. Um manifesto existente não é sobrescrito pelo registrador; a migração precisa preservar cópia e hash do registro original, validar o novo perfil e ativá-lo durante manutenção.

6. Registre um modelo textual compatível conforme `FOUNDATION.md`, preservando registros anteriores, e reinicie o servidor cooperativamente. Conversa experimental não promove o modelo como programadora ou QA qualificada.
7. Abra/reconecte os clientes já vinculados. O cliente 0.3.7 carrega esta interface pelo servidor; esta mudança web não exige reinstalação. Em navegador, use HTTPS ou loopback; HTTP por IP da rede não habilita microfone.

Push distribui código; instalar a revisão e reiniciar outro servidor continua necessário. Pesos e configuração da fala ficam no servidor central, não no instalador cliente.

## Verificação

561 testes Python passaram, incluindo áudio inválido/silencioso/excedido, autenticação, origem, ausência de configuração, isolamento, concorrência, cancelamento e encerramento. `scripts/voice-ui-smoke.py` usa captura PCM real do Chromium com microfone sintético e dublês declarados de STT, TTS e modelo. A regressão das outras telas permanece no CI.

O decoder real isolado reconheceu três frases sintéticas em português, produzidas pela voz Maria do Windows, em aproximadamente 7 segundos por fala. Qwen3.5 4B local respondeu a dois turnos com histórico: aproximadamente 37 segundos na primeira carga e 2 segundos no segundo turno. Estes casos não qualificam reconhecimento universal ou inteligência geral. Microfone físico do usuário e outro computador precisam de conferência no uso.

Nova verificação e evidências: [conversação e voz em 20/10/2026](reports/CONVERSACAO_E_VOZ_2026-10-20.md). O script opt-in `scripts/conversation-real-check.py --run-real --home CAMINHO --output PASTA_NOVA` executa doze pedidos no modelo registrado, sem usar a base de conversas do servidor. `--audio-fixtures PASTA` acrescenta arquivos sintéticos `input-*.wav` no formato canônico acima, com transcrição real e histórico entre turnos. Resultados e áudio ficam privados. `success` significa execução sem saída truncada, não aprovação semântica: revise respostas, transcrições e limitações.

Referências: [Whisper.cpp](https://github.com/ggml-org/whisper.cpp), [vozes locais no navegador](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService).

Comparação de latência, configurações descartadas e limites: [otimização de voz em 20/10/2026](reports/VOZ_LATENCIA_2026-10-20.md).
