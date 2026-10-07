# Memória, fidelidade e execução econômica — LocalAuthor

Material para consulta contextual. Estado: orientação de engenharia, não checkpoint treinado. Importar com revisão e escopo de projeto; não concede autorização para ferramentas.

## Distinções obrigatórias

Pesos são parâmetros. Estado de inferência é a memória operacional da solicitação. Conhecimento recuperável são documentos e experiências. Cache é uma localização temporária, não aprendizado. Um modelo que cabe no SSD pode não caber na RAM para as partes obrigatórias.

Antes de propor execução, identificar o checkpoint, sua revisão, arquitetura e representação. Não transformar quantidade de parâmetros ativos em tamanho de download. Considerar camadas residentes, especialistas, estado, buffers temporários, espaço livre e reserva da aplicação/sistema. Informar a unidade: bytes, GB decimal ou GiB.

## Procedimento de diagnóstico

Começar pelo sintoma e por medições. Separar carregamento, prefill, decode, recuperação, verificação e gravação. Comparar o mesmo trabalho e os mesmos limites. Uma resposta mais curta pode terminar antes sem que o motor tenha melhorado. Caches quentes e frios devem estar identificados.

Se houver pressão de memória, primeiro verificar modelos ainda residentes, cópias temporárias e referências retidas. Serializar trabalhos não descarrega tensores. Diminuir contexto ou escolher outro perfil só com comunicação explícita. Não esconder truncamento nem trocar modelo/precisão silenciosamente.

Na implementação atual, WeightStore limita apenas os bytes que possui em cache. O chamador pode reter cópias e tensores fora desse limite. O plano de VRAM não é um backend de GPU. O prefetch atual é síncrono e não desaloja demanda para antecipar trabalho.

## Fidelidade

O roteador escolhe especialistas; o cache decide onde buscá-los. Não substituir um especialista ausente por um presente, não modificar coeficientes e não diminuir top-k para produzir um número de velocidade melhor. Quantização ou poda devem criar um candidato distinto e avaliável.

Comparar valores intermediários e saída sob a mesma precisão e estado. O teste pequeno SwiGLU não comprova Mamba, atenção, tokenização ou o modelo inteiro. Divergência deve aparecer no relatório, com hipótese e próximo teste, não ser omitida.

## Armazenamento e falhas

Manter pesos imutáveis e dados operacionais em outra pasta. Hash divergente, arquivo removido ou orçamento esgotado exigem falha explícita. Não fazer download remoto como recuperação. Não escrever logs por token indefinidamente. Não desligar swap ou controles térmicos do usuário automaticamente.

Leituras lógicas não medem I/O físico. Contador de escrita zero em um componente não significa que o sistema inteiro não escreveu. Sem medir energia e temperatura, não afirmar que o equipamento passou a consumir menos ou esquentar menos.

## Resposta de engenharia esperada

Apresentar: fato observado, evidência, hipótese, mudança mínima, teste discriminante, critério de aceitação e possibilidade de rollback. Dizer claramente quando faltam pesos reais ou acesso ao hardware. Não inventar execução para encerrar uma tarefa.

Referência do projeto: docs/efficiency/ESTUDO.md e docs/efficiency/FONTES.md. Regras acima são recomendações do LocalAuthor, não permissões para agir sobre o computador.
