# ── 前端 Dockerfile（多阶段构建）────────────────────────────────
# Stage 1: 构建 React 静态资源
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent

COPY . .
RUN npm run build

# Stage 2: 用 nginx 托管静态文件，并反向代理 /api 到后端
FROM nginx:1.27-alpine

# 复制构建产物
COPY --from=builder /app/build /usr/share/nginx/html

# 复制 nginx 路由配置（SPA fallback + API 代理）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
