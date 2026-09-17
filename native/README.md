# Backend nativo/GPU — não implementado

Esta entrega possui um Transformer CPU funcional em `src/localauthor/nn/`.
Não contém backend CUDA, cuBLAS, kernels GPU nem integração nativa disfarçada de pronta.

Próximo aceite: kernels forward/backward, testes de diferenças finitas, concordância CPU/GPU,
medição de VRAM e checkpoint interoperável na RTX 2060 do usuário.
Não aumentar o modelo para 34 milhões antes desse aceite e do diagnóstico do notebook.
