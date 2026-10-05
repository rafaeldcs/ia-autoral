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
- Ao concluir alterações, faça commit e push na branch de trabalho após revisão e validação, sem aguardar outro pedido. Não publique segredos/dados privados; não force push. Se o envio falhar, informe o impedimento.
- Consulte `docs/FOUNDATION.md` para instalação, processo, limites e homologação. O pipeline antigo de treino não treina o modelo foundation.
