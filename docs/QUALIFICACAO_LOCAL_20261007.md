# Qualificação local de marketing, negócio e QA - 07/10/2026

**Estado: software validado; autonomia do modelo não homologada.** Não há evidência de ausência universal de erros. Aprovação de todos os testes executados não significa aprovação de todos os casos possíveis. Não foi promovido um perfil neural reprovado.

## Melhorias concretas

A LocalAuthor escreveu funções de cálculo, validação, interface, filtro de diagnósticos e métodos de QA, com feedback e revisão. O supervisor definiu contratos, revisou propostas, montou fragmentos, integrou componentes e escreveu oráculos independentes e controladores de sandbox. Esta é autoria supervisionada, não programação autônoma.

Os cálculos autenticados de campanha, ativação e caixa estão implementados. A interface trata unidades monetárias, entradas inválidas, valores indisponíveis, saldo negativo e resultados obsoletos. O filtro preserva diagnóstico de inicialização/GPU e limites de segurança. O método adicional de campo extra usa um inteiro válido para distinguir erro de esquema de erro de tipo; sua primeira versão passava pelo motivo errado.

## Resultados de software

| Evidência | Resultado | Alcance |
| --- | --- | --- |
| Suíte Linux real | 537/537; zero falhas, erros ou pulos | Código de software, não inteligência |
| Oráculos de aritmética | 13.842 combinações mais validações | Conjunto finito, não domínio inteiro |
| Navegador | 14 fluxos de integração + 1 exercício funcional da IA | API aritmética real; geração usa dublês explícitos |
| Primeiro exercício da IA | 4/4 métodos e 4/4 mutantes | Correção e montagem supervisionadas |
| Segundo exercício da IA | 6/6 métodos e 6/6 mutantes | Expectativas monetárias ensinadas, fragmentos montados pelo supervisor |

Cada mutante alterou a implementação em cópia descartável. As falhas exigidas foram asserções de comportamento, não erro de importação/sintaxe. Os bytes da fonte foram restaurados. A primeira instrução do segundo exercício era ambígua: não serve como avaliação justa de transferência. Após esclarecer o contrato, ainda houve erros reais de unidade e exceção. Erros do controlador, incluindo descoberta vazia, foram separados dos erros do modelo; nenhum zero testes foi aceito como sucesso.

A regeneração integral posterior de seis métodos foi rejeitada por reintroduzir um campo inexistente e manter um teste negativo ambíguo. A versão final aprovada reúne cinco métodos da proposta válida e um método pontual corrigido pela IA. Nenhuma proposta foi executada no Windows: código revisado e analisado entrou somente em sandbox Linux inspecionada, sem rede, privilégios ou fallback no host.

## Qualidade dos modelos reais

| Perfil experimental | Aprovados | Parciais | Reprovados ou inválidos |
| --- | ---: | ---: | ---: |
| Qwen3-8B Q4_K_M, 32 regressões | 7 | 11 | 14 |
| Qwen3-8B Q4_K_M, 24 casos novos | 12 | 6 | 6 |
| Qwen3.5-4B Q8_0, 32 casos | 7 | 11 | 13 + 1 truncado |
| Qwen3.5-4B, 32 correções específicas, sem thinking | 7 | 7 | 18 |
| Qwen3.5-9B Q3_K_M, 18 casos novos | 3 | 8 | 7 |
| Qwen3.5-9B, 14 comparações executadas | 4 | 3 | 7 |
| Qwen3.5-9B, última rodada de 6 itens assistidos | 3 | 2 | 1 |
| Qwen3.5-9B, 6 perguntas novas nessa rodada | 0 | 5 | 1 |

Os perfis têm parâmetros e exposição diferentes: não comparar as taxas como experimento causal de tamanho do modelo. Os pesos 8B carregaram 37/37 camadas; 4B e 9B carregaram 33/33 na GPU. Isso comprova execução, não competência. Origens, revisões, licenças Apache-2.0, hashes e diagnósticos foram preservados privadamente. Não houve API externa de IA, download automático do aplicativo, LoRA ou alteração de pesos.

O ensaio inicial 9B teve rejeição do worker ao começar a 15ª comparação; causa não comprovada. Restaram 18 comparações e o QA planejado nessa fase sem execução. Rodadas posteriores são ensaios separados e não tornam o perfil inicial completo. A auto revisão 4B aprovou quatro respostas entre seis revisadas externamente; três dessas aprovações mantinham erros. Essa estratégia foi interrompida explicitamente pelo supervisor e não foi registrada como conclusão de 32 casos.

Na rodada de seis perguntas novas, os gabaritos não foram enviados ao modelo, mas também não houve recuperação das lições centrais. Ela não mede o efeito da consulta. As correções seguintes recebem feedback e trechos verificados dessas lições: são assistidas, com expectativa fornecida, e não substituem uma nova avaliação independente. Primeiras tentativas, reprovações e diferenças permanecem privadas.

Na correção com trechos centrais, oito itens tiveram 4 aprovações, 3 parciais e 1 reprovação; uma aprovação refere-se somente ao fragmento matemático solicitado. A rodada seguinte restringiu o campo de ação para manter a entrega em resposta: 5 itens, **3 aprovados, 1 parcial e 1 reprovado**. As respostas ainda ecoam instruções; o anúncio descreveu um CTA em vez de entregar o convite, e o plano de reserva chamou expectativas de fatos observados. Essa restrição foi somente experimental, sem alterar a configuração de produção. A cópia inicial do controlador omitiu um script confiável; o erro foi corrigido e preservado separadamente, sem inferência do modelo executada naquela tentativa. Nenhuma dessas correções é prova cega de autonomia.

## Conhecimento no servidor central

As lições revisadas de cálculos, testes, pesquisa de marketing e acessibilidade foram importadas para consulta nos projetos ShopAir, Orbit e aprendizado, com backup CRC/SHA-256 e hashes dos documentos conferidos. Os registros mantêm `training_allowed=false`. Atualizar contexto consultável não modifica os pesos nem autoriza treinar com casos privados. O perfil experimental não foi ativado como padrão do servidor.

O material de pesquisa distingue hipótese de resultado, atribuição de incremento causal e alvo WCAG AA de AAA. Também ensina solicitar escolha entre referência visual e proposta original, revisar direitos e não inventar preço, status, compromisso ou benefício. Planos não são integrações operacionais nem execução autorizada.

Não houve publicação social, gasto, cobrança, deploy de produção ou uso da conta ShopAir Super nesta rodada. A conta de QA mantém as restrições próprias. Push de código não publica instalador nem distribui pesos automaticamente.

## Uso e verificação

Consulte [Cálculos e QA](CALCULOS_NEGOCIO_QA.md) e [Publicação na main](PUBLICACAO_MAIN.md). O CI deve ser conferido no SHA publicado, incluindo as oito etapas reais de Python Windows/Linux, .NET, navegador e pacote. O resultado do CI é registrado após o push; não usar sucesso de um SHA anterior como sucesso da revisão final.

A pendência de autonomia permanece: precisa de avaliação nova apropriada ao uso e evidência de correção generalizável. Não retirar proteções, reescrever gabaritos ou ocultar respostas ruins para declarar 100%. Os documentos temporários de aprendizado permanecem porque os critérios completos de treino/homologação não foram cumpridos.
