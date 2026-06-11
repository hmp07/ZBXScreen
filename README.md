# ZabbixScreen — Zabbix 监控大屏展示系统

轻量级 Zabbix 监控数据可视化大屏，单容器部署，开箱即用。

## 快速开始

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env，修改 APP_SECRET_KEY

# 2. 启动服务
docker-compose up -d

# 3. 访问
# http://localhost:8088
# 默认账号：admin / admin123
```

## 开发环境

### 后端

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python ../scripts/init_db.py
uvicorn main:app --reload --host 0.0.0.0 --port 5001
# Swagger: http://localhost:5001/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### Docker 开发

```bash
docker-compose -f docker-compose.dev.yml up --build
# http://localhost:8088
```

## 技术栈

- **前端**: Vue 3 + TypeScript + Vite + Element Plus + ECharts 5
- **后端**: Python 3.11+ + FastAPI + SQLAlchemy 2.0 + aiosqlite
- **数据库**: SQLite (WAL 模式)
- **部署**: Docker + Supervisor (Nginx + Uvicorn + Scheduler)

## 支持的 Zabbix 版本

Zabbix 5.x / 6.x / 7.x

## 项目文档

详见 [项目设计方案](项目设计方案-ZabbixScreen-v1.1.md)
