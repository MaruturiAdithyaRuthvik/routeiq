FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_USE_FIXTURES=false
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} VITE_USE_FIXTURES=${VITE_USE_FIXTURES}
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
