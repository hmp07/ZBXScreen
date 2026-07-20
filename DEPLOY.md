# ZBXScreen 部署手册（v1.3）

---

## 1. 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux（x86_64 或 aarch64/ARM64） |
| Docker | ≥ 20.10 |
| Docker Compose | ≥ 2.0 |
| 内存 | ≥ 512 MB |
| 磁盘 | ≥ 2 GB |

---

## 2. 部署文件

```
/opt/zbxscreen/
├── docker-compose.yml
├── .env
└── zabbixscreen-v1.3.tar.gz    # Docker 镜像（离线部署）
```

---

## 3. 导入镜像（离线部署）

```bash
cd /opt/zbxscreen
docker load < zabbixscreen-v1.3.tar.gz
docker images | grep zabbixscreen
```

---

## 4. 配置 .env

```bash
vi .env
```

**必填**：
```ini
APP_SECRET_KEY=<openssl rand -base64 32 生成>
```

**可选**：
```ini
ZBX_PORT=8088
TZ=Asia/Shanghai
DEFAULT_ADMIN_PASSWORD=Admin@123
```

---

## 5. 启动

```bash
mkdir -p data logs
chmod 777 data logs
docker compose up -d
docker compose logs -f
```

---

## 6. 初始配置

1. 访问 `http://<IP>:8088`，用 admin / Admin@123 登录
2. 进入 **系统设置 → 数据源 → Zabbix 数据源**，添加 Zabbix 连接
3. 切换到 **运维集成** tab，配置运维管理系统（iTop）地址和凭据
4. `docker compose restart` 使集成代理生效
5. 配置 Zabbix 服务器 HTTP 认证（Administration → Authentication → HTTP），实现自动登录

---

## 7. 升级（v1.2 → v1.3）

```bash
# 备份
cp ./data/zabbixscreen.db ./data/zabbixscreen.db.bak

# 数据库迁移（幂等）
sqlite3 ./data/zabbixscreen.db "ALTER TABLE alert_records ADD COLUMN datasource_id INTEGER;" 2>/dev/null || true

# 更新代码
git pull origin master

# 重建
docker compose up --build -d
```

---

## 8. 常用命令

```bash
docker compose ps          # 状态
docker compose logs -f     # 日志
docker compose restart     # 重启
docker compose down        # 停止
```

## 9. 备份恢复

```bash
cp ./data/zabbixscreen.db ./backup/zabbixscreen-$(date +%Y%m%d).db
```

## 10. 故障排查

| 现象 | 排查 |
|------|------|
| 容器无法启动 | `docker compose logs`；检查 .env 中 APP_SECRET_KEY 不为默认值 |
| 无数据 | 确认数据源已配置；`docker compose logs \| grep AGGREGATOR` |
| 运维工具空白页 | `docker compose restart` 重新生成代理配置 |

---

*手册版本：v1.3 | 适用 ZBXScreen v1.3+*
