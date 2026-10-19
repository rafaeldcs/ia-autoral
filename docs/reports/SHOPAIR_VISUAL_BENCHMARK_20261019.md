# ShopAir — teste real de imagem e revisão visual

## Conclusão

A alteração `a28a71c` ampliou controles de criação e composição, mas **não demonstrou melhoria na qualidade nem aceleração confiável da inferência nas mesmas condições**. Os três conceitos produziram PNGs idênticos nas quatro rodadas de controle. A mediana de seis imagens por versão foi 3,8507 s na revisão anterior e 3,8231 s na atual: diferença de 0,72%, sem estudo de significância e insuficiente para atribuir ganho consistente.

O prompt negativo produziu imagens diferentes, com resultados mistos. Ainda surgem letras, rótulos e marcas fictícias, além de desvios do briefing. A captura de 19 casos com sucesso não aprova qualidade comercial. A revisão do proprietário permanece pendente; nada foi publicado ou autorizado para treinamento.

## Execução real

- Anterior: `35198478531691bbd4147d651bdfdc3bdd115712`.
- Atual: `a28a71c7711e0953d012563e2c90ee065ecb4a31`.
- Modelo já existente: `stable-diffusion-v1-5/stable-diffusion-v1-5`, revisão `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`; licença registrada `CreativeML-OpenRAIL-M`.
- Manifesto: `720dccb322bde70dba1792a4fcc7d9d341b7f4d5f14f832c41f4ff3713e50382`.
- GPU: NVIDIA GeForce RTX 2060, 6 GiB; CUDA 11.8; float16.
- Runtime efetivamente usado: torch 2.5.1+cu118, diffusers 0.35.2, transformers 4.57.6, safetensors 0.7.0, Pillow 11.3.0. É o ambiente visual existente, não uma afirmação sobre todas as versões das dependências textuais.
- Imagem Docker existente, por identidade imutável: `sha256:2d8064bb369c7f9bd695c8e00b6912e62b2e507755da51109bd19285b3a87b98`.
- Sandbox inspecionada antes/depois: sem rede, root somente leitura, usuário 10001, capabilities removidas, no-new-privileges/seccomp, limite de 6 GiB RAM, quatro CPUs e 128 PIDs. Somente o volume de pesos foi montado, somente leitura. Código/entradas foram transferidos por arquivo tar validado e conferidos por hash.
- Canary CUDA executado, pipeline UNet em CUDA e verificador visual ativo. Hashes dos pesos conferidos novamente ao fim de cada rodada. Sem dublês na inferência; sem downloads ou fallback externo.

Os briefings do supervisor abordaram loja/expedição, catálogo e restaurante, com referência às cores registradas da ShopAir (azul, roxo e magenta). Não representam clientes reais, telas funcionais ou provas de vendas. Os pixels foram produzidos por `FoundationService/ImageRuntime`; a direção de teste, a comparação e a galeria são trabalho do supervisor. Não houve treinamento dos pesos.

## Medições

Sequência anterior–atual–atual–anterior (ABBA), três casos em cada rodada, mesmas seeds, prompts, 512 × 512, 20 passos e guidance 7.5. Aquecimento, carregamento/verificação do modelo e recuperação dos artefatos ficaram fora da latência de geração. A medição de geração inclui pipeline, codificação PNG e persistência do serviço, com sincronização CUDA.

| Medida | Anterior | Atual |
| --- | ---: | ---: |
| Amostras de geração | 6 | 6 |
| Mediana, modelo carregado | 3,8507 s | 3,8231 s |
| PNGs nas mesmas condições | Idênticos | Idênticos |

O carregamento com verificação de hashes levou de 20,67 a 23,48 s nas seis rodadas. O aquecimento de cada processo levou de 6,47 a 6,70 s e foi excluído da comparação. Portanto, 3,82 s não descreve uma primeira solicitação com o modelo descarregado, a espera da fila, a troca do modelo textual ou a rede do cliente.

| Perfil atual adicional | Tamanho | Passos | Geração observada |
| --- | --- | ---: | ---: |
| Retrato | 512 × 768 | 20 | 6,21 s |
| Paisagem | 768 × 512 | 20 | 11,08 s |
| Prévia | 512 × 512 | 5 | 2,16 s |
| Mais passos | 512 × 512 | 50 | 14,67 s |

Esses perfis tiveram uma captura cada; não são estimativas universais de latência. Maior contagem de passos não garante qualidade. A prévia de cinco passos apresentou artefatos visíveis e não foi aprovada para anúncio. O pico de memória alocada pelo PyTorch foi 3.733.703.680 bytes (~3,48 GiB), e o pico reservado foi 4.735.369.216 bytes (~4,41 GiB); isso não inclui toda a memória do driver, desktop ou outros processos.

Foram entregues **19 de 19 casos avaliados**: 12 de controle, três com prompt negativo e quatro de perfis. Os aquecimentos são separados. Cancelamento prévio e rejeição de prompt acima do tokenizador foram conferidos em cada processo; gravação/recuperação dos PNGs teve hash igual. Isso não equivale a cobrir todos os defeitos possíveis ou todas as seeds.

## Defeitos encontrados e corrigidos

O teste funcional anterior só conferia a existência da tag da miniatura e a assinatura EBML do arquivo. A investigação ampliada encontrou:

1. Miniaturas via URL `blob:` eram bloqueadas pela CSP. A interface passou a criar miniaturas pequenas em data URL, compatíveis com a política existente.
2. Formato, legendas e outros controles podiam mudar durante a gravação. Agora ficam bloqueados, e a composição usa dimensões/cenas congeladas. Falhas do codificador restauram os controles e encerram recursos.
3. O capturador antigo de briefings chamava um método de descarte removido. Agora usa `FoundationService.close()`; um teste de falha confirma encerramento e preservação do relatório.

A validação com arquivos reais da ShopAir passou em 15 casos no Edge, incluindo miniaturas decodificadas sob a CSP do produto, entrada corrompida/tipo não aceito/excesso de arquivos, preservação das cenas, reordenação, erro provocado na inicialização do codificador, bloqueio de controles, resolução real dos três WebMs, exclusão de cena e layout móvel. Os vídeos têm duas cenas/4 s e foram renderizados, baixados e decodificados; são composição de imagens estáticas, sem geração neural de movimento.

`python scripts/foundation-ui-smoke.py --browser-channel msedge` também passou, com as novas regressões de miniatura e bloqueio. Esse smoke ainda usa dublês nas conversas e inferência; a bateria CUDA acima é separada.

Um PNG retrato realmente gerado na GPU também foi importado, sem regeneração, em uma sessão descartável do aplicativo para conferir a entrega: requisição sem token retornou 401; a interface mostrou 512 × 768 pixels; o botão “Baixar PNG” produziu um arquivo com o mesmo SHA-256 do original da GPU. Não houve dublê de imagem nessa conferência; ela prova recuperação/exibição/download, não uma segunda inferência ou aprovação de qualidade.

`python scripts/run-tests.py --allow-unavailable-symlinks --report <relatório privado>`: **593 executados, 590 aprovados, zero falhas/erros e três skips de symlink por privilégio indisponível no Windows**. O resultado local é incompleto nesses três testes. Conferir o workflow `local-platform-ci` do commit publicado desta entrega para as matrizes remotas; a inferência real desta seção pertence às revisões identificadas acima, não a uma execução GPU do CI.

## Evidências e aprovação

O pacote privado contém PNGs originais com hashes, seis relatórios completos de inferência, logs, inspeções da sandbox, galeria antes/candidata/controle, vídeos nos três formatos e capturas desktop/móvel. A galeria permite registrar preferência por caso e exportar uma avaliação JSON. Nenhuma escolha vem marcada; seu download não publica mídia, não envia decisões ao servidor e não autoriza treinamento.

As falhas iniciais também foram preservadas: Docker indisponível por socket temporário, compartilhamento Windows sem os arquivos esperados, aquecimento de cinco passos bloqueado pelo verificador e extração recusada por divergência de caminho virtualizado. Nenhuma delas foi transformada em teste aprovado nem levou à desativação do verificador. A execução final usou cópias de fonte/entradas verificadas e um aquecimento separado com briefing já conhecido; as sementes dos 19 casos avaliados não foram trocadas para procurar acertos.

Não houve registro/ativação do modelo de imagem no servidor principal. A revisão visual e uma decisão explícita sobre uso comercial continuam necessárias antes de promover peças ou modelos. Para uma melhoria futura, o próximo experimento deve comparar um novo checkpoint ou uma mudança concreta do pipeline, com licença revisada, orçamento compatível com o hardware, casos reservados e critérios de qualidade definidos antes da execução.

## Repetir o procedimento

`scripts/foundation-image-benchmark.py` é um worker opt-in. Exige sandbox Linux inspecionada, GPU real, manifesto com hashes, casos congelados e pasta nova. Recebe a fonte explicitamente e registra hashes dos módulos; o controlador externo deve conferir essa cópia contra o commit informado. Não executar no host como alternativa à sandbox.

`scripts/visual-studio-qa.py --output <pasta privada nova> --browser-channel msedge` exercita composição e exportação reais, sem inferência de modelo. Os relatórios permanecem privados até revisão; o usuário pode aprovar ou rejeitar a qualidade das imagens independentemente do resultado funcional.
