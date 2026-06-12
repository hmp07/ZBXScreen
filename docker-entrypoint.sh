#!/bin/bash
set -e

echo "============================================"
echo "  ZBXScreen - Starting..."
echo "  Platform: $(uname -m)"
echo "  Date:     $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# ── 设置数据目录（database.py 通过 ZBX_DATA_DIR 环境变量读取）──
export ZBX_DATA_DIR=/app/data
mkdir -p /app/data /app/logs

# ── 首次运行：初始化数据库 ──
if [ ! -f /app/data/zabbixscreen.db ]; then
    echo "[entrypoint] First run — initializing database..."
    python /app/scripts/init_db.py
    echo "[entrypoint] Database initialized."
else
    echo "[entrypoint] Database exists, skipping init."
fi

# ── 确保应用日志目录可写（uvicorn / nginx / scheduler 日志）──
touch /app/logs/.write_test 2>/dev/null && rm -f /app/logs/.write_test || {
    echo "[entrypoint] WARNING: Cannot write to /app/logs/. Host directory permissions may be incorrect."
    echo "[entrypoint] Run on host: chmod 777 \$(pwd)/logs"
}

echo "[entrypoint] Starting services via supervisord..."
echo "  - Nginx     :80  (static + reverse proxy)"
echo "  - uvicorn   :5001 (FastAPI, internal)"
echo "  - scheduler :     (data aggregation)"
echo "============================================"

exec "$@"
