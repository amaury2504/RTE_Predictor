# Frontend RTE Predictor : construction avec Node, puis service des fichiers statiques et proxy de /api avec Caddy.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# L'API est appelée sur le même domaine, sous /api (voir Caddyfile) : aucun CORS à gérer
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
