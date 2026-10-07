# LocalAuthor — núcleo de eficiência verificável

Estudo e implementação iniciados em 7 de outubro de 2026 e incorporados à branch principal `main`. Objetivo: incorporar conceitos úteis no próprio LocalAuthor, sem APIs externas de inferência, preservando procedência de código, dados e pesos. O PR #3 foi integrado e encerrado; não é necessário selecionar a antiga branch para obter o upgrade.

## O que foi entregue

| Componente | Estado nesta entrega |
|---|---|
| Cache original de blocos em RAM, leitura sob demanda, SHA-256 e orçamento de leitura | Implementado; testes CPU sintéticos |
| Planejamento de RAM/VRAM, reservas e staging | Implementado como cálculo; não aplica limites ao sistema operacional |
| Execução SwiGLU de especialistas pequenos | Oráculo sintético; não é um forward Nemotron |
| Alternância entre modelo textual e visual | Integrada ao FoundationService: libera o anterior antes de carregar o seguinte |
| Perfil de raciocínio e tempo de geração | Manifesto e CLI; suporte do template precisa ser homologado por checkpoint |
| Encerramento da aplicação e da fila | Libera modelos após parada confirmada; não descarta recursos de worker ainda ativo |
| Verificação local de checkpoint | CLI `localauthor.foundation.smoke` com processo descartável e orçamento total |
| Critério de aceitação de candidatos de aprendizado | Implementado para relatórios de avaliador confiável; não treina nem promove pesos |
| Distribuição do código da main | Pacote com revisão e hash; job dependente dos testes de software |
| Streaming real de Nemotron em CUDA/CPU | Pendente: decodificador, layouts, forward e estados específicos |
| Treinamento/distilação de pesos, embeddings semânticos, agente com ferramentas e multimodalidade nova | Especificados, não executados por esta entrega |

As bibliotecas locais de referência existentes permanecem. O laboratório neural autoral continua separado. Nenhum cliente de serviço externo de IA, peso ou dataset foi adicionado ao Git.

## Leitura

- [Publicação da main e teste local do checkpoint](../PUBLICACAO_MAIN.md).
- [Estudo e arquitetura](ESTUDO.md): decisões, matemática de memória, hipóteses, riscos e sequência de evolução.
- [Procedimento local e critérios de aceitação](EXECUCAO_LOCAL.md): comandos e evidências exigidas.
- [Fontes e procedência](FONTES.md): referências primárias e limites de reutilização.
- [Conhecimento: memória e fidelidade](../../knowledge/efficiency/01_memoria_fidelidade.md).
- [Conhecimento: aprendizado verificável](../../knowledge/efficiency/02_aprendizado_verificavel.md).
- [Conhecimento: programação e multimodalidade](../../knowledge/efficiency/03_programacao_multimodalidade.md).

## Evidências históricas

O commit `4a3e4b813b8df3ae1467156f2c15ade5b3d95784` passou no GitHub Actions run `37627459914`: sete jobs, incluindo Python 3.13/3.14 em Ubuntu/Windows, .NET nas duas plataformas e interface. O log Windows/Python 3.13 registra 356 testes aprovados sem skips. Esse é o resultado da revisão anterior às correções de encerramento e publicação; conferir o CI do novo commit, não reutilizar aprovação antiga como se cobrisse código diferente.

O primeiro CI detectou uma divergência stat/fstat no Windows. A correção usa descritores de forma consistente sem remover campos de identidade, timestamps ou SHA-256 e inclui teste de regressão (fonte S13).

O `self-check` gerou quatro especialistas minúsculos temporários e comparou 32 passos: saídas idênticas; 393216 bytes de leituras lógicas sem cache e 24576 com cache de 12288 bytes. A redução calculada é 93,75%, somente nessa sequência deliberadamente repetitiva. Não mede NVMe físico, desgaste, energia ou habilidade de programação. Não generalizar a redução para modelos reais.

## Regra de comunicação

`Importado para consulta` não significa `treinado`. `Registrado` não significa `compatível`. `Teste sintético passou` não significa `Nemotron executado`. `Código enviado` não significa `instalado no servidor de Rafael`.

Não remover os documentos temporários de `docs/aprendizado-local` nem seu bloco em `AGENTS.md` antes de cumprir a conferência que eles exigem.
