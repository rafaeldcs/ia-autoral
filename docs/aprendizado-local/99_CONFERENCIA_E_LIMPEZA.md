# Última etapa — conferir tudo e apagar somente os roteiros temporários

**Executar por último. Não apagar nada ao instalar, ler ou importar este pacote.**

O proprietário solicitou que estes Markdown sejam colocados no GitHub e retirados ao final, depois de executar todos os passos e conferi-los. Esta é uma autorização condicional e limitada ao pacote `docs/aprendizado-local/`. Não é autorização para apagar o aprendizado, modelos, dados ou o repositório.

## 1. Portão obrigatório de conclusão

Reabrir a cópia privada do estado e conferir cada etapa contra seus artefatos reais. Não usar apenas a palavra `CONCLUIDO` escrita pelo próprio executor como prova.

| Conferência | Evidência necessária para liberar a limpeza |
|---|---|
| Ambiente e preservação | Revisão real, testes, backup e restauração ensaiados |
| Modelos reais | Texto e imagem efetivamente gerados; origem, licença e hashes registrados |
| Conhecimento | Sete notas preservadas, fontes corretas, recuperação e isolamento retestados |
| Implementações | Itens aplicáveis do plano implementados e testados, não apenas descritos |
| Dados e treinamento | Direitos de todo o contexto; partições; piloto, treino e recarga reais quando exigidos |
| Currículos e avaliação | Competências v1 aplicáveis avaliadas com critérios congelados; falhas incluídas na contagem |
| Decisão visual | Geração validada; fine-tuning realizado quando exigido, ou dispensa de escopo fundamentada e aceita |
| Aceite e operação | Resultado que atende à meta, decisão humana real, versão ativa e rollback demonstrados |
| Relatório | Comandos, recibos, hashes, limitações e revisão final efetivamente conferidos |

**Qualquer requisito obrigatório PENDENTE, EM_EXECUCAO, BLOQUEADO, FALHOU ou sem evidência impede apagar o pacote.** Uma entrega parcial ou candidato rejeitado sem solução para a meta não libera a limpeza. Item opcional `NAO_APLICAVEL` exige decisão de escopo documentada e aceita; não rebaixar requisitos para declarar sucesso.

Não exigir novo aceite só para repetir a autorização de remoção já dada: cumprir a condição e registrar o recibo. As aprovações de direitos, modelos e resultados previstas no processo continuam exigindo decisões humanas reais; o executor não pode assiná-las em nome do proprietário.

## 2. Preservar antes de remover

1. Guardar uma cópia íntegra deste pacote e de seu manifesto na área privada de evidências, fora do Git e dos projetos indexados. Registrar commit de origem e SHA-256; conferir a cópia antes de continuar.
2. Manter todas as cópias preenchidas de `estado/`, os relatórios de avaliação, aprovações, checkpoints, adaptadores, datasets autorizados, imagens, backups, SQLite e diários. Não publicá-los nem apagá-los nesta operação.
3. Mover as sete notas públicas de `conhecimento/` para `knowledge/aprendizado-local/`, preservando nomes e bytes. Se o destino existir, comparar hashes: reutilizar somente cópia idêntica; em conflito, parar e reconciliar sem sobrescrever mudanças humanas. Preservar também as cópias privadas registradas no LocalAuthor.
4. Preservar procedimentos duráveis necessários à operação fora da pasta temporária, após revisão. Não misturar gabaritos reservados ou dados privados com documentação pública.
5. Reabrir as fontes privadas importadas, conferir seus hashes e testar recuperação. Executar consultas de sanidade e uma geração visual real no modelo ativo; registrar o resultado antes da remoção.

## 3. Delimitar exatamente o que pode sair do Git

Copiar para o diário privado a lista de arquivos do `MANIFESTO.json` da revisão efetivamente conferida. Comparar a lista e seus hashes com os arquivos versionados; mudanças posteriores ou não revisadas bloqueiam a limpeza. Não confiar em um manifesto reescrito por uma saída de modelo.

A lista autorizada contém somente os caminhos de Markdown desse manifesto sob `docs/aprendizado-local/`, mais estes três arquivos de controle na mesma pasta:

- `MANIFESTO.json`;
- `SHA256SUMS.txt`;
- `VALIDACAO_DOCUMENTAL.json`.

Os sete caminhos de `conhecimento/` serão **movidos**, não perdidos. Qualquer arquivo adicional, não rastreado, modificado por outra pessoa ou fora desta lista deve permanecer intacto. Resolva caminhos, confira a raiz Git e rejeite links/junctions; nunca ampliar a lista por curingas.

Não usar `git clean`, `reset --hard`, force-push, remoção recursiva da raiz, `Remove-Item -Recurse` genérico ou exclusão de branches. Não apagar `knowledge/`, `src/`, `tests/`, os dados de `LOCALAI_HOME` nem `AGENTS.md`.

## 4. Efetuar a limpeza de forma recuperável

Trabalhar na branch autorizada, preservando alterações humanas. Primeiro registrar um commit de conclusão com o conhecimento durável e um resumo sanitizado em `docs/APRENDIZADO_LOCAL_CONCLUIDO.md`; criar esse relatório somente agora, com resultado real, revisão validada, critérios atendidos, limites e referência à auditoria privada sem expor seu conteúdo.

Depois preparar **um commit separado de limpeza**: para cada caminho explicitamente autorizado, usar `git rm -- CAMINHO_EXATO` ou a operação Git equivalente. Usar `git mv -- ORIGEM_EXATA DESTINO_EXATO` para as notas ainda não movidas; não construir remoções a partir de texto gerado sem conferência. Guardar o inventário no diário privado para poder terminar mesmo após retirar este próprio arquivo.

No `AGENTS.md`, remover somente o bloco entre os marcadores `LOCALAUTHOR_APRENDIZADO_LOCAL:BEGIN` e `LOCALAUTHOR_APRENDIZADO_LOCAL:END`, inclusive os marcadores. Preservar todas as demais instruções. Corrigir links que apontavam para o pacote, direcionando-os ao relatório e aos documentos duráveis, sem alterar documentação não relacionada.

## 5. Conferir novamente e publicar

Executar a suíte real indicada pelo `AGENTS.md`, verificar links, revisar `git diff --cached --name-status` e comprovar que só os roteiros listados foram retirados, as notas permanecem no destino e nenhum dado privado foi incluído. Repetir consultas/recarga de sanidade sem depender da pasta removida. Falha em testes ou perda de fontes bloqueia a publicação da limpeza.

Fazer commit/push sem force na branch de trabalho; seguir o fluxo de PR/merge autorizado. Conferir SHA remoto, CI da revisão e presença das notas e do relatório no destino. Só então registrar `CLEAN-02 = CONCLUIDO` na cópia privada do estado.

Se o envio falhar, registrar `LIMPEZA_LOCAL_PENDENTE_DE_PUBLICACAO`, conservar evidências e repetir somente a etapa de publicação, não o treinamento. Se outra pessoa alterou o pacote, reconciliar antes de remover. Retirar arquivos da branch não apaga o histórico Git; o commit anterior permite recuperação.

**Resultado esperado: roteiros temporários removidos depois do aceite; conhecimento, modelos, código, testes e evidências preservados.** Este documento não agenda tarefas nem executa exclusão sozinho: precisa ser seguido pelo executor local autorizado.
