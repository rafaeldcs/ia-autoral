FROM localauthor-testing-lab:1
USER root
RUN apt-get update && apt-get install -y --no-install-recommends postgresql python3-numpy && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --no-create-home lab
COPY backend /build/backend
RUN dotnet publish /build/backend/Orbit.Api.csproj -c Release -o /opt/orbit-api
COPY frontend/package.json frontend/package-lock.json /opt/orbit-web/
WORKDIR /opt/orbit-web
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend /opt/orbit-web
ENV NEXT_TELEMETRY_DISABLED=1 ORBIT_API_PORT=5088 ORBIT_WEB_PORT=3100
RUN npm run build
COPY lab /opt/functional-lab
RUN chmod -R a+rX /opt/orbit-api /opt/functional-lab
USER 10001:10001
ENV HOME=/tmp
WORKDIR /tmp
ENTRYPOINT ["python3","/opt/functional-lab/run.py"]
