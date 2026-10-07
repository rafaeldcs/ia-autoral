# Primeiro incremento com matrizes de um checkpoint real

`localauthor.efficiency.safetensor_store` conecta o `WeightStore` existente a
matrizes F32/BF16 de um arquivo local `model.safetensors`. As funções foram
propostas pela LocalAuthor com Qwen3-8B local e revisão do supervisor. As
correções de tipos inteiros exigiram orientação explícita. Os testes de
regressão são do verificador independente: os rascunhos de testes produzidos
pelo modelo tiveram erros e não foram aceitos como prova de autonomia.

## API implementada

`build_matrix_store(spec, names, cache_bytes=..., max_block_bytes=...)` verifica
o inventário e os hashes do `ModelSpec`, lê um cabeçalho limitado, confere as
matrizes selecionadas e retorna `(store, metadata)`. `decode_matrix(store,
metadata, name, cancel=None)` usa o leitor com integridade e cancelamento para
devolver a matriz NumPy. Os argumentos de orçamento são somente por nome.

Este componente exige arquivos imutáveis sob controle do operador e um
manifesto de procedência previamente revisado. Não é um validador completo do
formato Safetensors para entradas arbitrárias: não verifica todos os tensores,
lacunas do arquivo ou duplicatas de chaves. A seleção aceita somente matrizes
de duas dimensões F32/BF16. Não implementa inferência completa, GPU,
especialistas MoE, treinamento ou troca automática de checkpoint.

O cache contabiliza bytes brutos. Matrizes decodificadas, referências mantidas
pelo chamador, estado de inferência e buffers adicionais precisam de reservas
separadas. `store.clear()` libera o cache; não elimina referências externas.
A montagem verifica o checkpoint inteiro e lê os blocos escolhidos para gerar
seus hashes. Essas leituras de montagem não estão nos contadores do cache.
O evento de cancelamento atua nas leituras de `decode_matrix`, não cancela a
verificação inicial de todo o manifesto.

## Evidência desta execução

Em sandbox CPU sem rede, com pesos somente para leitura, o Qwen3-0.6B da
revisão `c1899de289a04d12100db370d81485cdf75e47ca` forneceu as matrizes BF16
`gate_proj`, `up_proj` e `down_proj` da primeira camada MLP. A leitura própria
foi comparada com `safetensors.safe_open` e PyTorch em float32. Os valores das
matrizes, os intermediários e as saídas para duas entradas sintéticas foram
exatamente iguais, com tolerância absoluta zero.

O primeiro acesso leu 18.874.368 bytes lógicos; a repetição acrescentou zero
bytes e registrou três acertos de cache. Cada conjunto das três matrizes
decodificadas ocupa 37.748.736 bytes, além do cache bruto. O processo de QA,
incluindo referências e duas cópias decodificadas, atingiu 370.667.520 bytes de
RSS máximo naquele contêiner. O cancelamento não acrescentou leituras e a
integridade da base foi conferida novamente ao final.

Não generalizar essas medidas para geração completa, acesso físico ao SSD,
consumo de energia, temperatura, desgaste ou capacidade intelectual. A
validação não executou Nemotron, roteamento MoE nem treinamento. O runtime
normal de geração continua usando os backends previamente registrados.

O relatório sanitizado está em
[`20261007-runtime-learning.json`](../learning-evidence/20261007-runtime-learning.json).
Os executores e os registros completos permanecem privados. O próximo
incremento deve validar a arquitetura e os estados completos antes de ligar
esse leitor à geração. O piloto LoRA é uma frente independente e continua
sujeito à aprovação real dos dados.
