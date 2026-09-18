# Stage 1: Build React app
FROM docker.m.daocloud.io/library/node:22-alpine AS builder

RUN npm config set registry https://registry.npmmirror.com

ARG APP_VERSION
ARG GIT_COMMIT
ARG VITE_TURNSTILE_SITE_KEY

ENV VITE_APP_VERSION=${APP_VERSION}
ENV VITE_GIT_COMMIT=${GIT_COMMIT}
ENV VITE_TURNSTILE_SITE_KEY=${VITE_TURNSTILE_SITE_KEY}

WORKDIR /app
COPY package*.json .npmrc ./
# 安装加固：提高并发连接数与重试次数，避免 registry 超时触发 npm "Exit handler never called!" 崩溃
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set maxsockets 128 \
    && npm install
COPY . .
RUN npm run build

# Stage 2: Serve with nginx (极轻量，仅 64m mem_limit)
FROM docker.m.daocloud.io/library/nginx:alpine

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80 443
