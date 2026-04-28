FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --production --no-audit --no-fund

COPY server.js ./

ENV NODE_OPTIONS="--max-old-space-size=384"
ENV NODE_ENV=production

EXPOSE 8080

CMD ["node", "server.js"]
