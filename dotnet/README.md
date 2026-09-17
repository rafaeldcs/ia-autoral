# Host .NET 10 opcional — não compilado nesta sessão

Esta camada ASP.NET Core serve a mesma interface e encaminha chamadas exclusivamente
para o núcleo de referência em `127.0.0.1:8765`. Não contém outro modelo e não usa APIs externas.
É uma integração local real, mas não é a migração completa de memória/agente para C#.

1. Inicie o núcleo Python (`scripts/start.ps1`).
2. No diretório `dotnet`, execute `dotnet build LocalAI.Host/LocalAI.Host.csproj -c Release`.
3. Execute `dotnet run --project LocalAI.Host --no-build -c Release`.
4. Abra `http://127.0.0.1:5080` e use o mesmo token local.

O SDK .NET não estava disponível no ambiente de implementação e a tentativa de obtê-lo
falhou por indisponibilidade de rede. Por isso, **não há evidência de compilação ou execução
C# nesta entrega**. O workflow inclui um job para compilar esta camada após a publicação.
Nenhum workflow GitHub foi executado nesta conversa.
