# Seleção, registro e homologação de modelos reais

## Selecionar por capacidade, não por nome

Selecione um checkpoint textual para conversa/código e outro visual para geração. Não há motivo para assumir que ambos serão NVIDIA. O componente visual precisa ser compatível com o pipeline efetivamente implementado. A escolha final exige comparação local e revisão da licença exata.

A ficha oficial consultada do Nemotron 3 Nano BF16 documenta entrada e saída textuais, arquitetura híbrida e suporte nativo a partir de Transformers 5.3. Isso não qualifica outro Nemotron, outra quantização ou o Ultra. O pacote não depende de afirmações anteriores sobre benchmarks ou datas de lançamento do Ultra. Verifique toda variante no material oficial antes de selecioná-la. Referência T2.

Não existe transferência automática do conhecimento desses pesos para o Transformer NumPy do LocalAuthor. Usar uma base original, especializá-la ou destilar exemplos dela são processos diferentes; preserve essa distinção no registro de modelo.

## Dossiê mínimo de aquisição

Para cada modelo, registrar em arquivo privado: publicador, identificador, revisão imutável, licença consultada, permissões de uso/derivação/destilação/redistribuição, arquivos incluídos, hashes, formato, tokenizador, arquitetura, biblioteca e versão exigidas. Campos desconhecidos bloqueiam a aquisição/uso pertinente; não preencher por inferência.

Downloads devem ser explícitos, limitados à aquisição e previamente dimensionados. Credenciais de acesso a modelos restritos permanecem fora de prompts, logs e Markdown. Offline significa que a execução não depende do servidor do fornecedor, não que a fase de obtenção possa ignorar licenciamento.

## Compatibilidade exigida pelo código atual

Texto exige pasta completa Transformers com Safetensors, configuração e tokenizador; imagem exige pipeline Diffusers completo com Safetensors. O inventário rejeita links simbólicos e formatos pickle. Um cache composto por links precisa ser materializado em arquivos regulares numa cópia revisada.

O registro não sobrescreve o manifesto ativo. Um LoRA isolado, um GGUF ou um arquivo NVFP4 não podem ser apontados como se fossem o formato aceito. Não renomear extensões para contornar a validação. A revisão de código customizado é uma decisão humana de segurança, não solução genérica para erro de importação.

## Registro com a CLI existente

Execute após preencher os valores reais no estado privado. Não use `main` como se fosse uma revisão imutável do modelo. O exemplo utiliza CPU/float32 por simplicidade de sintaxe, **não como recomendação de capacidade ou desempenho**. Altere dispositivo e precisão apenas após homologação.

```powershell
$textDir = Read-Host 'Pasta absoluta do checkpoint textual completo e revisado'
$textId = Read-Host 'Identificador real da origem/modelo'
$textRevision = Read-Host 'Revisão imutável verificada'
$textLicense = Read-Host 'Identificador da licença revisada'
$reviewer = Read-Host 'Nome do operador que realizou a revisão'
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" register-model text "$textDir" --model-id "$textId" --revision "$textRevision" --license "$textLicense" --reviewed-by "$reviewer" --device cpu --dtype float32 --context-tokens 4096 --output-tokens 768
if ($LASTEXITCODE -ne 0) { throw 'Registro textual falhou. Não sobrescreva o manifesto existente.' }
```

Para imagem, repita com os dados do modelo visual, e não os dados do textual:

```powershell
$imageDir = Read-Host 'Pasta absoluta do pipeline visual completo e revisado'
$imageId = Read-Host 'Identificador real do modelo visual'
$imageRevision = Read-Host 'Revisão imutável do modelo visual'
$imageLicense = Read-Host 'Licença visual revisada'
& $python -m localauthor.foundation --home "$env:LOCALAI_HOME" register-model image "$imageDir" --model-id "$imageId" --revision "$imageRevision" --license "$imageLicense" --reviewed-by "$reviewer" --device cpu --dtype float32
if ($LASTEXITCODE -ne 0) { throw 'Registro visual falhou; investigar sem contornar a validação.' }
```

A CLI também aceita `cuda`, e apenas texto aceita a execução `auto` no runtime. Não concluir que `auto` elimina limites de memória. Para ensaios de candidatos, usar área experimental separada da instalação ativa.

## Teste de ponta a ponta

Com o mesmo Python e os dados corretos, inicie o servidor usando `localauthor --home CAMINHO serve`; obtenha o token somente no terminal local com o comando `token`. Não capture o token em relatório. Abra `/foundation` no endereço local exibido.

Execute pelo menos um pedido textual, um pedido de código e um brief visual. Confirme que os resultados vieram dos modelos reais, e não dos dublês da suíte. Para o PNG, verifique abertura, dimensões, hash e correspondência ao pedido. Não considerar os primeiros bytes PNG suficientes para qualidade visual.

Mantenha o modelo sem acesso de rede durante a prova. As opções offline das bibliotecas são defesa adicional, não firewall. Observe tentativas de saída com uma ferramenta do sistema aprovada e registre método/limitações; a ausência de um log de rede não prova isolamento.

Meça carregamento, memória, duração e geração; não estime esses números pelo tamanho do arquivo. Teste cancelamento e erro por modelo ausente, sem modificar pesos ou manifestos reais: use cópias de teste. Timeout da geração não garante interromper carregamento nem kernel GPU imediatamente.

## Critério de saída

Relatório com versões, licença, hashes, saídas reais, medidas, evidências de offline e resultado da inspeção humana. `registered=true` é apenas registro. `loaded=true` é carregamento. Nenhum dos dois significa “treinado” ou “programador qualificado”.

Referências R2–R5, T1, T2 e T6 em [Fontes](../FONTES_E_COMPATIBILIDADE.md).
