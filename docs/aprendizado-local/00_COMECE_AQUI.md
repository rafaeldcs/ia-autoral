# LocalAuthor — pacote de aprendizado e conclusão local

**Versão do pacote:** 1.1, 05/10/2026 — publicação no repositório e encerramento com limpeza condicionada.  
**Código de referência inspecionado:** `rafaeldcs/ia-autoral`, commit `dd8a1376ad89230461fd85b2fcb5b5507590dcec`.  
**Natureza da entrega:** documentos de execução, conhecimento, currículo e avaliação. Não contém pesos, imagens de treinamento, um treinador novo implementado ou resultados de execução na máquina do proprietário.

## O que este pacote permite organizar

Concluir um ciclo verificável de evolução do LocalAuthor: preparar o ambiente, executar modelos locais reais, importar conhecimento, implementar as lacunas de treinamento, construir exemplos autorizados, treinar candidatos de texto/código e, quando justificado, de imagens, avaliar e promover somente os aprovados.

“Todo aprendizado necessário” significa, neste pacote, **as competências e os critérios da versão 1 definidos no currículo**, não conhecimento universal ou garantia de atingir a qualidade de modelos de fronteira. A conclusão exige evidências; ler todos estes arquivos não basta.

## Quem executa

O destinatário operacional é um **agente de desenvolvimento com ferramentas locais autorizadas ou um desenvolvedor humano**. O modo `/foundation` atual do LocalAuthor responde e gera imagens, mas não tem o executor geral nem o treinador necessários para realizar sozinho todas estas etapas. Colar o prompt nele, sem implementar essas capacidades, produziria instruções, não execução.

O produto continua sendo LocalAuthor. Bibliotecas e modelos locais especializados são componentes internos. O modelo textual não ganha geração de pixels somente por ler um Markdown; existe um caminho visual separado. Modelos derivados mantêm a procedência e as obrigações das bases.

## Como começar

1. O pacote está em `docs/aprendizado-local/` no repositório. Leia-o com o executor autorizado, sem importar ou indexar a pasta inteira. Para trabalhar fora do Git, copie-o para uma pasta **não indexada**, separada dos dados de produção. Não substitua o `AGENTS.md`: ele contém apenas um apontamento temporário para esta continuação.
2. Abra o repositório no executor local autorizado. Entregue-lhe [01_PROMPT_MESTRE_EXECUTOR_LOCAL.md](01_PROMPT_MESTRE_EXECUTOR_LOCAL.md), informando apenas o caminho local deste pacote e o repositório já aberto.
3. O executor deve começar pela inspeção da revisão atual e preencher uma cópia privada de [estado/ESTADO_EXECUCAO.template.md](estado/ESTADO_EXECUCAO.template.md).
4. Importe no LocalAuthor **somente a pasta `conhecimento/`**, após revisão, pelo procedimento de importação. Não importe o pacote inteiro.

A única autorização de remoção acrescentada pelo proprietário é a limpeza deste pacote temporário, **depois de executar e conferir todas as etapas**, conforme [99_CONFERENCIA_E_LIMPEZA.md](99_CONFERENCIA_E_LIMPEZA.md). Nenhum arquivo será apagado agora. Isso não autoriza apagar conhecimentos ativos, evidências, modelos, dados ou mudanças humanas, enviar dados a terceiros, comprar infraestrutura ou aceitar licenças pelo proprietário.

## Mapa e ordem de leitura

| Etapa | Documento | Resultado exigido |
|---|---|---|
| Missão | [Prompt mestre](01_PROMPT_MESTRE_EXECUTOR_LOCAL.md) | Executor identifica objetivo, limites e ponto de retomada |
| Estado | [Estado e conclusão](execucao/01_ESTADO_E_CRITERIOS_DE_CONCLUSAO.md) | Capacidades reais separadas de tarefas futuras |
| Ambiente | [Preparação Windows](execucao/02_PREPARACAO_WINDOWS.md) | Ambiente e dados preservados; diagnóstico registrado |
| Modelos | [Modelos e homologação](execucao/03_MODELOS_LOCAIS_E_HOMOLOGACAO.md) | Execução real local, com origem e hashes |
| Memória | [Importar conhecimento](execucao/04_IMPORTACAO_CONHECIMENTO.md) | Documentos recuperados no projeto certo |
| Desenvolvimento | [Implementações pendentes](execucao/05_IMPLEMENTACAO_DO_APRENDIZADO.md) | Treinadores, verificadores e promoção implementados e testados |
| Dados | [Curadoria e datasets](execucao/06_CURADORIA_E_DATASETS.md) | Exemplos autorizados e partições rastreáveis |
| Texto/código | [Treinamento textual](execucao/07_TREINAMENTO_TEXTO_CODIGO.md) | Candidato treinado e recarregado, não apenas loss menor |
| Imagens | [Treinamento visual](execucao/08_TREINAMENTO_IMAGENS.md) | Geração real; especialização visual quando houver necessidade e dados |
| Aceite | [Avaliação e promoção](execucao/09_AVALIACAO_PROMOCAO_ROLLBACK.md) | Comparação com a base e aprovação humana |
| Continuidade | [Operação e evolução](execucao/10_OPERACAO_E_EVOLUCAO.md) | Retomada segura, manutenção e reversão ensaiadas |
| Última etapa | [Conferência e limpeza](99_CONFERENCIA_E_LIMPEZA.md) | Aceite comprovado, conhecimento preservado e roteiros temporários removidos em commit separado |

## Pastas que não devem se misturar

`conhecimento/` é material consultável. `curriculo/` contém o programa didático e exemplos de desenvolvimento: não é uma prova independente. `avaliacao/` contém o protocolo para um avaliador separado; os casos finais serão criados fora do pacote e fora do alcance do treinamento. `estado/` contém modelos de registros vazios; as cópias preenchidas ficam em armazenamento privado.

Leia [FONTES_E_COMPATIBILIDADE.md](FONTES_E_COMPATIBILIDADE.md) para conferir os contratos existentes. O manifesto e os hashes acompanham o ZIP para verificar integridade. Nenhum indicador de progresso deste pacote vem marcado como treinamento realizado.

## Atenção ao indexar o próprio repositório

A presença no Git não torna este pacote uma fonte autorizada de RAG ou treinamento. Não indexe a raiz inteira do LocalAuthor enquanto o indexador não excluir estes roteiros, currículos, avaliações e templates. Use uma cópia de laboratório contendo apenas fontes autorizadas ou implemente exclusões testadas. Casos e gabaritos finais continuam fora do Git e do alcance do candidato.

Um nível parcial ou um item obrigatório bloqueado não libera a limpeza. A condição final é a conclusão integral do escopo v1 aceito, não apenas o término de uma sessão.
