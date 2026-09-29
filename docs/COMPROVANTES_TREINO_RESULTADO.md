# Treino local de classificação de comprovantes

Em 29/09/2026 o corpus sintético `saravaapp-comprovantes-20260929-v1` foi preparado no servidor DEV1 e treinado em dois experimentos separados. A avaliação reservada permaneceu fora do treinamento e foi executada em contêiner somente leitura, sem alterar o modelo ativo.

| Experimento | Passos | Perda inicial | Perda final | Rótulos corretos na avaliação |
| --- | ---: | ---: | ---: | ---: |
| v1 | 1.000 | 5,5616 | 1,6522 | 0/12 |
| v2 | 10.000 | 5,5616 | 3,3330 | 4/12 |

O avaliador recarrega o checkpoint e aceita somente uma linha de protocolo com rótulo exato (`Proxima_verificacao: ROTULO`). Não corrige acentuação, completa texto, escolhe o rótulo pelo gabarito ou modifica a resposta gerada. A primeira execução com limite de 32 tokens foi descartada por truncamento; a avaliação válida usa 96 tokens.

Resultado: ambos os checkpoints estão reprovados e fora do agente. A perda do v2 piorou após o prolongamento; aumentar passos não resolveu a generalização. O próximo experimento deve alterar o desenho do corpus e a tarefa supervisionada, mantendo casos reservados separados, em vez de simplesmente aumentar o número de passos.

Os checkpoints e relatórios privados ficam em `%LOCALAPPDATA%\LocalAuthor\models` e `%LOCALAPPDATA%\LocalAuthor\exports`. Não há dados reais, cobrança, publicação ou alteração no SaravaAPP nesta rodada.
