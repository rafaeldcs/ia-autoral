# Capacidade visual: gerar, avaliar e especializar quando necessário

## Separação indispensável

Uma descrição textual melhor pode ajudar o gerador visual, mas não altera os pesos dele. O modelo textual da base não passa a produzir pixels porque leu instruções sobre composição. O LocalAuthor usa um pipeline visual distinto; sua qualidade precisa ser medida separadamente. O código de referência não compreende nem edita imagens de entrada. Referências R2/R4.

A primeira conclusão visual deve ser **geração real homologada**, mesmo que sem fine-tuning. Só treinar quando houver uma meta mensurável não atendida pela base: por exemplo, consistência de um conjunto de ícones próprios ou um vocabulário visual autorizado. Não treinar apenas para poder dizer que houve aprendizado.

## Geração inicial e limites existentes

O runtime atual usa 512 × 512, 20 passos, seed 31 e exige callback de cancelamento compatível. Não concluir que esses parâmetros são apropriados para qualquer pipeline. Homologar o modelo escolhido nesse perfil ou implementar perfis validados em ENG-09. A API de referência não permite presumir suporte a dimensões, negative prompt, máscaras, imagem-guia ou seed configurável.

Gere briefs do currículo visual em ambiente privado. Salve PNG, hash, prompt efetivamente enviado, modelo, versões e parâmetros. Visualize o resultado com uma ferramenta real. Um modelo sem entrada de imagem não pode “aprovar visualmente” o PNG; use um avaliador humano ou um componente visual separado e identificado.

## Dataset visual

Usar apenas imagens próprias/autorizadas. Cada item precisa de arquivo íntegro, hash, dimensões, legenda revisada, origem, permissões e grupo de origem. Legenda descreve o conteúdo visível, não o conteúdo que se desejava ver. Não incluir screenshots com segredos ou dados pessoais sem tratamento e autorização.

Separar imagens do mesmo produto, pessoa, sessão, arte-base e suas derivações no mesmo grupo antes da divisão. Guardar a imagem original; transformações de recorte/redimensionamento devem ter política registrada. Não cortar detalhes que definem o requisito nem inverter uma imagem quando a direção espacial importa.

Dataset do eixo visual é imagem+texto, não JSON de conversas sem os PNGs. O export `image` do LocalAuthor é um ponto de partida para curadoria, não um trainer. As regras de conteúdo e consentimento continuam aplicáveis aos dados e aos resultados.

## Treinamento visual proposto

Concluir ENG-10 com uma receita oficial adequada ao modelo selecionado. Diffusers fornece exemplos distintos por tarefa e arquitetura; um script para uma família não deve ser usado em outra somente porque ambos geram imagens. Registrar o commit da receita e suas dependências. Referências T5/T7.

Primeiro piloto: carregamento do conjunto pequeno autorizado, pré-processamento conferido, forward/backward, gradientes finitos, atualização do adaptador/parâmetros esperados, checkpoint e recarga. Não copiar configurações de resolução, schedule e alvos LoRA do treino textual.

Depois executar a especialização delimitada, com prompts de validação que não apareçam como cópias do treino. Não ativar upload ao Hub nem trackers remotos; logs e validação ficam locais. O executor deve remover essas opções de exemplos oficiais antes de utilizá-los, mantendo o propósito da receita.

## Avaliação visual

Comparar base e candidato com os mesmos briefs e política de amostragem. Não selecionar apenas a melhor imagem e esconder as demais. Quando ENG-09 permitir seeds variados, predefinir o conjunto; no perfil fixo atual, declarar que a avaliação cobre uma única seed.

Rubrica: atendimento às restrições obrigatórias, composição, coerência entre objetos, fidelidade às cores solicitadas, ausência de deformações relevantes, legibilidade quando houver texto e consistência de série. Inspeção humana deve anotar o motivo de cada nota; nota de um modelo avaliador não é verdade absoluta.

Checar semelhança indevida com exemplos de treino e perda de diversidade, especialmente em datasets pequenos. Se o candidato memoriza os exemplos e falha em briefs novos, rejeitar a promoção.

## Export e ativação

O adaptador visual deve ser compatível com a base/pipeline exatos. O runtime atual exige export completo em Safetensors: produzir export seguro em pasta nova se suportado ou implementar um carregador de adaptadores versionados com validação. Não declarar que fundiu pesos sem realizar o procedimento e recarregar o resultado.

Registrar a relação entre base, adaptador, tokenizer/text encoders, scheduler e configuração. Revalidar a geração pela interface do LocalAuthor, e não apenas pelo script do trainer. A troca de pipeline não pode remover os controles existentes.

## Critério de saída

Relatório com imagens reais inspecionadas, comparação, direitos, hashes e decisão. Distinguir “o briefing melhorou”, “a base gerou”, “o modelo visual foi treinado” e “o candidato visual foi aprovado”. Entendimento/edição de imagens, áudio e vídeo continuam fora do mínimo desta etapa.
