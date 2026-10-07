# LocalAuthor — núcleo de eficiência verificável

Estudo e implementação inicial em 7 de outubro de 2026. Objetivo: incorporar conceitos úteis no próprio LocalAuthor, sem APIs externas de inferência, preservando procedência de código, dados e pesos.

## O que foi entregue

| Componente | Estado nesta entrega |
|---|---|
| Cache original de blocos em RAM, leitura sob demanda, SHA-256 e orçamento de leitura | Implementado; testes CPU sintéticos |
| Planejamento de RAM/VRAM, reservas e staging | Implementado como cálculo; não aplica limites ao sistema operacional |
| Execução SwiGLU de especialistas pequenos | Oráculo sintético; não é um forward Nemotron |
| Alternância entre modelo textual e visual | Integrada ao FoundationService: libera o anterior antes de carregar o seguinte |
| Perfil de raciocínio e tempo de geração | Manifesto e CLI; suporte do template ainda precisa ser homologado |
| Critério de aceitação de candidatos de aprendizado | Implementado para relatórios de avaliador confiável; não treina nem promove pesos |
| Streaming real de Nemotron em CUDA/CPU | Pendente: decodificador, layouts, forward e estados específicos |
| Treinamento/distilação de pesos, embeddings semânticos, agente com ferramentas e multimodalidade nova | Especificados, não executados por esta entrega |

As bibliotecas locais de referência existentes permanecem. O laboratório neural autoral continua separado. Nenhum cliente de serviço externo de IA, peso ou dataset foi adicionado ao Git.

## Leitura

- [Estudo e arquitetura](ESTUDO.md): decisões, matemática de memória, hipóteses, riscos e sequência de evolução.
- [Procedimento local e critérios de aceitação](EXECUCAO_LOCAL.md): comandos e evidências exigidas.
- [Fontes e procedência](FONTES.md): referências primárias e limites de reutilização.
- [Conhecimento: memória e fidelidade](../../knowledge/efficiency/01_memoria_fidelidade.md).
- [Conhecimento: aprendizado verificável](../../knowledge/efficiency/02_aprendizado_verificavel.md).
- [Conhecimento: programação e multimodalidade](../../knowledge/efficiency/03_programacao_multimodalidade.md).

## Evidência inicial

Foram executados 49 testes do núcleo em Python 3.13.5 e NumPy 2.3.5, CPU, numa cópia parcial dos módulos. Os hashes Git dos sete arquivos de `efficiency` foram comparados com o commit `98c0e89d744d5be017ca3c81f10038ef28120314` e coincidiram. Isso não substitui a suíte completa no checkout real.

O `self-check` gerou quatro especialistas minúsculos temporários e comparou 32 passos: saídas idênticas; 393216 bytes de leituras lógicas sem cache e 24576 com cache de 12288 bytes. A redução calculada é 93,75%, somente nessa sequência deliberadamente repetitiva. Não mede NVMe físico, desgaste, energia ou habilidade de programação. Não generalizar a redução para modelos reais.

O primeiro CI do PR executou 355 testes: as matrizes Ubuntu/Python 3.13 e 3.14 passaram, assim como os builds e smoke tests .NET em Ubuntu/Windows e os smoke tests de interface. As matrizes Python no Windows detectaram um falso positivo na comparação de metadados de arquivos; os 15 novos testes de integração do Foundation passaram mesmo nessas matrizes.

A correção usa `fstat` de forma consistente sem remover campos de identidade, timestamps ou SHA-256 (ver fonte S13). Um teste de regressão adicional reproduz a divergência entre metadados de caminho e de descritor. Foram executados 50 testes locais do núcleo após essa correção. A próxima execução completa deve descobrir 356 testes. Consulte o resultado do GitHub Actions no commit avaliado; a presença deste documento não significa CI aprovado. O PR #3 registra a situação de validação.

## Regra de comunicação

`Importado para consulta` não significa `treinado`. `Registrado` não significa `compatível`. `Teste sintético passou` não significa `Nemotron executado`. `Código enviado` não significa `instalado no servidor de Rafael`.

Não remover os documentos temporários de `docs/aprendizado-local` nem seu bloco em `AGENTS.md` antes de cumprir a conferência que eles exigem.
