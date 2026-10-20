# Latência da conversa por voz — 20/10/2026

A queixa de demora foi reproduzida com Whisper small q5_1 em CPU e Qwen3.5 4B Q8 na RTX 2060 6 GB. O computador tem i7-10750H, seis núcleos físicos e doze threads. O modelo textual, os pesos de voz e suas licenças foram preservados; não houve aquisição de pesos nem uso de API de IA externa.

## Comparação controlada

A versão anterior foi extraída da revisão `44dd679d623875ffbf3e29623729ff7891d846c0`. Ela e a candidata foram executadas sequencialmente, sem a suíte pesada em paralelo, com o mesmo áudio sintético Maria Desktop, a mesma voz de saída Daniel, os mesmos pesos e três turnos por execução. O tempo até a leitura inclui a captura da fala e a pausa de 1,5 segundo; não é somente tempo de inferência.

| Medida | Anterior | Candidata |
| --- | ---: | ---: |
| Primeira captura até começar a ler, modelo textual frio | 42,29 s | 29,78 s |
| Segunda captura até começar a ler | 13,11 s | 7,93 s |
| Terceira captura até começar a ler | 13,37 s | 7,70 s |
| Três turnos completos, incluindo a leitura | 84,49 s | 59,05 s |

Nos dois ensaios os três turnos terminaram e abriram a próxima escuta, com STT, LLM e TTS reais. A entrada “Bom dia! Tudo bem?” foi preservada no ensaio final. A primeira resposta ainda pode demorar: carregar e conferir o modelo na GPU não é instantâneo. Carga concorrente, respostas longas, troca entre modelos e outro hardware podem mudar esses números. Microfone físico e outra máquina não foram homologados.

As respostas dos turnos seguintes variaram um pouco em texto e pontuação; isso também muda a duração da leitura. A comparação principal é captura → início da leitura, sem somar a duração do texto falado: redução de aproximadamente 41% nos turnos com modelo já carregado e 30% no primeiro turno observado.

## Alterações

- O decoder fica residente em um contêiner verificado e sem rede externa, em vez de recriar/carregar tudo a cada fala. Imagem imutável, pesos somente leitura, usuário sem privilégios, limites de RAM/CPU/PIDs, sem portas publicadas e sem logs Docker de transcrições.
- Novo `whisper-server` compilado do código MIT já adquirido, revisão `d1be6fde11ac6e0407606b4e42fe72d34add8037`. Só o controlador fixo acessa seu loopback interno. Não há contexto textual entre pedidos; cada pedido mantém identidade e prazo próprios. Falha/cancelamento descarta a instância.
- Perfil explícito de seis threads/CPUs neste servidor, ainda com 2 GiB de RAM. Compatibilidade com quatro threads e com o manifesto antigo.
- Para áudio de até oito segundos, janela de encoder de 15,36 segundos; para o restante, janela completa de 30 segundos. Cobertura de todas as amostras verificada nos limites de duração. Beam e best-of continuam em 5.
- Aquecimento textual pela fila assim que começa a captura. Permissões de projeto verificadas no envio e na execução, sem gerar mensagens nem salvar áudio. Captura conectada antes de aguardar a rede, para não perder o começo da fala.

## Qualidade e tentativas descartadas

O teste real de reconhecimento comparou três arquivos da rodada anterior e cinco adicionais, incluindo agradecimento, número 25, terça-feira, C#/PostgreSQL e falas de 18 e 28 segundos. A candidata conservadora preservou os termos verificados. O erro anterior Kanban → Cambam continuou existindo; não se declarou reconhecimento perfeito.

Os registros privados conservam uma janela menor que perdeu PostgreSQL e uma janela adaptativa em fala longa que escreveu “Abakashi” em vez de “abacaxi”. Essas configurações não foram promovidas. A pausa de 0,85 segundo também foi descartada depois de um ensaio não preservar “Tudo bem” na transcrição; a versão final mantém 1,5 segundo.

Uma primeira medição completa feita junto com outros testes foi mais lenta e perdeu palavras iniciais. Foi preservada como tentativa não aprovada. Havia uma espera de rede antes de conectar a captura, capaz de perder seu início. A captura foi conectada antes dessa espera e a comparação foi repetida isoladamente. Os testes sintéticos são avaliação interna limitada, não homologação de sotaques, ruído, qualquer vocabulário ou qualidade igual à voz do Codex.

Validação local final: 721 testes de software executados, 718 aprovados, zero falhas/erros e três testes de symlink não executados por privilégio do Windows; 23 verificações da interface com dublês declarados; 29 verificações dirigidas de voz/HTTP/ciclo de vida. Os modelos reais foram avaliados separadamente nos ensaios descritos acima. Banco e registros originais foram copiados antes da manutenção. Após o retorno, projetos, conversas e mensagens mantiveram suas contagens; um job adicional aqueceu o modelo pelo perfil existente do operador, sem criar mensagem de chat.

## Operação

Os clientes carregam a interface e usam os modelos do servidor; esta alteração não exige um novo instalador. Recarregar a janela aplica a interface. Um servidor diferente exige implantação do código, imagem persistente local conferida e registro compatível; push sozinho não distribui pesos ou a imagem Docker. O manifesto antigo e os volumes são preservados para reversão. O registro por `scripts/register-voice.py` recusa sobrescrita e exige licença e hash de imagem explícitos.
