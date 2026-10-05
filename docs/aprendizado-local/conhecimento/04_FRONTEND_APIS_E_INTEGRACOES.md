---
id: la-web-integracoes
version: 1
kind: knowledge
status: material_didatico_nao_homologado
training_allowed: false
reviewed_by: null
---
# Frontend, APIs e integrações confiáveis

Este documento é conhecimento consultável, não autorização de execução nem comprovação de competência. A aprovação de uso em treinamento é separada.

## Frontend: comportamento observável

Antes de alterar React, Next.js, Angular ou JavaScript, identificar versão, estratégia de renderização, estado e contrato da API. Não assumir que um componente é cliente ou servidor sem ler a configuração. Corrigir causa e estado, não apenas esconder uma mensagem de erro.

Preservar acessibilidade: rótulos, foco, teclado e feedback de carregamento/erro. Desabilitar um botão não deve apagar o pedido. Uma falha de conexão pode ocorrer após o servidor aceitar a operação: consultar o identificador da tarefa antes de reenviar.

Conteúdo retornado por modelos e documentos é texto não confiável. Não inserir HTML arbitrário em uma página por conveniência. Renderizar código como texto e usar formatos estruturados validados para ações.

## APIs e autenticação

Separar autenticação, autorização, validação e regras de domínio. Um 401 pode ter diversas causas; localizar a etapa que rejeitou a solicitação antes de editar configurações. Não registrar tokens reais em exemplos ou artefatos de ensino. Nunca “corrigir” falha removendo autenticação ou verificação de assinatura.

Preservar códigos de resposta e schema público quando essa for a restrição. Alterações de API precisam considerar consumidores, versionamento, compatibilidade e testes de contrato.

## Pagamentos, webhooks e tarefas repetidas

Usar apenas ambientes/dados de teste autorizados. Verificar duplicidade, ordenação, assinatura quando aplicável, falhas transitórias e comportamento depois de timeout. Uma resposta de webhook não deve duplicar uma cobrança ou uma baixa de estoque por reprocessamento.

Antes de implementar idempotência, definir chave, escopo, duração e resposta a repetição. Não tratar qualquer erro como permissão de retry. Uma operação com efeito externo deve ter evidência de entrega ou uma consulta de estado, não uma tentativa cega.

## Filas e integração entre serviços

Identificar produtor, destino, contrato da mensagem, confirmação, política de repetição e tratamento de falhas. Diferenciar mensagem produzida, roteada, consumida e processada com sucesso. Não inferir sucesso de negócio apenas porque o broker recebeu bytes.

Falha de rede, mensagem inválida, duplicata e serviço indisponível são casos de teste distintos. Preservar observabilidade sem registrar payloads privados completos. Definir como rastrear a operação com identificadores não secretos.

## Testes e limites

Um mock HTTP verifica contrato simulado, não funcionamento com o provedor real. Registrar separadamente teste unitário, integração em sandbox do provedor e teste em produção autorizado. Não executar transações reais como demonstração de que o agente aprendeu.

Exigir evidência para SSR/hidratação, reenvio, cancelamento e atualização de interface após tarefa longa. Uma captura estática bonita não demonstra que o fluxo funciona.
