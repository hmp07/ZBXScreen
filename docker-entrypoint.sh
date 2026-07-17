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

# ── 配置运维集成反代 ──
TEMPLATE="/app/nginx/integrations.conf.template"
OUTPUT="/app/nginx/integrations.conf"
mkdir -p /app/nginx

if [ -f "$TEMPLATE" ]; then
    echo "[entrypoint] Configuring integration proxy..."

    # 从数据源读取 Zabbix 凭据并生成 Basic Auth
    ZABBIX_CREDS=$(python3 -c "
import sqlite3, base64, hashlib, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

db_path = '/app/data/zabbixscreen.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT url, username, password_encrypted FROM datasources WHERE enabled=1 LIMIT 1')
row = cur.fetchone()
if not row:
    sys.exit(0)

zabbix_url, username, encrypted = row[0], row[1], row[2]

import os
key_str = os.environ.get('APP_SECRET_KEY', 'change-this-in-production')
aes_key = hashlib.sha256(key_str.encode()).digest()[:16]
raw = base64.b64decode(encrypted)
iv, ct = raw[:16], raw[16:]
cipher = AES.new(aes_key, AES.MODE_CBC, iv)
password = unpad(cipher.decrypt(ct), AES.block_size).decode()

basic = base64.b64encode(f'{username}:{password}'.encode()).decode()
print(f'ZABBIX_URL={zabbix_url}')
print(f'ZABBIX_BASIC={basic}')
conn.close()
" 2>/dev/null)

    if [ -n "$ZABBIX_CREDS" ]; then
        eval "$ZABBIX_CREDS"
        sed "s|ZABBIX_REAL_HOST|$ZABBIX_URL|g; s|ZABBIX_CREDENTIALS|$ZABBIX_BASIC|g; s|ITOP_REAL_HOST|127.0.0.1|g; s|ITOP_CREDENTIALS|DISABLED|g" "$TEMPLATE" > "$OUTPUT"
        echo "[entrypoint] Zabbix proxy configured: $ZABBIX_URL"
    else
        echo "[entrypoint] No Zabbix datasource found — integration proxy disabled"
        sed 's|ZABBIX_REAL_HOST|http://127.0.0.1|g; s|ZABBIX_CREDENTIALS|DISABLED|g; s|ITOP_REAL_HOST|http://127.0.0.1|g; s|ITOP_CREDENTIALS|DISABLED|g' "$TEMPLATE" > "$OUTPUT"
    fi
fi

echo "[entrypoint] Starting services via supervisord..."
echo "  - Nginx     :80  (static + reverse proxy)"
echo "  - uvicorn   :5001 (FastAPI, internal)"
echo "  - scheduler :     (data aggregation)"
echo "============================================"

exec "$@"
