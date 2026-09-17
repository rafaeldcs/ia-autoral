# Escrita e preservação de código — 17/09/2026

Esta entrega separa proteção do texto no aplicativo e capacidade de escrita do modelo. As proteções passaram nos testes em servidor temporário; o novo candidato neural não foi aprovado. **A ativação das mudanças de backend na instância da porta 8765 exige reinício, que ficou pendente após rejeição automática do comando pela política de execução.** O processo existente foi preservado.

## Editor e armazenamento

O seletor **Entrada → Código** usa fonte monoespaçada e desliga correção ortográfica/autocapitalização. Tabulações, espaços, aspas, barras, comentários, acentos, emojis e quebras de linha são enviados como conteúdo JSON e armazenados sem aplicar formatação ou escape adicional. HTML e sequências como `</textarea><script>` são exibidos como texto. **Copiar mensagem** copia o conteúdo armazenado, sem rótulos e avisos da interface.

Foi removido o corte automático do atributo `maxlength`. Ao exceder 8.000 caracteres, o envio é recusado e o conteúdo permanece no editor. O modo neural informa seu limite de 180 bytes, diferente da contagem de caracteres com acentos. A API atualizada rejeita conteúdo excessivo ou Unicode inválido sem salvar parte da mensagem. Títulos derivados usam caracteres Unicode completos, sem cortar um emoji ao meio. Ctrl+Enter envia; Enter mantém uma nova linha. O atalho não envia durante composição de caracteres.

Limite conhecido: navegador e clipboard podem normalizar quebras CRLF para LF ou vice-versa. Não se promete preservação byte a byte de um arquivo pelo clipboard. A API/SQLite preservaram CRLF recebido diretamente; o teste de navegador comparou exatamente a string fornecida pelo campo. Acentos e marcas combinantes não são normalizados pelo aplicativo.

## Saída do modelo

Foi removida a substituição silenciosa de bytes inválidos por `�` no backend atualizado. Uma geração UTF-8 inválida falha explicitamente e não salva metade da troca. Ao atingir 120 tokens, a resposta recebe aviso de possível truncamento. Isso não valida gramática nem garante compilação. Nenhum código do chat é executado automaticamente.

Os guias incluem escrita clara, concordância, preservação de identificadores/strings/comentários, alteração somente do trecho solicitado e escape conforme o destino. C#, JSON e atributos HTML têm regras diferentes. Esses guias determinísticos são identificados como tal; não são prova de aprendizado neural.

## Ensino real e resultado

144 exercícios sintéticos novos em doze temas: concordância, acentuação, clareza, incerteza sobre testes, esclarecimento de pedidos, aspas JSON, caminhos JSON, atributo HTML, string C#, delimitador de comentário, comentários em múltiplas linhas e literal JavaScript. O treino revisitou 1.002 exemplos anteriores. Não foram usados dados das conversas nem pesos externos.

O verificador de corpus rejeitou uma proposta com frases quase idênticas entre partições. As partições foram refeitas com instruções reformuladas, sem relaxar o verificador. São doze tarefas conhecidas com dois identificadores por instrução, não 24 famílias independentes.

Após 2.000 passos, as validações continuaram em 0/24. Pela regra de seleção por acerto exato, o primeiro checkpoint empatado, aos 500 passos, ficou selecionado. Seu teste final foi **0/24**; a regressão de gerações anteriores foi **45/68**, sem reexecução dos programas. O candidato permanece com `chatEnabled=false` e não substituiu o candidato anterior de engenharia. Não há alegação de domínio geral da escrita.

Em diagnósticos, bytes inválidos podem aparecer como substituições marcadas por `validUtf8=false`; não são uma resposta corrigida no chat. Checkpoint e seed permitem reproduzir a geração.

Evidências privadas sob `%LOCALAPPDATA%\LocalAuthor`:

- `exports\communication-report.json` e `exports\communication-20260917T175115Z\report.json`.
- `models\communication-20260917T175115Z\best-validation.npz`, com hash de integridade.
- `corpus\communication-20260917T175115Z\manifest.json`.

Script: `C:\Users\rafae\OneDrive\Desktop\jira-local-experimental\scripts\train-communication.py`. Nenhuma nova dependência ou arquitetura neural. Próximo desafio: instruções de treino mais diversas e seleção que considere qualidade de geração e regressões, com outra avaliação independente. Baixa perda de treino não comprova capacidade.

## Validação

**152 testes locais:** 149 aprovações e 3 testes de symlink indisponíveis por privilégio do Windows. **19 verificações em Edge:** geração real com o candidato anterior, isolamento, histórico, cópia, acentos, código literal, colagem longa, mobile e ausência de exceções JavaScript. O fechamento do navegador produziu reset de conexão HTTP no servidor temporário, sem falha das verificações.

Relatórios: `reports/writing-tests.json` e `reports/chat-smoke.json`. Captura: `reports/writing-code.png`. Os testes usaram projetos e dados temporários. A porta 8765 continua com o processo anterior até que o serviço seja reiniciado; testes temporários não foram apresentados como ativação do backend de uso diário.
