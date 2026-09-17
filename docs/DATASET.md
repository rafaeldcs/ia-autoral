# Dados e treinamento — contrato do protótipo

Não acompanha esta entrega um corpus produtivo de programação. A memória de consulta também não é convertida automaticamente em corpus. A autoria/permissão precisa ser verdadeira e revisada, não somente um campo `true` escolhido para passar na validação.

## Manifesto

Copie `experiments/manifest.example.json` para uma pasta privada de corpus fora do Git. Preencha caminhos relativos, hashes SHA-256 dos bytes reais e origem de cada material. Um registro contém exatamente:

```json
{
  "path": "train/exercicio-001.txt",
  "split": "train",
  "group": "familia-independente-a",
  "sha256": "SHA256_REAL_DO_ARQUIVO",
  "training_allowed": true,
  "provenance": {
    "kind": "human-authored",
    "owner": "TITULAR_REAL",
    "license_or_permission": "DESCRICAO_REAL_DA_PERMISSAO"
  }
}
```

`split`: `train`, `validation` ou `test`. `kind`: `human-authored`, `licensed` ou `synthetic-authorized`. Essas etiquetas não autorizam uso sozinhas; o responsável precisa manter a evidência da permissão fora do Git público.

O motor requer pelo menos um registro de treino e outro de validação. Um mesmo grupo não pode atravessar partições. Duplicação exata entre partições e certas semelhanças altas de shingles são rejeitadas. Essa heurística não prova ausência de contaminação semântica.

O manifesto tem limite de 4 MB/2.000 registros, cada documento até 1 MB e o corpus total até 8 MB incluindo holdout. A implementação carrega o pequeno corpus e os tokens em memória; não é um loader para bilhões de tokens.

Para calcular o hash sem carregar o arquivo inteiro no PowerShell:

```powershell
(Get-FileHash C:\LocalAuthorData\corpus\train\exercicio-001.txt -Algorithm SHA256).Hash.ToLowerInvariant()
```

## Separação de avaliação

O validador pode ler arquivos `test` para verificar integridade/deduplicação, mas não retorna seu texto ao treinador. Isso não é isolamento por sistema operacional. O treino consome apenas `train`; amostras de `validation` fornecem a perda de validação. Um conjunto final secreto, avaliador independente de código e proteção do holdout em processo/usuário separado ainda precisam ser implementados.

Não use a mesma família de exercícios como treino e prova final. Não considere compilação ou memorização de texto como prova de resolução de tarefas inéditas.

## Treinamento

Use caminhos fora do repositório. Defina `PYTHONPATH=src` e use o Python da `.venv` com NumPy. Exemplo de estrutura, a adaptar aos seus arquivos reais:

```text
C:\LocalAuthorData\corpus\manifest.json
C:\LocalAuthorData\corpus\train\exercicio-001.txt
C:\LocalAuthorData\corpus\validation\exercicio-002.txt
C:\LocalAuthorData\models\experimento-001\
```

`validate-dataset` verifica o contrato. `train --config experiments/configs/smoke-cpu.json --steps 100 --output DIRETORIO` executa o piloto pequeno. O tokenizador byte preserva UTF-8; `--tokenizer bpe` aprende merges apenas do treino, com limites próprios de 500 KB e 1.024 tokens. Para Unicode, o modelo continua operando tokens/bytes, não caracteres semanticamente compreendidos.

O loop registra perdas, contagem de parâmetros, throughput, hashes, passos e cancelamento. `latest.npz` contém pesos, estados AdamW, RNG e tokenizador, permitindo `--resume CAMINHO`. A retomada exige o mesmo hash do corpus. Alterar os dados exige novo experimento. A taxa de aprendizado e demais decisões são simples para o laboratório; não há escalonamento de grande escala.

O checkpoint é salvo periodicamente e ao encerramento/cancelamento cooperativo. Ctrl+C solicita parada; não reinicie repetidamente durante a escrita. Não há promessa de recuperação de toda falha elétrica/corrupção.

## Promoção

A versão 0.1 não possui promoção automática nem manual para um agente generativo produtivo. Os relatórios marcam `programming_qualified=false`. A saída de `generate` é apenas uma continuação experimental, nunca uma autorização para modificar arquivos.

O próximo marco exige corpus licenciado, avaliação por tarefas inéditas, comparações com baselines e teste independente. Sem esse resultado, não liberar o modelo como programador.
