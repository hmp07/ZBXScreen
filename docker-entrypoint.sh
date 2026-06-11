#!/bin/bash
set -e

echo "============================================"
echo "  ZBXScreen - Starting..."
echo "  Platform: $(uname -m)"
echo "  Date:     $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# ── 首次运行：初始化数据库 ──
if [ ! -f /app/data/zabbixscreen.db ]; then
    echo "[entrypoint] First run — initializing database..."
    python /app/scripts/init_db.py
    echo "[entrypoint] Database initialized."
else
    echo "[entrypoint] Database exists, skipping init."
fi

# ── 确保日志目录权限 ──
touch /app/logs/supervisord.log 2>/dev/null || true

echo "[entrypoint] Starting services via supervisord..."
echo "  - Nginx     :80  (static + reverse proxy)"
echo "  - uvicorn   :5001 (FastAPI, internal)"
echo "  - scheduler :     (data aggregation)"
echo "============================================"

exec "$@"
