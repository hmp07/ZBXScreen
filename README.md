# ZBXScreen — 统一运维门户

轻量级 Zabbix 监控大屏 + 运维系统集成门户，单容器部署，开箱即用。

## 核心功能

- **监控大屏**：数据中心大屏 / 网络监控大屏 / 告警大屏，30s 自动刷新
- **主机管理**：主机列表、历史趋势图、触发器详情
- **告警管理**：告警规则、告警记录、Webhook 推送、告警风暴抑制
- **运维门户**：Zabbix / iTop 一键跳转，自动登录，无二次认证
- **多架构支持**：linux/amd64、linux/arm64

## 快速开始

```bash
# 1. 配置环境
cp .env.example .env
vi .env  # 修改 APP_SECRET_KEY

# 2. 启动
docker compose up -d

# 3. 访问 http://localhost:8088
# 默认账号：admin / Admin@123
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + ECharts 5 |
| 后端 | Python 3.11+ + FastAPI + SQLAlchemy 2.0 + aiosqlite |
| 数据库 | SQLite (WAL 模式) |
| 部署 | Docker + Supervisor (Nginx + Uvicorn + Scheduler) |

## 支持的 Zabbix 版本

Zabbix 5.x / 6.x / 7.x

## 文档

- [项目设计方案](项目设计方案-ZabbixScreen-v1.1.md)
- [部署手册](DEPLOY.md)
