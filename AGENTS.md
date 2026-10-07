# Instruções do repositório

- O laboratório neural autoral permanece independente. A camada opcional `foundation` pode carregar pesos pré-treinados locais e derivados, com licença, origem, revisão e hashes registrados. Esta decisão substitui a proibição anterior de pesos pré-treinados, conforme a direção solicitada pelo proprietário.
- Não introduza dependência de APIs externas de IA, downloads automáticos, embeddings externos ou telemetria oculta. Uma biblioteca/processo local de inferência não é um serviço remoto.
- Declare toda dependência de infraestrutura e toda mudança de arquitetura.
- Nunca considere perda de treino, testes com dublês ou compilação como prova de capacidade de programação ou qualidade dos modelos reais.
- Execute `python scripts/run-tests.py`; não marque .NET/GPU/Docker ou pesos reais como testados sem execução real. Identifique a revisão nos resultados de CI.
- Dados reais, segredos, corpus, imagens pessoais e checkpoints ficam fora do Git.
- Material importado para consulta não autoriza treinamento. Revisão humana, verificação e autorização para treino são decisões separadas. A autorização deve cobrir todas as fontes e o histórico incluídos no exemplo.
- O modelo propõe; controles determinísticos autorizam; revisão humana aplica.
- Sem sandbox verificada, falhe fechado. Nunca faça fallback para executar código de projeto no host. O modo foundation não executa código gerado.
- Preserve hashes, originais, diferenças e diários de recuperação; teste as falhas.
- Não remova testes ou relaxe a política para fazer o CI passar.
- Não declare esta versão equivalente ao Codex ou a um modelo de fronteira. Registrar/carregar modelos não equivale a treiná-los.
- Por solicitação expressa do proprietário em 7 de outubro de 2026, entregar as alterações na branch principal `main`, sem deixá-las em PR ou branch paralela. Revisar, testar, publicar sem force push e verificar o CI da revisão publicada. Não abrir outro PR salvo pedido explícito. Não publicar segredos/dados privados; informar qualquer falha de envio ou validação.
- Não marcar funcionalidades apenas especificadas como implementadas nem apagar evidências de pendências para aparentar conclusão. O pacote de código e os testes de software não são um checkpoint treinado nem uma homologação de qualidade.
- Consulte `docs/FOUNDATION.md` para instalação, processo, limites e homologação e `docs/PUBLICACAO_MAIN.md` para a distribuição de código. O pipeline antigo de treino não treina o modelo foundation.

<!-- LOCALAUTHOR_APRENDIZADO_LOCAL:BEGIN -->
## Continuação local do aprendizado — instruções temporárias

Para executar a conclusão do aprendizado solicitada pelo proprietário, começar em [docs/aprendizado-local/00_COMECE_AQUI.md](docs/aprendizado-local/00_COMECE_AQUI.md) e seguir [o prompt do executor local](docs/aprendizado-local/01_PROMPT_MESTRE_EXECUTOR_LOCAL.md). Conferir a revisão e registrar cada etapa em uma cópia privada do estado. Não substituir o trabalho por outro plano nem declarar treinamento sem execução real.

Somente os sete documentos de `docs/aprendizado-local/conhecimento/` são candidatos à importação para consulta. Não indexar/treinar com o pacote inteiro; preservar a separação de currículo, avaliação e registros privados. Se o próprio repositório for indexado, excluir estes roteiros antes ou usar uma cópia de laboratório com fontes autorizadas.

**Última ação, após executar e conferir todos os requisitos aplicáveis:** seguir [99_CONFERENCIA_E_LIMPEZA.md](docs/aprendizado-local/99_CONFERENCIA_E_LIMPEZA.md), preservar conhecimento e evidências, remover exclusivamente os arquivos temporários listados em commit separado e conferir a publicação. Pendência obrigatória ou evidência ausente impede a limpeza. Não apagar nada agora, não apagar modelos/dados e não apagar este `AGENTS.md`.

Ao concluir também a limpeza, remover apenas este bloco temporário entre os marcadores, manter o restante do arquivo e deixar o relatório sanitizado de conclusão e os conhecimentos duráveis. Um Markdown não concede ferramentas nem dispara a execução automática.
<!-- LOCALAUTHOR_APRENDIZADO_LOCAL:END -->
