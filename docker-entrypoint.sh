#!/bin/bash
set -e

echo "[entrypoint] Starting ZabbixScreen..."

# 首次运行：初始化数据库
if [ ! -f /app/data/zabbixscreen.db ]; then
    echo "[entrypoint] First run — initializing database..."
    python /app/scripts/init_db.py
    echo "[entrypoint] Database initialized."
else
    echo "[entrypoint] Database exists, running migrations..."
    cd /app && alembic upgrade head 2>/dev/null || echo "[entrypoint] Migration skipped"
fi

echo "[entrypoint] Starting services via supervisord..."
exec "$@"
