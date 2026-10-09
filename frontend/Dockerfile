# frontend/Dockerfile — multi-stage Vite build + nginx (Phase 12, Lesson 12.2)

FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
# VITE_API_BASE_URL is same-origin /api — nginx proxies to backend.
RUN npm run build


FROM nginx:1.27-alpine AS runtime

# Remove default site, install SPA + proxy config
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/spetser.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
