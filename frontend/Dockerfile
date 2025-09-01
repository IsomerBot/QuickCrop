# ---- deps (full) ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# ---- build ----
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
RUN npm run build

# ---- prod-deps (only production) ----
FROM node:22-alpine AS proddeps
WORKDIR /app
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev

# ---- run ----
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
# Only production node_modules
COPY --from=proddeps /app/node_modules ./node_modules
# Needed runtime files
COPY frontend/next.config.js ./next.config.js
COPY frontend/public ./public
COPY frontend/package*.json ./
# Built app
COPY --from=build /app/.next ./.next

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://127.0.0.1:3000 || exit 1

CMD ["npm","run","start","--","-p","3000"]