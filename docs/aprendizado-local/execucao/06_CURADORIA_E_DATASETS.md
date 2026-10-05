# Dados de aprendizado: origem, verificação e separação

## Unidade de aprendizado

Uma linha de chat não é, por si, um exemplo correto. Uma unidade útil reúne pedido, contexto efetivamente disponível, resposta-alvo, evidências, resultado da verificação, família da tarefa, origem e permissões. Exemplo de código inclui ambiente e teste observável; exemplo visual inclui o arquivo real e a legenda que o descreve.

Use três estágios privados: `candidatos`, `revisados` e `aprovados_para_treino`. Nenhum conteúdo cru deve saltar diretamente da conversa para pesos. Uma base externa competente pode gerar candidatos, mas não é o verificador da própria verdade.

## Fontes permitidas para consideração

Conteúdo do próprio proprietário com direitos confirmados; exemplos didáticos próprios; materiais de terceiros cuja licença permita o uso pretendido; saídas de modelos locais cujos termos sejam compatíveis. Documentação pública não é automaticamente corpus livre. Dados de clientes, empregadores, comprovantes reais, mensagens privadas e imagens de pessoas exigem autorização específica, não uma aprovação genérica do projeto.

A autorização deve cobrir prompt, histórico, código, documento recuperado, imagem, resposta e derivados. Os arquivos `conhecimento/` começam com `training_allowed: false`: sua inclusão em um exemplo demanda nova decisão explícita. Não modificar um front matter para simular a decisão do proprietário.

## Revisão das experiências já registradas — comandos existentes

Use o identificador efetivo apresentado na resposta. Primeiro consulte a experiência e verifique o conteúdo/metadata integral:

```powershell
$experienceId = Read-Host 'ID da experiência a revisar'
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" experience "$projectId" "$experienceId"
if ($LASTEXITCODE -ne 0) { throw 'Experiência não localizada no projeto.' }
```

Somente depois de revisão real, o operador pode usar `review`. O exemplo abaixo **não autoriza a execução automática das aprovações pelo modelo**:

```powershell
$expectedHash = Read-Host 'output_hash que corresponde ao resultado inspecionado'
$reviewer = Read-Host 'Revisor que realmente realizou a avaliação'
$note = Read-Host 'Evidência de correção e de direitos sobre TODO o contexto'
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" review "$projectId" "$experienceId" --expected-hash "$expectedHash" --reviewer "$reviewer" --verification-note "$note" --accepted --verified --rights-reviewed --training-allowed --split train
if ($LASTEXITCODE -ne 0) { throw 'A revisão não foi registrada.' }
```

Se qualquer decisão não ocorreu, não use sua flag. `verified` representa uma declaração do revisor no CLI atual: não é um avaliador automático comprovando o resultado. Vincule o relatório externo pertinente. A exportação candidata existente é:

```powershell
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" export-training "$projectId" text
if ($LASTEXITCODE -ne 0) { throw 'Nenhum dataset textual válido foi exportado.' }
# Execute separadamente para code ou image somente quando existirem exemplos aprovados desse tipo.
```

O export visual referencia PNGs privados; copie-os para um dataset autossuficiente com caminhos relativos e hashes antes de treinar. Não exportar só a frase “imagem gerada” como alvo visual. O JSONL atual exige conversão/validação para o trainer escolhido; não é um formato universal.

## Manifesto proposto para o novo pipeline

Cada exemplo precisa de: `example_id`, `task_family`, `project_group`, `modality`, `source_ids`, hashes das fontes, `context_hash`, `target_hash`, `rights_status`, `verification_receipt`, `reviewer`, `split` e revisão do gerador quando houver. Esse contrato deve ser implementado em ENG-01/02; não é um schema já aceito pelo CLI antigo.

Registre também dependências transitivas: se a resposta utiliza uma fonte, o exemplo depende dos direitos dessa fonte. Exclusão posterior deve bloquear exportações futuras e sinalizar datasets/checkpoints afetados; não prometer apagar conhecimento de pesos já treinados por exclusão de um arquivo.

## Partições e prevenção de contaminação

Agrupe variantes do mesmo bug, template, projeto, documento, sessão ou imagem-base antes de dividir. Faça a divisão **antes** de produzir paráfrases, recortes e outras variações. Recorte/flip de uma foto e renomeação de variáveis não criam independência.

Como ponto de partida operacional, reservar grupos para treino, validação e teste final, por exemplo 80/10/10, ajustando ao número de grupos reais. Não deixar uma família inteira sem avaliação; não apresentar porcentagem como garantia estatística. O export atual remove problemas exatamente repetidos presentes em validation/test, mas não garante deduplicação semântica nem ausência de gabarito no histórico.

Os casos finais ficam em área privada não indexada e fora do acesso do trainer. O avaliador recebe o candidato, não entrega seus gabaritos ao gerador de exemplos. Após consultar resultados e adaptar o sistema, aquele conjunto deixa de ser uma avaliação totalmente inédita para o próximo ciclo.

## Como aproveitar um modelo aberto como professor local

Peça exemplos com contrato verificável, variantes e explicação curta da solução. Execute testes independentes para código e use revisão humana para fatos/qualidade visual. Guarde tentativas rejeitadas como falhas de investigação, não como respostas-alvo corretas.

Dados sintéticos não devem dominar sem uma justificativa medida; multiplicar paráfrases pode aumentar volume sem aumentar cobertura. Aumentar o dataset só faz sentido quando adiciona famílias, casos-limite ou evidências novas. Não extrair supostos “pensamentos internos verdadeiros”; prefira justificativas observáveis, chamadas de ferramenta registradas e resultados.

## Critério de saída

Dataset imutável, manifesto, direitos verificáveis, deduplicação, grupos/partições, recibos dos testes, revisão de segredos e relatório de lacunas. Volume inicial pode ser pequeno para validar o pipeline; não declarar suficiência de treinamento por atingir determinado número de exemplos. Referências R2/R3 e T3/T4/T5 em [Fontes](../FONTES_E_COMPATIBILIDADE.md).
