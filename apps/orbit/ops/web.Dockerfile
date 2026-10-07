FROM node:22-bookworm-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY artifacts/web/ ./
USER 10001:10001
CMD ["node", "server.js"]
