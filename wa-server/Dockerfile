# ── Build stage ─────────────────────────────────────────────────────
FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./
RUN npm ci --production

# ── Runtime stage ────────────────────────────────────────────────────
FROM node:20-slim

# Solo libatomic1 es necesaria en runtime (algunas deps la usan)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY server.js ./

# Limitar heap de Node para evitar OOM kill en Railway (512 MB container)
ENV NODE_OPTIONS="--max-old-space-size=384"
ENV NODE_ENV=production

EXPOSE 8080

CMD ["node", "server.js"]
