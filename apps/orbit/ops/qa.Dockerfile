FROM node:22-bookworm-slim AS node
FROM mcr.microsoft.com/dotnet/sdk:10.0
COPY --from=node /usr/local/ /usr/local/
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=true NEXT_TELEMETRY_DISABLED=1 NUGET_PACKAGES=/opt/packages HOME=/tmp PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN apt-get update && apt-get install -y --no-install-recommends git python3 postgresql ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin orbitqa
WORKDIR /opt/orbit-web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-fund --no-audit
WORKDIR /opt/qa
COPY backend/Orbit.Api.csproj /opt/api/Orbit.Api.csproj
COPY qa/Orbit.Testing.Reference/Orbit.Testing.Reference.csproj /opt/unit/Orbit.Testing.Reference.csproj
RUN dotnet restore /opt/api/Orbit.Api.csproj && dotnet restore /opt/unit/Orbit.Testing.Reference.csproj
RUN npm install --ignore-scripts --no-fund --no-audit @playwright/test@1.55.0 && npx playwright install --with-deps chromium
RUN chmod -R a+rX /opt
WORKDIR /tmp
