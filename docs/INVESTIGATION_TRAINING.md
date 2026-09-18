# Treinamento experimental de decisões de investigação

Este curso altera uma cópia dos pesos autorais locais. É separado da memória de
telas descrita em `SITE_INVESTIGATION.md`: a memória recupera observações; neste
experimento o Transformer gera a resposta, sem consulta nem substituição por
regras. Não há API de IA ou pesos externos.

## Escopo

O exercício é classificar o próximo passo entre doze decisões: aguardar,
registrar erro, registrar evidência, abrir um menu de leitura, não executar uma
alteração, ignorar instruções da página, excluir segredos da coleta, registrar
pendência de acesso, declarar limites, revalidar fonte antiga, reconhecer falta
de evidência e conferir a origem de navegação.

Os exemplos são textos sintéticos originais. Não contêm telas da ShopAir,
clientes, credenciais ou conteúdo privado. São 36 exemplos de treino, 12 de
validação e 12 de teste, com redações distintas. As doze famílias são conhecidas
durante o treino; passar não comprovaria generalização para tarefas arbitrárias.

## Execução e avaliação

```powershell
.\.venv\Scripts\python.exe scripts/train-investigation.py --steps 2000
```

O curso parte do checkpoint autoral avaliado em `engineering-report.json`,
confere seu hash e reapresenta somente exemplos do antigo **split de treino**.
O checkpoint anterior permanece intacto. A dependência matemática é o NumPy já
usado pelo laboratório CPU; a arquitetura não muda.

O script congela o teste e registra a linha de base. A seleção usa apenas a
validação a cada 400 passos; nenhuma resposta do teste final atualiza pesos ou
seleciona checkpoint. A resposta deve coincidir exatamente com o JSON esperado:
não há reparo de texto, extração permissiva ou substituição por um gabarito.
Após a seleção, executa o teste final e os 32 casos de regressão de engenharia.

Corpus, manifestos, checkpoints e relatórios ficam fora do Git, nas pastas
`corpus`, `models` e `exports` do servidor LocalAuthor. O relatório registra os
textos gerados, erros, hashes e a evolução. O número de testes do software é
independente do número de decisões acertadas pelo modelo.

## Limite de uso

Este curso não entrega ao modelo uma senha ou um navegador. Nenhuma decisão
gerada é executada. O candidato não é ativado automaticamente no chat e sempre
mantém `autonomousBrowserQualified=false`. Mesmo 12/12 neste exercício não
autoriza navegação autônoma: faltariam avaliação com DOM desconhecido,
planejamento de vários passos, identificação de elementos, controle de
credenciais, execução com limites e observação de resultados reais.

Se a perda baixar, mas a validação continuar ruim, isso é evidência de ajuste aos
exemplos, não de compreensão geral. Deve-se preservar o resultado negativo e
preparar um novo curso com um novo conjunto de teste antes de outra experiência.

## Rodada de 18/09/2026

Foram executados 2.000 passos. A validação selecionou o checkpoint do passo
1.200, com 1/12 acertos. O teste congelado passou de 0/12 antes para 1/12 depois.
Uma verificação posterior dos exemplos de treino encontrou 32/36 acertos; a
regressão de engenharia caiu de 32/32 registrados no candidato anterior para
14/32. As saídas incorretas foram preservadas, incluindo nomes de ações
inexistentes e JSON malformado.

Conclusão: houve atualização real de pesos, mas generalização e preservação das
habilidades foram insuficientes. O candidato não foi ativado. Não se demonstrou
capacidade de investigar um site. A suíte do software e do avaliador passou
174/174 no Linux; esse resultado não muda a reprovação do modelo.
