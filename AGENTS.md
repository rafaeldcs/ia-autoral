# Instruções do repositório

- Não introduza APIs de IA, pesos pré-treinados, embeddings externos ou telemetria oculta.
- Declare toda dependência de infraestrutura e toda mudança de arquitetura.
- Nunca considere perda de treino ou compilação como prova de capacidade de programação.
- Execute `python scripts/run-tests.py`; não marque .NET/GPU/Docker como testados sem execução real.
- Dados reais, segredos, corpus e checkpoints ficam fora do Git.
- Material importado para consulta não autoriza treinamento. Respeite o manifesto e a origem.
- O modelo propõe; controles determinísticos autorizam; revisão humana aplica.
- Sem sandbox verificada, falhe fechado. Nunca faça fallback para executar código de projeto no host.
- Preserve hashes, originais, diferenças e diários de recuperação; teste as falhas.
- Não remova testes ou relaxe a política para fazer o CI passar.
- Não declare esta versão equivalente ao Codex ou a um modelo de fronteira.
- Ao concluir solicitações com alterações neste projeto, faça commit e push na branch de trabalho, após revisão e validação, sem aguardar outro pedido do usuário.
- Não publique segredos ou dados privados; não force push. Se o envio falhar, informe o impedimento. Consultas sem alterações não exigem commit vazio.
