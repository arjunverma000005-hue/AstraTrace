# Multi-stage Node 22 / Nginx Dockerfile for AstraTrace Frontend
FROM node:22-alpine AS builder

WORKDIR /build

COPY apps/frontend/package.json ./
RUN npm install

COPY apps/frontend/ ./
RUN npm run build

# Runner Stage: Nginx Alpine
FROM nginx:alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

# Expose standard frontend port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
