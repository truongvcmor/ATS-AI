FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Baked in as a placeholder; docker-entrypoint.sh substitutes the real runtime
# VITE_API_URL value into the built JS at container start (see that file for why).
ENV VITE_API_URL=__RUNTIME_API_URL__
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && chown -R node:node /app

# node:alpine ships a non-root "node" user (uid 1000) out of the box.
USER node

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:5173/ || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
