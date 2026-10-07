FROM mcr.microsoft.com/dotnet/aspnet:10.0
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY artifacts/api/ ./
USER 10001:10001
ENTRYPOINT ["dotnet", "Orbit.Api.dll"]
