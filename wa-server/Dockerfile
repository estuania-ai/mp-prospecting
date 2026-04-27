FROM node:20-slim

# Dependencias de sistema para Baileys (criptografía nativa)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (capa de caché)
COPY package*.json ./
RUN npm ci --production

# Copiar código
COPY server.js ./

# Railway inyecta $PORT; el código usa process.env.PORT
ENV NODE_ENV=production

# Auth_info se monta como volumen en /data — NO en /app
# El código usa AUTH_DIR=/data si WA_AUTH_DIR está seteado

EXPOSE 8080

CMD ["node", "server.js"]
