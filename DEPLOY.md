# ZBXScreen 容器化部署指南

## 系统要求

### 宿主机环境

| 项目 | 最低要求 |
|------|----------|
| 操作系统 | Linux (x86_64 / ARM64) |
| Docker | ≥ 20.10 |
| Docker Compose | ≥ 2.0（或 `docker compose` 插件） |
| 内存 | ≥ 512 MB |
| 磁盘 | ≥ 1 GB（含镜像和数据） |

### 平台支持

| 平台 | 架构 | 适用硬件 |
|------|------|----------|
| `linux/amd64` | x86_64 | Intel Xeon, AMD EPYC, 通用 PC 服务器 |
| `linux/arm64` | ARM64 / aarch64 | 华为鲲鹏 (Kunpeng 920), 飞腾 (Phytium), 树莓派 4B+, Apple M 系列 |

---

## 部署步骤

### 步骤 1：准备项目文件

```bash
# 克隆项目
git clone https://github.com/hmp07/ZBXScreen.git
cd ZBXScreen
```

### 步骤 2：配置环境变量

```bash
# 从模板创建 .env 文件
cp .env.example .env

# 编辑配置（务必修改 APP_SECRET_KEY）
vi .env
```

**必须修改的配置项：**

```ini
# 生成一个随机密钥（至少 32 字符）
APP_SECRET_KEY=替换为随机字符串

# 生产环境关闭调试模式
DEBUG=false

# 首次登录后建议修改
DEFAULT_ADMIN_PASSWORD=Admin@123
```

> 可用 `openssl rand -base64 32` 生成随机 APP_SECRET_KEY

### 步骤 3：构建 Docker 镜像

#### 单平台构建（快速本地测试）

```bash
# 构建当前平台镜像
docker build -t zabbixscreen:latest .
```

#### 多平台构建（生产发布）

```bash
# 1. 创建多架构构建器（仅首次需要）
docker buildx create --name multiarch-builder --use
docker buildx inspect --bootstrap

# 2. 构建并推送到镜像仓库（替换为你的仓库地址）
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag your-registry/zabbixscreen:latest \
  --push .

# 3. 仅构建到本地（不推送，仅当前平台）
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag zabbixscreen:latest \
  --load .
```

> **注意：** `--load` 仅支持单平台。如需本地测试多平台，建议按上述方式分别构建。

#### ARM64 平台单独构建（鲲鹏/飞腾服务器）

```bash
# 在 ARM64 服务器上直接构建
docker build -t zabbixscreen:latest .
```

### 步骤 4：创建数据目录

```bash
# 创建持久化数据目录
mkdir -p data logs

# 确保目录可写
chmod 755 data logs
```

### 步骤 5：启动服务

```bash
# 生产模式启动
docker compose up -d

# 查看日志
docker compose logs -f

# 查看容器状态
docker compose ps

# 停止服务
docker compose down
```

### 步骤 6：验证部署

```bash
# 检查健康状态
curl http://localhost:8088/api/v1/health
# 预期输出: {"code":0,"message":"success","data":{"status":"healthy"}}

# 浏览器访问
# http://<服务器IP>:8088
# 默认用户名: admin
# 默认密码: Admin@123
```

---

## 镜像传输（离线部署）

如果构建机器与部署服务器网络隔离，可使用以下方式传输镜像：

```bash
# === 在构建机器上 ===

# 导出为 tar 文件
docker save zabbixscreen:latest | gzip > zabbixscreen-latest.tar.gz

# 传输到目标服务器
scp zabbixscreen-latest.tar.gz user@target-server:/tmp/

# === 在目标服务器上 ===

# 导入镜像
docker load < /tmp/zabbixscreen-latest.tar.gz

# 启动服务
cd /path/to/ZBXScreen
docker compose up -d
```

---

## 容器架构

```
┌─────────────────────────────────────────┐
│              Docker Container           │
│                                         │
│  ┌──────────┐    ┌──────────────────┐  │
│  │  Nginx   │───▶│  uvicorn:5001    │  │
│  │  :80     │    │  (FastAPI)        │  │
│  │  静态文件 │    └──────────────────┘  │
│  │  + /api  │                           │
│  │  反向代理 │    ┌──────────────────┐  │
│  └──────────┘    │  scheduler        │  │
│                  │  (APScheduler)    │  │
│                  │  数据聚合+告警检测  │  │
│                  └──────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  SQLite (WAL 模式)               │  │
│  │  /app/data/zabbixscreen.db      │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘

进程管理: Supervisor (管理 Nginx + uvicorn + scheduler)
```

---

## 环境变量完整参考

| 变量 | 必填 | 默认值 | 说明 |
|------|:--:|--------|------|
| `APP_SECRET_KEY` | **是** | — | JWT 签名 + AES 加密密钥 |
| `TZ` | 否 | `Asia/Shanghai` | 时区 |
| `DEBUG` | 否 | `false` | FastAPI 调试模式 |
| `DEFAULT_ADMIN_PASSWORD` | 否 | `Admin@123` | 初始管理员密码 |
| `DEFAULT_REFRESH_INTERVAL` | 否 | `30` | 数据刷新间隔（秒） |
| `ALERT_CHECK_INTERVAL` | 否 | `60` | 告警检测间隔（秒） |
| `DATA_RETENTION_DAYS` | 否 | `30` | 数据保留天数 |
| `ZABBIX_REQUEST_TIMEOUT` | 否 | `25` | Zabbix API 超时（秒） |
| `AGGREGATION_TOTAL_TIMEOUT` | 否 | `28` | 数据聚合总超时（秒） |
| `WEBHOOK_REQUEST_TIMEOUT` | 否 | `10` | Webhook 发送超时（秒） |
| `ZBX_PORT` | 否 | `8088` | 宿主机映射端口 |

---

## 数据持久化

| 宿主机目录 | 容器内路径 | 内容 |
|------------|-----------|------|
| `./data/` | `/app/data/` | SQLite 数据库文件 |
| `./logs/` | `/app/logs/` | Supervisor 日志、Nginx 日志、应用日志 |

> 升级容器或重建时，保留这两个目录即可保留所有数据。

---

## 常用运维命令

```bash
# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f zabbixscreen

# 查看最近 100 行日志
docker compose logs --tail=100

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 停止并删除数据卷（会丢失数据！）
docker compose down -v

# 进入容器调试
docker exec -it zabbixscreen bash

# 查看容器资源使用
docker stats zabbixscreen

# 更新镜像后重新部署
docker compose down
docker build -t zabbixscreen:latest .
docker compose up -d
```

---

## 故障排查

### 容器无法启动

```bash
# 查看日志
docker compose logs zabbixscreen

# 常见原因:
# 1. 端口冲突: 修改 ZBX_PORT
# 2. 权限问题: 确保 data/ logs/ 目录可写
# 3. APP_SECRET_KEY 未设置
```

### 数据库损坏

```bash
# 备份当前数据库
cp data/zabbixscreen.db data/zabbixscreen.db.bak

# 重建容器（会创建新数据库）
docker compose down
rm -f data/zabbixscreen.db*
docker compose up -d
```

### ARM64 平台兼容性

```bash
# 如果镜像不支持 ARM64，在目标服务器上本地构建:
docker build -t zabbixscreen:latest .
docker compose up -d
```

### Nginx 502 错误

```bash
# uvicorn 未正常启动，查看应用日志
docker exec zabbixscreen cat /app/logs/uvicorn_err.log
```

---

## 安全建议

1. **务必修改 `APP_SECRET_KEY`**：使用随机生成的 64 字符密钥
2. **首次登录后修改管理员密码**：默认密码 `Admin@123`
3. **使用反向代理开启 HTTPS**：生产环境建议在容器前加 Nginx/Caddy 提供 TLS
4. **限制端口暴露**：如果使用外部反向代理，可将端口映射为 `127.0.0.1:8088:80`
5. **定期备份数据库**：`cp data/zabbixscreen.db data/backup-$(date +%Y%m%d).db`
