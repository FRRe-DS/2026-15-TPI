# syntax=docker/dockerfile:1

# Misma major de Node que frontend/.nvmrc y el CI.
FROM node:24-alpine AS construccion

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build \
    && npm prune --omit=dev

FROM node:24-alpine

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY --from=construccion --chown=node:node /app/package.json ./
COPY --from=construccion --chown=node:node /app/node_modules ./node_modules
COPY --from=construccion --chown=node:node /app/.next ./.next

USER node

EXPOSE 3000

# Las variables API_URL, KEYCLOAK_* y TEST_* se leen en el servidor en cada
# request (la página es force-dynamic), por lo que se inyectan desde Compose.
CMD ["npx", "next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
