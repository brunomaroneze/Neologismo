# --- Estágio 1: dependências ------------------------------------------------
FROM node:22-alpine AS dependencias
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


# --- Estágio 2: build -------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

COPY --from=dependencias /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* é embutido no bundle no momento do build, não lido em runtime:
# precisa chegar aqui como build-arg, senão o site aponta para localhost.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# --- Estágio 3: runtime -----------------------------------------------------
FROM node:22-alpine AS final
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# `output: standalone` monta em .next/standalone um servidor com apenas as
# dependências realmente usadas — a imagem final não leva node_modules inteiro.
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
