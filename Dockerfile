# syntax=docker/dockerfile:1

# =====================================================================
# ZBXScreen 多架构 Dockerfile
# 支持: linux/amd64, linux/arm64
# 构建: docker buildx build --platform linux/amd64,linux/arm64 -t zabbixscreen .
# =====================================================================

# ── 阶段 1: 前端构建 ──────────────────────────────────────────
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# 利用 Docker 层缓存：先装依赖，再复制源码
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent 2>/dev/null || npm install

COPY frontend/ ./
RUN npm run build


# ── 阶段 2: 后端运行环境 ─────────────────────────────────────
FROM python:3.11-slim

LABEL org.opencontainers.image.title="ZBXScreen"
LABEL org.opencontainers.image.description="Zabbix monitoring visualization platform"
LABEL org.opencontainers.image.vendor="ZBXScreen"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
ENV ZBX_DATA_DIR=/app/data

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    # 清理默认 nginx 配置
    rm -f /etc/nginx/sites-enabled/default && \
    # 创建运行时目录
    mkdir -p /app/data /app/logs && \
    mkdir -p /var/log/nginx /var/log/supervisor && \
    mkdir -p /var/run/nginx /var/run/supervisor

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物到 Nginx 静态目录
COPY --from=frontend-build /app/frontend/dist /app/static

# 复制 Nginx 配置
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf

# 复制 supervisor 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制数据库初始化脚本
COPY scripts/init_db.py /app/scripts/init_db.py

# 复制容器入口脚本
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 创建应用用户并设置权限
RUN useradd -m -u 1000 appuser 2>/dev/null || true && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /var/log/supervisor && \
    chown -R appuser:appuser /var/run/nginx && \
    chown -R appuser:appuser /var/run/supervisor && \
    chown -R appuser:appuser /var/lib/nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost/api/v1/health || exit 1

USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
