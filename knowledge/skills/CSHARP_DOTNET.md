---
id: csharp-dotnet-procedimento
version: 1
training_allowed: false
---
# Investigar e propor alterações em C#/.NET

Identifique solução, projetos, target frameworks, arquitetura de processo, bibliotecas, SDK e ambiente de execução antes de recomendar APIs. Não trate .NET Framework/WebForms e ASP.NET Core como intercambiáveis. Preserve nomes de propriedades/rotas, serialização e contratos públicos.

Para uma API, relacione endpoint, DTO, validação, serviço, persistência e testes. Examine ordem de middleware, tratamento de erros, cancelamento, transações e autorização quando pertinentes. Não assuma que um 401 tem uma causa específica sem evidência.

Em acesso a dados, mantenha consultas parametrizadas e verifique semântica de nulidade, ordenação, paginação, concorrência e índices. Em operações assíncronas, propague CancellationToken quando o contrato permitir; não troque sem análise todo trecho síncrono.

Proponha regressão focada que falhe no comportamento antigo. Declare comandos de build/test apenas como instruções quando não houver execução real. Não invente suporte Roslyn: o analisador semântico só existe quando integrado e testado.
