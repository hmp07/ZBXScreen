# ZBXScreen 离线部署手册（v1.1）

---

## 1. 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux（x86_64 或 aarch64/ARM64） |
| Docker | ≥ 20.10 |
| Docker Compose | ≥ 2.0（或 `docker compose` 插件） |
| 内存 | ≥ 512 MB |
| 磁盘 | ≥ 2 GB（镜像约 500MB + 数据空间） |
| 网络 | 容器需能访问 Zabbix Server API |

---

## 2. 准备部署文件

将以下 3 个文件放到目标服务器的同一目录（如 `/opt/zbxscreen`）：

```
/opt/zbxscreen/
├── docker-compose.yml
├── .env
└── zabbixscreen-v1.1.tar.gz     # 导出的 Docker 镜像
```

> **获取 `docker-compose.yml` 和 `.env`**：从项目仓库下载，或从构建机上复制。

---

## 3. 导入镜像

```bash
cd /opt/zbxscreen

# 导入镜像
docker load < zabbixscreen-v1.1.tar.gz

# 确认导入成功
docker images | grep zabbixscreen
# 输出: zabbixscreen   v1.1   xxxxx   xx MB
```

---

## 4. 修改配置文件

### 4.1 编辑 `.env`

```bash
vi .env
```

**必须修改的配置：**

```ini
# 生成随机密钥（重要！不可用默认值）
APP_SECRET_KEY=<使用 openssl rand -base64 32 生成>
```

**按需修改的配置：**

```ini
# 服务端口（默认 8088，冲突时修改）
ZBX_PORT=8088

# 时区
TZ=Asia/Shanghai

# 首次登录密码（登录后建议立即修改）
DEFAULT_ADMIN_PASSWORD=Admin@123
```

### 4.2 确认 `docker-compose.yml`

检查端口映射和挂载路径是否符合预期，一般无需修改。

---

## 5. 启动服务

```bash
cd /opt/zbxscreen

# 创建数据目录（设置可写权限）
mkdir -p data logs
chmod 777 data logs

# 启动容器（后台运行）
docker compose up -d

# 查看启动日志
docker compose logs -f
# 看到 "success: scheduler entered RUNNING state" 后按 Ctrl+C 退出
```

---

## 6. 检查服务状态

### 6.1 健康检查

```bash
curl http://localhost:8088/api/v1/health
```

预期输出：
```json
{"status":"healthy","timestamp":"...","version":"1.0.0","services":{"database":"ok"}}
```

### 6.2 检查 scheduler（数据聚合）

```bash
# 等待 30 秒后检查 scheduler 日志
docker compose logs --tail=10 zabbixscreen | grep AGGREGATOR
```

预期输出类似：
```
[AGGREGATOR] Done: 1 sources, 251 hosts (244 online), ... cpu=10 mem=10 ...
```

如果看到 `cpu=0 mem=0` 或无输出，说明 scheduler 未正常运行，执行：
```bash
docker compose logs zabbixscreen | grep -i "error\|traceback"
```

### 6.3 检查进程

```bash
docker compose ps
# STATUS 应为 "Up" 且 "(healthy)"
```

---

## 7. 登录使用

### 7.1 浏览器访问

```
http://<服务器IP>:8088
```

### 7.2 登录

| 项目 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `.env` 中 `DEFAULT_ADMIN_PASSWORD` 的值（默认 `Admin@123`） |

> 首次使用默认密码登录会弹出修改密码提示，建议立即修改。

### 7.3 配置 Zabbix 数据源

登录后进入 **数据源管理**，添加 Zabbix Server 连接：

| 字段 | 说明 |
|------|------|
| 名称 | 自定义，如"生产环境Zabbix" |
| URL | Zabbix API 地址，如 `http://10.4.0.250` |
| 用户名 | Zabbix API 用户 |
| 密码 | Zabbix API 密码 |

点击 **测试连接**，确认成功后保存。

> 支持 Zabbix 5.x / 6.x / 7.x，系统会自动适配 API 版本。

### 7.4 添加后首次数据加载

数据源保存后，scheduler 会在 **30 秒内**开始首次数据聚合（约 10-30 秒完成，取决于主机数量）。聚合完成后各监控大屏将显示数据。

---

## 8. 常用运维命令

```bash
# 进入部署目录
cd /opt/zbxscreen

# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 启动服务
docker compose up -d

# 更新镜像后重新部署
docker compose down
docker load < zabbixscreen-v1.2.tar.gz
# 修改 docker-compose.yml 中的镜像 tag 为 v1.2
docker compose up -d
```

---

## 9. 数据备份与恢复

```bash
# 备份数据库
cp /opt/zbxscreen/data/zabbixscreen.db /opt/backup/zabbixscreen-$(date +%Y%m%d).db

# 恢复数据库（先停止容器）
docker compose down
cp /opt/backup/zabbixscreen-20260101.db /opt/zbxscreen/data/zabbixscreen.db
chmod 666 /opt/zbxscreen/data/zabbixscreen.db
docker compose up -d
```

---

## 10. 故障排查

| 现象 | 排查方法 |
|------|----------|
| 容器无法启动 | `docker compose logs` 查看错误；检查端口是否冲突 |
| 页面能打开但无数据 | 确认已配置数据源；`docker compose logs \| grep AGGREGATOR` 检查 scheduler |
| scheduler 日志有 `Permission denied: '/data'` | 数据目录权限不足：`chmod 777 data/` |
| scheduler 日志有 `timeout` | Zabbix API 超时：增加 `.env` 中 `ZABBIX_REQUEST_TIMEOUT` 的值 |
| 主机数量为 0 | 确认 Zabbix 数据源 URL、用户名、密码正确；测试连接 |
| CPU/内存数据为空 | 确认 Zabbix 主机有 `system.cpu.util[,idle]` 和 `vm.memory.utilization` 监控项 |

---

## 11. 网络设备识别配置

如需网络监控大屏显示设备数据，请在 Zabbix 中将网络设备（交换机、路由器、防火墙等）分配到以下**任一**主机组：

| 主机组名称 | 说明 |
|-----------|------|
| `网络设备` | 通用网络设备 |
| `网络安全设备` | 防火墙、IPS 等 |
| `安全设备` | 安全类设备 |
| `交换机` | 交换机 |
| `路由器` | 路由器 |

> 主机组名称需**严格匹配**。设备加入上述任一主机组后，网络监控大屏将自动识别并展示。

---

*手册版本：v1.1 | 适用 ZBXScreen v1.1+*
