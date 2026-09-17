# Host .NET 10 opcional — validado no notebook

Esta camada ASP.NET Core serve a mesma interface e encaminha chamadas exclusivamente
para o núcleo de referência em `127.0.0.1:8765`. Não contém outro modelo e não usa APIs externas.
É uma integração local real, mas não é a migração completa de memória/agente para C#.

1. Inicie o núcleo Python (`scripts/start.ps1`).
2. No diretório `dotnet`, execute `dotnet build LocalAI.Host/LocalAI.Host.csproj -c Release`.
3. Execute `dotnet run --project LocalAI.Host --no-build -c Release`.
4. Abra `http://127.0.0.1:5080` e use o mesmo token local.

Em 17/09/2026, esta camada e o laboratório foram compilados no notebook com SDK
10.0.301, sem avisos/erros. `scripts/dotnet-smoke.py` executou onze verificações reais
de autenticação, origem, proxy JSON, consulta e erro quando o backend fica indisponível.
Evidência: `reports/dotnet-smoke-windows.json` e `docs/PROGRESS_WINDOWS.md`.

Depois do build, execute na raiz `.venv\Scripts\python.exe scripts/dotnet-smoke.py`.
O teste cria backend e dados temporários, exige porta 5080 livre e encerra apenas o host
que ele próprio iniciou. O núcleo continua Python; isso não conclui a migração C#.
O workflow atualizado inclui Windows/Linux e ainda aguarda publicação/execução remota.
