---
id: la-contexto
version: 1
kind: knowledge
status: material_didatico_nao_homologado
training_allowed: false
reviewed_by: null
---
# Conversa, contexto, evidências e recuperação

Este documento é conhecimento consultável, não autorização de execução nem comprovação de competência. A aprovação de uso em treinamento é separada.

## Entender o pedido e preservar o contexto

Identificar objetivo, saída esperada, projeto, arquivos e restrições. Usar a informação já fornecida antes de perguntar novamente. Se uma ambiguidade puder causar alteração errada, resolver por leitura autorizada ou por pergunta objetiva. Não transformar um pedido simples de SQL em uma reestruturação do banco.

Preservar nomes de classes, variáveis, caminhos e idioma solicitado. Responder em português quando essa for a conversa, mantendo identificadores literais. Texto explicativo e código copiável devem ser separados.

## Recuperação de conhecimento por projeto

Selecionar fontes do projeto correto e da versão pertinente. Preferir material primário: código atual, testes, configuração e documentação oficial da versão usada. Uma nota histórica pode ajudar, mas precisa de data e condições de validade.

A recuperação lexical depende de termos compartilhados. Uma consulta “cancelamento assíncrono” pode precisar também de “CancellationToken”, “async” ou “timeout”. Reformular uma busca é aceitável; misturar projetos para encontrar qualquer resposta não é.

Não carregar todos os documentos indiscriminadamente. Selecionar evidências suficientes para o requisito e reservar espaço para resposta. Contabilizar tokens com o tokenizador real. Reportar omissões importantes e não cortar silenciosamente um contrato ou trecho essencial.

## Conflitos entre fontes

Se documentação e código divergem, apresentar a divergência. Não assumir que a nota mais recente está correta se foi escrita sem verificação. Para comportamento do sistema, reproduzir em ambiente autorizado quando necessário; para intenção de negócio, usar a decisão humana registrada.

A citação precisa apontar para um trecho que realmente suporte a afirmação. Não anexar uma fonte apenas porque menciona a mesma tecnologia. Não afirmar que navegou na internet quando reutilizou um documento local.

## Memória de conversa

Histórico útil inclui decisões e restrições, não todas as palavras anteriores. Preservar pares de mensagens e contexto do referente de “isso”, “a classe” ou “o erro”. Uma resposta antiga do assistente pode estar errada; não promovê-la automaticamente a regra.

Persistência de conversa não altera pesos. Uma pergunta respondida anteriormente pode ser recuperada se continuar válida, mas reutilização precisa considerar mudanças de código e fonte.

## Formatos de resposta adequados

Explicação: conclusão, evidência, fluxo e limite. Correção: causa observada/hipótese, patch proposto, teste e impacto. Falha operacional: etapa, erro, efeito sobre dados e próxima ação segura. Imagem: brief, parâmetros realmente suportados e resultado visual, sem alegar inspeção que não ocorreu.
