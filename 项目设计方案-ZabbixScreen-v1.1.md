# ZBXScreen — 统一运维门户

## 项目设计方案 v1.3

> **状态：已发布** | 当前版本：v1.3 | 文档版本：v1.3
>
> **v1.3 更新说明**（2026-07-17）：
> - 新增运维门户融合：Zabbix/iTop 自动登录桥接页，侧边栏"运维功能"子菜单
> - 告警引擎重写：event_id 改为 `{triggerid}_{lastchange}`，解决告警全部误恢复的重大 Bug
> - 主机状态修正：区分启用/停用/在线/离线四种状态，排除停用主机参与在线统计
> - 侧边栏菜单重组：监控大屏/主机管理/运维功能/系统设置 四级菜单
> - 新增 Scheduler 健康检查端点 `/api/v1/scheduler-status`
> - 品牌统一：ZBXScreen 统一命名，前端/后端/webhook 全部一致
> - 安全加固：iTop 密码 AES 加密、Nginx 安全头+速率限制、URL 协议校验
> - PUT/DELETE 全部改为 POST（适配客户现场 WAF 设备）

---

## 目录

1. [项目定位与目标](#一项目定位与目标)
2. [技术选型](#二技术选型)
3. [系统架构设计](#三系统架构设计)
4. [功能模块详细设计](#四功能模块详细设计)
5. [数据流设计](#五数据流设计)
6. [API 接口设计](#六api-接口设计)
7. [数据库设计](#七数据库设计)
8. [项目目录结构](#八项目目录结构)
9. [Docker 部署方案（multi-arch）](#九docker-部署方案multi-arch)
10. [开发里程碑规划](#十开发里程碑规划)
11. [开发规范](#十一开发规范)
12. [本地开发环境搭建](#十二本地开发环境搭建)
13. [规模边界与性能考量](#十三规模边界与性能考量)
14. [附录 A：Zabbix 版本兼容详情](#附录-azabbix-版本兼容详情)
15. [附录 B：大屏异常状态展示规范](#附录-b大屏异常状态展示规范)
16. [附录 C：关键技术决策说明](#附录-c关键技术决策说明)

---

## 一、项目定位与目标

### 1.1 项目定位

ZBXScreen 是一款**轻量级 Zabbix 监控大屏 + 运维系统集成门户**。单容器部署，将 Zabbix 监控数据可视化与运维系统（Zabbix 前端 / iTop ITSM）统一入口融合，实现一键跳转、自动登录。

核心能力：
- **实时监控大屏**：数据中心大屏、网络监控大屏、告警大屏，30s 自动刷新
- **主机管理**：主机列表、历史趋势图、触发器详情
- **告警管理**：告警规则、告警记录、Webhook 推送、告警风暴抑制
- **运维门户**：Zabbix / iTop 一键跳转，自动登录（Nginx 反代 + 凭证注入 / 登录桥接页）

### 1.2 核心目标

| 目标 | 说明 |
|------|------|
| **轻量化** | SQLite 内嵌数据库，单容器部署，无需额外数据库服务 |
| **开箱即用** | 零配置接入 Zabbix，连接后自动发现并展示监控数据 |
| **大屏聚焦** | 监控大屏/网络大屏/告警大屏，适配运维指挥中心场景 |
| **运维门户** | Zabbix 前端 / iTop ITSM 统一入口，自动登录，无需二次认证 |
| **快速部署** | Docker Compose 一键启动，支持 amd64 和 ARM64 |
| **兼容性强** | 支持 Zabbix 5.x / 6.x / 7.x 版本 |

## 二、技术选型

| 层级 | 技术方案 | 版本要求 | 选型理由 |
|------|---------|---------|---------|
| **前端框架** | Vue 3 + Vite | Vue 3.4+，Vite 5+ | 轻量、生态成熟，适合大屏可视化场景 |
| **UI 组件库** | Element Plus | 2.x | 中文文档完善，组件丰富 |
| **图表引擎** | ECharts 5 | 5.4+ | 强大的可视化能力，大屏展示首选 |
| **拖拽引擎** | vue-draggable-plus | 最新稳定版 | 轻量级拖拽，适合大屏编辑器（P2） |
| **状态管理** | Pinia | 2.x | Vue 3 官方推荐，简洁高效 |
| **HTTP 客户端** | Axios | 1.x | 成熟稳定，拦截器机制完善 |
| **后端框架** | Python + FastAPI | Python 3.11+，FastAPI 0.110+ | 异步高性能，Zabbix API 对接方便，自带 Swagger |
| **异步运行时** | uvicorn | 0.29+ | ASGI 服务器，生产可配合 gunicorn |
| **数据库** | SQLite（WAL 模式） | SQLite 3.35+ | 零运维，轻量部署，配置 WAL 模式解决并发写入 |
| **ORM** | SQLAlchemy 2.0 + aiosqlite | 2.0+ | 异步支持，与 FastAPI 配合佳 |
| **任务调度** | APScheduler | 3.x | 轻量定时任务，无需额外 Worker 进程 |
| **部署** | Docker + Docker Compose | Docker 24+，Compose v2 | 一键部署，环境一致 |
| **多架构构建** | Docker Buildx | Buildx 0.11+ | 支持 linux/amd64 和 linux/arm64 同时构建推送 |
| **反向代理** | Nginx | 1.25+ alpine | 静态资源 + API 统一入口 |

### 技术栈架构图

```
┌──────────────────────────────────────────────────────┐
│               Docker Container (单容器)               │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │            Nginx :80 (暴露 :8088)             │   │
│   │       静态资源服务 + /api/* 反向代理            │   │
│   └────────────────────┬─────────────────────────┘   │
│                        │                             │
│   ┌────────────────────▼─────────────────────────┐   │
│   │         FastAPI Backend :5001 (内部)          │   │
│   │  ┌──────────────┐  ┌────────────────────────┐│   │
│   │  │ Zabbix API   │  │ SQLite (WAL 模式)       ││   │
│   │  │ Client 模块   │  │ zabbixscreen.db        ││   │
│   │  └──────────────┘  └────────────────────────┘│   │
│   │  ┌──────────────┐  ┌────────────────────────┐│   │
│   │  │ 数据聚合      │  │ APScheduler 定时任务    ││   │
│   │  │ 缓存模块      │  │ (大屏轮询/告警检测)     ││   │
│   │  └──────────────┘  └────────────────────────┘│   │
│   │  ┌──────────────┐                             │   │
│   │  │ Webhook 推送  │ → AI 分析引擎 (外部)        │   │
│   │  │ (含重试/记录) │                             │   │
│   │  └──────────────┘                             │   │
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │     Vue 3 前端静态文件 (Nginx 服务)            │   │
│   └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
        ┌──────────┐        ┌──────────────┐
        │  Zabbix  │        │  AI 分析引擎  │
        │  Server  │        │  (Webhook端点)│
        └──────────┘        └──────────────┘
```

---

## 三、系统架构设计

### 3.1 整体架构

```
                    ┌──────────────────┐
                    │    用户浏览器      │
                    │  (Chrome/F11)    │
                    └────────┬─────────┘
                             │ HTTP
                    ┌────────▼─────────┐
                    │    Nginx :8088    │
                    ├────────┬──────────┤
                    │        │          │
            ┌───────▼──┐  ┌▼───────────┴──────┐
            │Vue 3 SPA  │  │  FastAPI :5001    │
            │ 前端静态   │  ├───────────────────┤
            └──────────┘  │  模块列表:          │
                          │  · 用户认证 (JWT)   │
                          │  · 数据源管理       │
                          │  · 监控数据聚合     │
                          │  · 主机历史查询     │
                          │  · 告警检测引擎     │
                          │  · Webhook 推送器  │
                          │  · 系统设置        │
                          ├───────────────────┤
                          │  SQLite (WAL)      │
                          │  · datasource      │
                          │  · dashboard       │
                          │  · alert_rule      │
                          │  · alert_record    │
                          │  · webhook_config  │
                          │  · webhook_log     │
                          │  · settings        │
                          └───────────────────┘
                                   │
                    ┌──────────────┴───────────┐
                    │                          │
              ┌─────▼──────┐         ┌────────▼──────┐
              │ Zabbix API  │         │  AI 分析引擎   │
              │ (外部访问)  │         │  (Webhook)    │
              └────────────┘         └───────────────┘
```

### 3.2 后端模块划分

```
backend/
├── main.py                    # FastAPI 应用入口，仅挂载路由（不初始化 scheduler）
├── config.py                  # 配置管理（环境变量/默认值）
├── database.py                # SQLite 初始化（WAL 模式 PRAGMA 配置 + 连接池）
├── models/                    # SQLAlchemy ORM 数据模型
│   ├── __init__.py
│   ├── user.py                # 用户（管理员账号）
│   ├── datasource.py          # Zabbix 数据源配置
│   ├── dashboard.py           # 自定义大屏配置
│   ├── dashboard_widget.py    # 大屏组件定义
│   ├── alert_rule.py          # 告警规则
│   ├── alert_record.py        # 告警记录
│   ├── webhook_config.py      # Webhook 端点配置
│   ├── webhook_log.py         # Webhook 推送日志
│   └── settings.py            # 系统设置（键值对）
├── api/                       # FastAPI 路由层（仅负责请求/响应处理）
│   ├── __init__.py
│   ├── auth.py                # 登录/Token 刷新/修改密码
│   ├── datasource.py          # 数据源 CRUD + 测试连接
│   ├── monitor.py             # 大屏汇总数据/TOP N/告警列表
│   ├── host.py                # 主机列表 + 历史数据
│   ├── dashboard.py           # 自定义大屏管理（P2）
│   ├── alert.py               # 告警规则 + 记录
│   ├── webhook.py             # Webhook 配置 + 测试 + 日志
│   └── settings.py            # 系统设置
├── services/                  # 业务逻辑层（核心实现）
│   ├── __init__.py
│   ├── zabbix_client.py       # Zabbix API 封装（login/host/item/history/trigger，含版本适配）
│   ├── data_aggregator.py     # 大屏数据聚合（合并多数据源，计算 TOP N，写入聚合缓存表）
│   ├── alert_engine.py        # 告警检测引擎（轮询 Zabbix 触发器，比对规则，含告警风暴抑制）
│   ├── webhook_sender.py      # Webhook 推送（标准化格式+指数退避重试+日志记录）
│   └── scheduler.py           # 独立调度器进程（APScheduler，非 FastAPI worker 内启动）
├── scheduler_main.py          # 调度器独立入口（由 supervisor 单独管理）
├── alembic/                   # 数据库迁移（Alembic）
│   ├── env.py
│   └── versions/
├── tests/                     # 后端测试
│   ├── conftest.py            # pytest fixtures（mock Zabbix API、测试数据库）
│   ├── test_zabbix_client.py
│   ├── test_data_aggregator.py
│   ├── test_alert_engine.py
│   └── test_webhook_sender.py
└── utils/                     # 工具函数
    ├── __init__.py
    ├── auth.py                # JWT 生成/验证
    ├── cache.py               # 聚合数据缓存（SQLite 缓存表 + 内存 TTL 双层）
    └── crypto.py              # AES-128-CBC 加密/解密（随机 IV）
```

### 3.3 前端模块划分

```
frontend/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts         # 路由（含守卫，未登录跳转 /login）
│   ├── views/
│   │   ├── Login.vue           # 登录页
│   │   ├── Dashboard.vue       # 默认监控大屏（P1）
│   │   ├── DashboardList.vue   # 自定义大屏列表（P2）
│   │   ├── DashboardEdit.vue   # 大屏编辑器（P2）
│   │   ├── DashboardView.vue   # 大屏全屏展示（P2）
│   │   ├── HostList.vue        # 主机列表（P1）
│   │   ├── HostDetail.vue      # 主机历史详情（P1）
│   │   ├── AlertRules.vue      # 告警规则管理（P1）
│   │   ├── AlertRecords.vue    # 告警记录（P1）
│   │   ├── WebhookConfig.vue   # Webhook 配置（P1）
│   │   └── Settings.vue        # 系统设置（P1）
│   ├── components/
│   │   ├── charts/
│   │   │   ├── HostCard.vue        # 主机状态卡片
│   │   │   ├── CpuChart.vue        # CPU 趋势图
│   │   │   ├── MemChart.vue        # 内存趋势图
│   │   │   ├── DiskChart.vue       # 磁盘使用图
│   │   │   ├── NetworkChart.vue    # 网络流量图
│   │   │   └── TopNChart.vue       # TOP N 柱状图
│   │   ├── dashboard/          # 大屏编辑器组件（P2）
│   │   │   ├── WidgetPanel.vue
│   │   │   ├── Canvas.vue
│   │   │   ├── PropertyPanel.vue
│   │   │   └── widgets/
│   │   │       ├── StatCard.vue
│   │   │       ├── LineChart.vue
│   │   │       ├── BarChart.vue
│   │   │       ├── PieChart.vue
│   │   │       ├── GaugeChart.vue
│   │   │       ├── TableWidget.vue
│   │   │       ├── TextWidget.vue
│   │   │       └── IframeWidget.vue
│   │   └── layout/
│   │       ├── AppLayout.vue
│   │       ├── Sidebar.vue
│   │       └── Header.vue
│   ├── stores/
│   │   ├── auth.ts
│   │   ├── datasource.ts
│   │   ├── monitor.ts
│   │   └── settings.ts
│   ├── api/
│   │   ├── request.ts          # Axios 实例（拦截器，401 自动跳转登录）
│   │   ├── auth.ts
│   │   ├── datasource.ts
│   │   ├── monitor.ts
│   │   ├── host.ts
│   │   ├── dashboard.ts
│   │   ├── alert.ts
│   │   └── webhook.ts
│   └── utils/
│       ├── format.ts           # 单位格式化（字节→GB，Hz→GHz 等）
│       └── zabbix.ts           # Zabbix item key → 中文名/单位映射
└── public/
```

---

## 四、功能模块详细设计

### 4.1 数据源管理模块

**功能说明**：配置 Zabbix Server 连接信息，支持多 Zabbix 实例接入。

| 功能项 | 说明 |
|--------|------|
| 添加数据源 | 配置 Zabbix URL、用户名、密码、备注名称 |
| 测试连接 | 验证连接是否可用，显示 Zabbix 版本号 |
| 编辑/删除 | 修改或移除数据源配置 |
| 自动发现 | 连接后自动拉取主机组、主机列表并缓存 |
| 连接状态 | 实时显示连接状态（在线 🟢 / 离线 🔴） |
| 启用/禁用 | 临时禁用某个数据源而不删除配置 |
| 重名主机去重 | 多数据源场景下，相同 hostname/IP 的主机自动去重（默认按 hostname） |

**密码存储**：密码在数据库中必须使用 AES-128-CBC 加密存储，不可明文。

**加密方案**（`utils/crypto.py` 实现）：

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os, hashlib

def derive_key(secret: str) -> bytes:
    """从 APP_SECRET_KEY 派生 16 字节 AES-128 密钥"""
    return hashlib.sha256(secret.encode()).digest()[:16]

def encrypt_password(plaintext: str, secret: str) -> str:
    """AES-128-CBC 加密，每次生成随机 IV，返回 base64(iv + ciphertext)"""
    key = derive_key(secret)
    iv = os.urandom(16)  # 每次加密生成新的随机 IV
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode()

def decrypt_password(encoded: str, secret: str) -> str:
    """解密，从前 16 字节提取 IV"""
    raw = base64.b64decode(encoded)
    iv, ciphertext = raw[:16], raw[16:]
    cipher = AES.new(derive_key(secret), AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode()
```

> **安全要点**：每次加密使用 `os.urandom(16)` 生成随机 IV，IV 与密文拼接存储。解密时从拼接数据中提取 IV。即使同一密码两次加密，密文也不相同（防止密文分析）。密钥从 `APP_SECRET_KEY` 的 SHA-256 哈希截取前 16 字节。

### 4.2 默认监控大屏模块

**功能说明**：开箱即用的默认监控大屏，自动展示所有已连接 Zabbix 的主机数据。

**大屏布局设计**（1920×1080 基准）：

```
┌─────────────────────────────────────────────────────────────┐
│  ZabbixScreen   [当前时间]   [数据源筛选]  [刷新频率] [全屏]  │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ 主机总数  │ 在线数量  │ 离线数量  │ 告警数量  │  CPU 使用率TOP5 │
│  (数值卡) │  (数值卡) │  (数值卡) │  (数值卡) │  (横向柱状图)  │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                                                             │
│          主机状态卡片矩阵（按主机组 Tab 切换）                  │
│      每张卡片：主机名 / CPU% / 内存% / 磁盘% / 在线状态       │
│                                                             │
├────────────────────────┬────────────────────────────────────┤
│  网络流量 TOP10         │  内存使用率 TOP10                   │
│  （水平柱状图）          │  （水平柱状图）                     │
├────────────────────────┼────────────────────────────────────┤
│  最近告警列表（滚动）    │  磁盘使用率 TOP10                   │
│  时间/主机/告警内容/级别 │  （水平柱状图）                     │
└────────────────────────┴────────────────────────────────────┘
```

**大屏功能**：
- **自动刷新**：默认 30 秒轮询，支持 10s / 30s / 60s / 120s 切换
- **全屏模式**：F11 全屏 / ESC 退出，支持点击按钮触发
- **主机组筛选**：下拉/Tab 切换按主机组过滤展示
- **主机卡片**：鼠标悬停显示详细 Tooltip（含 IP、运行时长、详细资源值）
- **响应式布局**：支持 1920×1080、1440×900 等常见分辨率

### 4.3 主机监控模块

**主机列表页**：
- 表格展示所有主机：主机名、IP、主机组、状态、CPU%、内存%、磁盘%、网络速率
- 支持按主机名/IP 搜索
- 支持按主机组筛选
- 点击主机名进入详情

**主机详情页**：
- **基本信息区**：主机名、IP、主机组、Zabbix 版本、操作系统、运行时长
- **实时数据区**：CPU、内存、磁盘、网络四块卡片（最新值 + 迷你趋势图）
- **历史趋势区**：
  - 时间范围：最近 1h / 6h / 24h / 7d / 30d / 自定义（精确到分钟）
  - 图表：CPU 折线图、内存折线图、磁盘使用率折线图、网络收发速率双折线图
  - 支持图表缩放和数据点 Tooltip

**P1 阶段 Zabbix Item Key 列表**：

| 指标 | Item Key | 说明 |
|------|----------|------|
| CPU 使用率 | `system.cpu.util[,idle]` | 返回 idle 百分比，使用率 = 100 - idle |
| 内存使用率 | `vm.memory.size[pused]` | 已用内存占总内存百分比 |
| 磁盘使用率（根分区） | `vfs.fs.size[/,pused]` | P1 默认监控根分区 `/` |
| 磁盘使用率（扩展） | `vfs.fs.size[/home,pused]` 等 | P2 支持多挂载点配置 |
| 网络入流量 | `net.if.in[{interface}]` | 网卡入方向字节率（默认 bytes/s），前端按需转换为 bps |
| 网络出流量 | `net.if.out[{interface}]` | 网卡出方向字节率 |

> **网卡自适应策略**（现代 Linux 网络接口名称已从 `eth0` 迁移到 Predictable Network Interface Names）：
> ```python
> # 实现参考：services/zabbix_client.py
> PREFERRED_INTERFACES = ["eth0", "ens33", "enp0s3", "eno1", "ens192", "ens160"]
> 
> async def discover_network_interface(zabbix_client, host_id):
>     items = await zabbix_client.item.get(
>         hostids=[host_id],
>         search={"key_": "net.if.in"},    # 模糊搜索所有网卡
>         output=["itemid", "key_"],
>     )
>     # 1. 按 PREFERRED_INTERFACES 顺序匹配
>     # 2. 若无匹配，选第一个非 lo 的活跃网卡
>     # 3. 从 key_ 中提取接口名（如 net.if.in[ens33] → ens33）
>     # 4. 排除回环接口 lo
> ```
>
> **磁盘多挂载点处理**：
> - P1 阶段：默认监控根分区 `/`，使用 `vfs.fs.size[/,pused]`
> - 通过 `vfs.fs.discovery` 自动发现主机所有挂载点，前端默认展示 `/`，详情页可切换查看其他挂载点
> - P2 阶段：支持用户自定义监控的挂载点列表

### 4.4 Webhook 告警模块（AI 引擎对接出口）

> **重要说明**：此模块是 ZabbixScreen 与外部 AI 分析引擎对接的核心接口，P1 期必须实现。
>
> 设计原则：推送数据需自包含（携带上下文指标），AI 引擎无需再回调 ZabbixScreen 即可完成分析。

**4.4.1 Webhook 端点配置**

支持配置多个 Webhook 端点，每个端点可绑定不同告警级别或主机组：

| 配置项 | 类型 | 说明 |
|--------|------|------|
| 名称 | String | 端点标识，如"AI 告警引擎"、"企业微信 Bot" |
| URL | String | 接收端地址 |
| 请求方式 | Enum | POST / PUT（默认 POST） |
| 自定义 Headers | JSON | 如 `{"Authorization": "Bearer xxx", "X-API-Key": "yyy"}` |
| 触发级别 | MultiSelect | INFO / WARNING / HIGH / DISASTER |
| 绑定主机组 | MultiSelect | 为空表示全部主机组 |
| 启用状态 | Bool | 开关，禁用不影响配置保留 |
| 重试次数 | Int | 默认 3 次 |
| 重试间隔 | Int | 默认 10s，采用指数退避（10s → 20s → 40s） |
| 连接超时 | Int | 默认 10s |

**4.4.2 推送数据格式（标准化 JSON Schema）**

**新告警事件**：

```json
{
  "schema_version": "1.0",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "alert",
  "event_time": "2026-06-01T10:00:00+08:00",
  "source": {
    "system": "zabbixscreen",
    "version": "1.1.0",
    "instance_url": "http://your-server:8088"
  },
  "host": {
    "id": "10001",
    "name": "web-server-01",
    "visible_name": "生产Web服务器-01",
    "ip": "192.168.1.10",
    "groups": ["Linux servers", "生产环境"],
    "zabbix_source": "Zabbix-生产"
  },
  "alert": {
    "trigger_id": "20011",
    "trigger_name": "CPU使用率超过90%持续5分钟",
    "level": "HIGH",
    "level_code": 4,
    "item_key": "system.cpu.util[,idle]",
    "item_name": "CPU idle time",
    "current_value": "7.5",
    "current_value_unit": "%",
    "threshold": "10",
    "operator": "<",
    "duration_seconds": 300,
    "first_occurred": "2026-06-01T09:55:00+08:00"
  },
  "context": {
    "cpu_utilization_recent": [88.1, 89.3, 91.2, 92.5, 93.0],
    "memory_utilization": 75.4,
    "disk_utilization": 62.1,
    "network_in_bps": 1048576,
    "network_out_bps": 524288,
    "data_points_interval_seconds": 60,
    "active_alerts_count": 3
  }
}
```

**告警恢复事件**（`event_type: "recovery"`）：

```json
{
  "schema_version": "1.0",
  "event_id": "550e8400-e29b-41d4-a716-446655441000",
  "event_type": "recovery",
  "event_time": "2026-06-01T10:15:00+08:00",
  "source": {
    "system": "zabbixscreen",
    "version": "1.1.0",
    "instance_url": "http://your-server:8088"
  },
  "host": {
    "id": "10001",
    "name": "web-server-01",
    "visible_name": "生产Web服务器-01",
    "ip": "192.168.1.10",
    "zabbix_source": "Zabbix-生产"
  },
  "alert": {
    "trigger_id": "20011",
    "trigger_name": "CPU使用率超过90%持续5分钟",
    "level": "HIGH",
    "level_code": 4,
    "recovered": true,
    "first_occurred": "2026-06-01T09:55:00+08:00",
    "recovered_at": "2026-06-01T10:14:30+08:00",
    "duration_seconds": 1170
  }
}
```

> **恢复事件说明**：恢复事件不携带 `context` 字段（减少 payload）。AI 引擎通过 `event_type` 字段区分新告警（`"alert"`）和恢复通知（`"recovery"`）。恢复事件携带 `recovered: true` 作为冗余标识。

**告警级别映射**：

| level_code | level | 说明 |
|-----------|-------|------|
| 1 | INFO | 信息 |
| 2 | WARNING | 警告 |
| 3 | AVERAGE | 一般严重 |
| 4 | HIGH | 严重 |
| 5 | DISASTER | 灾难 |

**Webhook JSON Schema 说明**：

本文档中 4.4.2 节定义的 JSON Schema 为**标准化告警推送格式**，具备以下特性：
- **自包含**：新告警携带完整告警上下文（近期指标数据），AI 引擎无需回调解压即可完成分析
- **事件区分**：`event_type` 字段取值为 `"alert"`（新告警）或 `"recovery"`（恢复通知），AI 引擎据此路由不同处理逻辑
- **版本化**：`schema_version` 字段标识格式版本，便于未来扩展
- **结构化**：`source`、`host`、`alert`、`context` 四层结构清晰，易于解析
- **恢复精简**：恢复事件（`event_type: "recovery"`）不携带 `context`，减少无效数据传输

> **AI 引擎对接要求**：接收端应验证 `schema_version` 并兼容 1.0 格式。

**4.4.3 Webhook 推送流程**

```
告警检测引擎检测到告警
       │
       ▼
  ┌──────────────────────────┐
  │ 1. 告警风暴聚合窗口判断    │  ← 60s 窗口内相同主机组的告警合并
  │    避免批量告警洪泛推送    │
  └──────────┬───────────────┘
             ▼
  ┌──────────────────────┐
  │ 2. 匹配 Webhook 端点  │  ← 按级别 + 主机组过滤
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │ 3. 构建标准化 Payload │  ← alert 事件查询近期指标数据填充 context
  │    recovery 事件不填充│     recovery 事件仅携带恢复时间和持续时长
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │ 4. HTTP POST 推送     │
  └──────────┬───────────┘
             │
      ┌──────┴──────┐
   成功（2xx）    失败（非2xx/超时）
      │               │
      ▼               ▼
  记录成功日志    指数退避重试（最多3次）
                      │
               重试仍失败 → 记录失败日志 + 告警页面标记
```

**告警风暴抑制策略**（`alert_engine.py` 中实现）：

```python
# 告警聚合窗口：60 秒
ALERT_AGGREGATION_WINDOW = 60

async def process_triggers(triggers):
    pending_alerts = []
    for trigger in triggers:
        # 判断是否为新告警
        if is_new_or_changed(trigger):
            pending_alerts.append(trigger)

    if len(pending_alerts) >= 5:
        # 超过阈值：按主机组合并，批量推送
        batched = group_by_hostgroup(pending_alerts)
        for batch in batched.values():
            # 合并 context：取各主机最新指标
            # 推送一条聚合告警，主机的告警详情作为子项
            await send_batched_webhook(batch)
    else:
        # 少量告警：逐条推送（含完整 context）
        for alert in pending_alerts:
            await send_single_webhook(alert)
```

> **设计考量**：告警风暴场景下（如一台核心交换机故障导致 50+ 主机不可达），逐条推送不仅效率低下，还可能触发 Webhook 接收端的速率限制。聚合窗口确保同一批次的主机组告警合并为一次推送，同时保留每条告警的细节。

**4.4.4 Webhook 推送日志**

页面展示近 7 天推送记录，字段：事件ID、触发时间、目标端点、推送状态（成功/失败/重试中）、HTTP 状态码、重试次数、响应耗时。

### 4.5 告警规则模块（P1）

**告警规则来源**：
1. **Zabbix 触发器同步**：自动同步 Zabbix 已有触发器作为告警源
2. **自定义阈值规则**：在 ZabbixScreen 内定义附加规则（如持续时间告警）

**告警记录**：
- 列表：时间、主机、告警内容、级别、状态（活跃/已恢复）、Webhook 推送状态
- 时间范围筛选
- 告警统计面板：按级别、按主机组分布图表

### 4.6 系统设置模块

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| 系统标题 | 大屏顶部显示的标题 | ZabbixScreen |
| 默认刷新频率 | 大屏轮询间隔（秒） | 30 |
| 数据保留天数 | 告警记录、Webhook 日志保留时长 | 30 |
| 修改密码 | 管理员密码修改 | - |
| 大屏背景主题 | 深色/浅色 | 深色 |
| 时区 | 系统时区 | Asia/Shanghai |

---

## 五、数据流设计

### 5.1 Zabbix API 调用流程

```
前端请求 → FastAPI → Zabbix API Client
                        │
                        ├── zabbix.user.login()         → 获取 auth token（有效期管理）
                        ├── zabbix.host.get()            → 主机列表（含接口、主机组）
                        ├── zabbix.item.get()            → 监控项列表
                        ├── zabbix.history.get()         → 历史数据（按时间范围）
                        ├── zabbix.trend.get()           → 趋势数据（>1天用 trend）
                        ├── zabbix.trigger.get()         → 告警触发器
                        └── zabbix.hostgroup.get()       → 主机组
```

**Zabbix Token 管理策略**：
- Token 缓存在内存中（TTL 3600s）
- 请求失败时自动重新 login
- 支持 Zabbix 5.x/6.x/7.x 不同认证接口差异兼容（7.x 使用 `user.login` → `user.checkAuthentication`）

### 5.2 大屏数据聚合流程

> **架构说明**：调度器作为独立进程运行（由 supervisor 管理），不与 FastAPI worker 共享进程空间。聚合结果写入 SQLite 聚合缓存表 + 内存 TTL 缓存，API worker 查询缓存而非直接调用 Zabbix。

```
独立调度器进程（APScheduler，每 30 秒触发）
       │
       ▼
  ┌─────────────────────┐
  │ 1. 遍历启用的数据源   │  ← 从 SQLite 读取配置
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │ 2. 并发拉取数据       │  ← asyncio.gather() 并发请求各 Zabbix
  │   - host.get         │    每个数据源有独立超时（默认 25s）
  │   - item lastval     │    超时数据源标记为"响应慢"，跳过本轮
  │   - trigger.get      │
  │   总超时: 28s         │  ← asyncio.wait_for() 包裹，留 2s 余量
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │ 3. 数据聚合计算       │  ← 合并多数据源
  │   - 状态统计         │    在线/离线/告警计数
  │   - TOP N 排序       │    CPU/内存/磁盘/网络 TOP10
  │   - 告警列表         │
  │   - 主机去重         │    按 hostname/IP 去重（跨数据源场景）
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │ 4. 写入聚合缓存表     │  ← SQLite monitor_cache 表（跨 worker 共享）
  │    + 更新内存 TTL     │     前端 API 请求直接读缓存，不调 Zabbix
  └─────────────────────┘
```

### 5.3 告警检测与 Webhook 推送流程

> 告警检测由独立调度器进程执行，与数据聚合共享同一个 APScheduler 实例。告警风暴抑制在 `alert_engine.py` 中实现。

```
独立调度器进程（APScheduler，每 60 秒触发）
       │
       ▼
  ┌────────────────────────┐
  │ 从 Zabbix 拉取活跃触发器 │  ← 按数据源并发拉取，各源独立超时 20s
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 对比告警规则配置        │  ← 过滤级别、主机组
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 新告警？写入 alert_record│  ← event_id 去重
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 告警风暴检测            │  ← 60s 窗口内 ≥5 条告警 → 按主机组合并
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 匹配 Webhook 端点配置   │
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ alert: 补充 context     │  ← 查历史数据填充上下文
  │ recovery: 不填充        │
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 异步 HTTP POST 推送     │  ← 不阻塞主流程
  │ + 指数退避重试          │
  │ + 写入 webhook_log     │
  └────────────────────────┘
```

### 5.4 前端数据刷新策略

| 页面 | 刷新策略 | 默认间隔 |
|------|---------|---------|
| 默认大屏 | setInterval 轮询 | 30s（可配置） |
| 主机列表 | 首次加载 + 手动刷新按钮 | - |
| 主机详情 | 首次加载 + 手动刷新 | - |
| 告警记录 | setInterval 轮询 | 60s |
| Webhook 日志 | 手动刷新 | - |

### 5.5 数据清理任务

> 每日凌晨 3:00 执行，清理过期数据以控制数据库体积。

```
APScheduler（每日 03:00 触发）
       │
       ▼
  ┌────────────────────────┐
  │ 读取 DATA_RETENTION_DAYS │  ← 从设置表读取保留天数（默认 30 天）
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 清理 alert_records     │  ← 删除 created_at 早于 N 天的记录
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 清理 webhook_logs       │  ← 同上
  └────────────┬───────────┘
               ▼
  ┌────────────────────────┐
  │ 记录清理日志            │  ← 记录清理数量和时间
  └────────────────────────┘
```

**scheduler.py 实现示例**：
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=3, minute=0)
async def cleanup_old_records():
    retention_days = int(get_setting("DATA_RETENTION_DAYS", 30))
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    async with get_db() as db:
        await db.execute(
            delete(AlertRecord).where(AlertRecord.created_at < cutoff_date)
        )
        await db.execute(
            delete(WebhookLog).where(WebhookLog.pushed_at < cutoff_date)
        )
```

---

## 六、API 接口设计

> 所有接口前缀：`/api/v1`
>
> 认证方式：Bearer JWT Token（`Authorization: Bearer <token>`），登录接口除外
>
> 统一响应格式：
> ```json
> { "code": 0, "message": "success", "data": {} }
> ```
> 错误时 code 非 0，message 包含错误描述。
>
> **分页参数规范**（适用于所有列表类接口）：
>
> | 参数 | 类型 | 默认值 | 说明 |
> |------|------|--------|------|
> | `page` | int | 1 | 页码（从 1 开始） |
> | `page_size` | int | 20 | 每页条数（最大 100） |
>
> 分页响应格式：
> ```json
> {
>   "code": 0,
>   "message": "success",
>   "data": {
>     "items": [...],
>     "total": 150,
>     "page": 1,
>     "page_size": 20,
>     "total_pages": 8
>   }
> }
> ```

### 6.1 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 登录，返回 access_token + refresh_token |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| PUT | `/api/v1/auth/password` | 修改密码（需旧密码验证） |

**Token 有效期定义**：
- `access_token`：有效期 30 分钟
- `refresh_token`：有效期 7 天

**Token 刷新策略（前端拦截器）**：
- Axios 响应拦截器在收到 401 时自动使用 refresh_token 换取新 access_token
- refresh 也失败时：保存当前页面路径到 sessionStorage，跳转登录页，登录成功后恢复
- 大屏全屏模式（无人值守场景）：大屏页面可配置使用独立的大屏查看 token（有效期 24h），避免全屏展示中因 token 过期而空白

**登录响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 1800,
    "token_type": "Bearer"
  }
}
```

### 6.2 数据源接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/datasources` | 获取所有数据源列表 |
| POST | `/api/v1/datasources` | 添加数据源 |
| PUT | `/api/v1/datasources/{id}` | 修改数据源 |
| DELETE | `/api/v1/datasources/{id}` | 删除数据源 |
| POST | `/api/v1/datasources/{id}/test` | 测试连接（返回 Zabbix 版本） |
| PUT | `/api/v1/datasources/{id}/toggle` | 启用/禁用数据源 |
| GET | `/api/v1/datasources/{id}/hostgroups` | 获取主机组列表 |
| GET | `/api/v1/datasources/{id}/hosts` | 获取主机列表 |

### 6.3 监控数据接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/monitor/summary` | 大屏汇总（主机总数/在线/离线/告警数） |
| GET | `/api/v1/monitor/hosts` | 主机最新数据列表（含 CPU/内存/磁盘/网络） |
| GET | `/api/v1/monitor/top-cpu` | CPU 使用率 TOP N（默认 N=10） |
| GET | `/api/v1/monitor/top-memory` | 内存使用率 TOP N |
| GET | `/api/v1/monitor/top-disk` | 磁盘使用率 TOP N |
| GET | `/api/v1/monitor/top-network` | 网络流量 TOP N |
| GET | `/api/v1/monitor/alerts` | 最近告警列表（大屏用，默认最新 20 条） |

**Query Parameters（hosts/top-* 接口）**：
```
datasource_id: int      # 可选，指定数据源，不传则聚合全部（跨数据源自动按 hostname 去重）
hostgroup_id: string    # 可选，按主机组过滤
limit: int              # 默认 10，最大 50
dedup_by: string        # 可选，跨数据源去重键：hostname（默认）/ ip
```

### 6.4 主机接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/hosts` | 主机列表（含基本信息和最新指标） |
| GET | `/api/v1/hosts/{hostid}` | 主机详情（基本信息 + 最新指标） |
| GET | `/api/v1/hosts/{hostid}/history` | 主机历史数据 |

**`/history` Query Parameters**：
```
item_key: string        # 监控项 key，如 system.cpu.util
start_time: ISO8601     # 开始时间
end_time: ISO8601       # 结束时间
datasource_id: int      # 数据源 ID
```

### 6.5 告警接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/alerts/rules` | 告警规则列表 |
| POST | `/api/v1/alerts/rules` | 创建自定义告警规则 |
| PUT | `/api/v1/alerts/rules/{id}` | 修改告警规则 |
| DELETE | `/api/v1/alerts/rules/{id}` | 删除告警规则 |
| PUT | `/api/v1/alerts/rules/{id}/toggle` | 启用/禁用规则 |
| GET | `/api/v1/alerts/records` | 告警记录列表（支持分页和时间筛选） |
| GET | `/api/v1/alerts/stats` | 告警统计（按级别/主机组分布） |

### 6.6 Webhook 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/webhooks` | Webhook 端点列表 |
| POST | `/api/v1/webhooks` | 创建 Webhook 端点 |
| PUT | `/api/v1/webhooks/{id}` | 修改 Webhook 端点 |
| DELETE | `/api/v1/webhooks/{id}` | 删除 Webhook 端点 |
| PUT | `/api/v1/webhooks/{id}/toggle` | 启用/禁用 |
| POST | `/api/v1/webhooks/{id}/test` | 发送测试推送（发送 mock 告警数据） |
| GET | `/api/v1/webhooks/{id}/logs` | 推送日志列表（支持分页） |

### 6.7 自定义大屏接口（P2 期实现）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboards` | 大屏列表 |
| POST | `/api/v1/dashboards` | 创建大屏 |
| GET | `/api/v1/dashboards/{id}` | 大屏详情（含组件配置） |
| PUT | `/api/v1/dashboards/{id}` | 更新大屏 |
| DELETE | `/api/v1/dashboards/{id}` | 删除大屏 |
| POST | `/api/v1/dashboards/{id}/copy` | 复制大屏 |
| GET | `/api/v1/dashboards/{id}/data` | 获取大屏实时数据 |
| GET | `/api/v1/dashboards/{id}/export` | 导出大屏 JSON |
| POST | `/api/v1/dashboards/import` | 导入大屏 JSON |

### 6.8 系统设置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/settings` | 获取所有设置 |
| PUT | `/api/v1/settings` | 批量更新设置 |

### 6.9 健康检查接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 服务健康检查（无需认证） |

**响应示例**：
```json
{
  "status": "healthy",
  "timestamp": "2026-06-01T10:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "ok",
    "zabbix": "ok"
  }
}
```

---

## 七、数据库设计

> 数据库：SQLite，文件路径：`/app/data/zabbixscreen.db`
>
> **必须配置 WAL 模式**（解决并发读写冲突）：
>
> ```python
> # database.py — 数据库初始化时执行以下 PRAGMA
> PRAGMA journal_mode = WAL;
> PRAGMA synchronous = NORMAL;
> PRAGMA cache_size = 10000;
> PRAGMA foreign_keys = ON;
> ```

### 7.1 用户表 `users`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 7.2 数据源表 `datasources`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | VARCHAR(100) | 数据源名称 |
| url | VARCHAR(500) | Zabbix URL |
| username | VARCHAR(100) | Zabbix 用户名 |
| password_encrypted | TEXT | AES-128 加密密码 |
| enabled | BOOLEAN | 是否启用 |
| last_connected_at | DATETIME | 最后连接时间 |
| zabbix_version | VARCHAR(20) | 检测到的 Zabbix 版本 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 7.3 告警规则表 `alert_rules`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 规则名称 |
| rule_type | ENUM | zabbix_trigger / custom_threshold |
| datasource_id | INTEGER FK | 关联数据源 |
| hostgroup_id | VARCHAR(50) | 主机组 ID，空=全部 |
| level | ENUM | INFO/WARNING/AVERAGE/HIGH/DISASTER |
| enabled | BOOLEAN | |
| config_json | TEXT | 规则详细配置（JSON），见下方 Schema |
| created_at | DATETIME | |

**`config_json` Schema 定义（P1 阶段）**：
```json
{
  "trigger_severity_min": 2,        // Zabbix 原生 trigger severity 下限（0-5）
                                    // 0=未分类, 1=信息, 2=警告, 3=一般严重, 4=严重, 5=灾难
                                    // 注意：这是 Zabbix trigger.priority 字段值，非本系统的 level_code
  "exclude_triggers": [],          // 排除的触发器名称关键词（数组）
  "notification_delay_seconds": 0, // 告警延迟发送秒数（0=立即）
  "recovery_notification": true     // 是否发送恢复通知
}
```

> **`trigger_severity_min` 说明**：此字段对应 Zabbix API `trigger.get` 返回的 `priority` 字段（0-5），与本系统告警记录中的 `level_code`（1-5）存在偏移关系。Zabbix `priority=0` 表示"未分类"（Not classified），在本系统中会被过滤掉（不生成告警）。`priority=1`（Information）映射为本系统 `level_code=1`（INFO），以此类推。

### 7.4 告警记录表 `alert_records`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| event_id | VARCHAR(50) UNIQUE | 去重用（Zabbix eventid） |
| host_id | VARCHAR(50) | |
| host_name | VARCHAR(200) | |
| trigger_name | VARCHAR(500) | |
| level | ENUM | |
| status | ENUM | active / recovered |
| value | VARCHAR(100) | 触发时的值 |
| first_occurred | DATETIME | 首次发生时间 |
| recovered_at | DATETIME | 恢复时间（可空） |
| webhook_pushed | BOOLEAN | 是否已推送 Webhook |
| created_at | DATETIME | |

### 7.5 Webhook 配置表 `webhook_configs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(100) | 端点名称 |
| url | VARCHAR(1000) | 推送 URL |
| method | ENUM | POST / PUT |
| headers_json | TEXT | 自定义请求头 JSON |
| trigger_levels | TEXT | 触发级别列表（逗号分隔） |
| hostgroup_ids | TEXT | 绑定主机组 ID（逗号分隔，空=全部） |
| enabled | BOOLEAN | |
| retry_count | INTEGER | 默认 3 |
| retry_interval | INTEGER | 默认 10（秒） |
| timeout | INTEGER | 默认 10（秒） |
| created_at | DATETIME | |

### 7.6 Webhook 推送日志表 `webhook_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| webhook_id | INTEGER FK | 关联配置 |
| alert_record_id | INTEGER FK | 关联告警记录 |
| event_id | VARCHAR(50) | 推送的事件 ID |
| status | ENUM | success / failed / retrying |
| http_status_code | INTEGER | HTTP 响应状态码 |
| retry_count | INTEGER | 已重试次数 |
| response_ms | INTEGER | 响应耗时（毫秒） |
| error_message | TEXT | 失败原因 |
| pushed_at | DATETIME | 推送时间 |

### 7.7 自定义大屏表 `dashboards`（P2）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 大屏名称 |
| description | TEXT | 描述 |
| layout_json | TEXT | 组件布局 JSON |
| background | VARCHAR(50) | 背景色/主题 |
| refresh_interval | INTEGER | 刷新间隔（秒） |
| is_carousel | BOOLEAN | 是否参与轮播 |
| carousel_order | INTEGER | 轮播顺序 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 7.7.1 大屏组件表 `dashboard_widgets`（P2）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| dashboard_id | INTEGER FK | 关联大屏 |
| widget_type | ENUM | stat_card / line_chart / bar_chart / pie_chart / gauge_chart / table / text / iframe |
| name | VARCHAR(100) | 组件名称 |
| position_x | INTEGER | X 坐标（像素） |
| position_y | INTEGER | Y 坐标（像素） |
| width | INTEGER | 宽度（像素） |
| height | INTEGER | 高度（像素） |
| config_json | TEXT | 组件配置（数据源、图表参数等） |
| sort_order | INTEGER | 排序序号 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**`widget_type` 组件类型说明**：

| 类型 | 说明 | config_json 关键字段 |
|------|------|---------------------|
| stat_card | 数值卡片 | `{ "value": 85, "unit": "%", "datasource": {...} }` |
| line_chart | 折线图 | `{ "item_key": "system.cpu.util", "time_range": "1h" }` |
| bar_chart | 柱状图 | `{ "items": [...], "orientation": "horizontal" }` |
| pie_chart | 饼图 | `{ "data": [...] }` |
| gauge_chart | 仪表盘 | `{ "value": 75, "min": 0, "max": 100 }` |
| table | 表格 | `{ "columns": [...], "data_source": "..." }` |
| text | 文本标签 | `{ "content": "标题文本", "font_size": 24 }` |
| iframe | 嵌入式网页 | `{ "url": "https://..." }` |

### 7.7.2 聚合缓存表 `monitor_cache`（P1）

> 调度器聚合结果写入此表，API worker 读取缓存而非直接调用 Zabbix API。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| cache_key | VARCHAR(100) UNIQUE | 缓存键，如 `summary_all`、`top_cpu_3`（3=datasource_id, 0=全部） |
| cache_type | VARCHAR(50) | 缓存类型：summary / hosts / top_cpu / top_memory / top_disk / top_network / alerts |
| datasource_id | INTEGER | 数据源 ID（NULL=聚合全部） |
| data_json | TEXT | 缓存数据 JSON |
| expires_at | DATETIME | 过期时间（当前时间 + 刷新间隔） |
| created_at | DATETIME | 创建时间 |

```sql
CREATE UNIQUE INDEX idx_monitor_cache_key ON monitor_cache(cache_key);
CREATE INDEX idx_monitor_cache_expires ON monitor_cache(expires_at);
```

### 7.8 系统设置表 `settings`

| 字段 | 类型 | 说明 |
|------|------|------|
| key | VARCHAR(100) PK | 配置键 |
| value | TEXT | 配置值 |
| updated_at | DATETIME | |

---

## 八、项目目录结构

```
zabbix-screen/                          # 项目根目录
├── docker-compose.yml                  # 生产部署（从 registry 拉取镜像）
├── docker-compose.dev.yml              # 开发环境（本地 build）
├── Dockerfile                          # multi-arch 单容器构建
├── docker-entrypoint.sh                # 容器启动脚本（DB 初始化 → 启动 supervisor）
├── supervisord.conf                    # Supervisor 进程管理配置（nginx + uvicorn + scheduler）
├── .env.example                        # 环境变量示例
├── README.md                           # 项目说明与快速开始
├── backend/
│   ├── requirements.txt                # Python 依赖（固定版本）
│   ├── main.py                         # FastAPI 入口（仅挂载路由，不初始化 scheduler）
│   ├── scheduler_main.py               # 调度器独立入口（由 supervisor 管理）
│   ├── config.py                       # 配置（从环境变量读取）
│   ├── database.py                     # SQLite 初始化 + WAL PRAGMA + 连接池配置
│   ├── alembic.ini                      # Alembic 迁移配置
│   ├── alembic/                         # 数据库迁移脚本
│   │   ├── env.py
│   │   └── versions/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── datasource.py
│   │   ├── dashboard.py
│   │   ├── dashboard_widget.py
│   │   ├── alert_rule.py
│   │   ├── alert_record.py
│   │   ├── webhook_config.py
│   │   ├── webhook_log.py
│   │   ├── monitor_cache.py             # 聚合数据缓存表（跨 worker 共享）
│   │   └── settings.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── datasource.py
│   │   ├── monitor.py
│   │   ├── host.py
│   │   ├── dashboard.py
│   │   ├── alert.py
│   │   ├── webhook.py
│   │   └── settings.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── zabbix_client.py             # Zabbix API 封装（含版本适配 + 超时控制）
│   │   ├── data_aggregator.py           # 大屏数据聚合（含主机去重）
│   │   ├── alert_engine.py              # 告警检测引擎（含告警风暴抑制）
│   │   ├── webhook_sender.py            # Webhook 推送（含批量和单条两种模式）
│   │   └── scheduler.py                 # APScheduler 定时任务配置
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth.py                      # JWT 生成/验证
│   │   ├── cache.py                     # 聚合数据缓存（SQLite 表 + 内存 TTL 双层）
│   │   └── crypto.py                    # AES-128-CBC 加密/解密（随机 IV）
│   └── tests/
│       ├── conftest.py                  # pytest fixtures（mock Zabbix API、测试 DB）
│       ├── test_zabbix_client.py
│       ├── test_data_aggregator.py
│       ├── test_alert_engine.py
│       └── test_webhook_sender.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/index.ts
│       ├── views/
│       │   ├── Login.vue
│       │   ├── Dashboard.vue
│       │   ├── DashboardList.vue        # P2
│       │   ├── DashboardEdit.vue        # P2
│       │   ├── DashboardView.vue        # P2
│       │   ├── HostList.vue
│       │   ├── HostDetail.vue
│       │   ├── AlertRules.vue
│       │   ├── AlertRecords.vue
│       │   ├── WebhookConfig.vue
│       │   └── Settings.vue
│       ├── components/
│       │   ├── charts/
│       │   │   ├── HostCard.vue
│       │   │   ├── CpuChart.vue
│       │   │   ├── MemChart.vue
│       │   │   ├── DiskChart.vue
│       │   │   ├── NetworkChart.vue
│       │   │   └── TopNChart.vue
│       │   ├── common/                   # 通用组件
│       │   │   ├── EmptyState.vue        # 空数据/异常状态占位
│       │   │   └── ErrorBoundary.vue     # 错误边界组件
│       │   ├── dashboard/               # P2
│       │   │   ├── WidgetPanel.vue
│       │   │   ├── Canvas.vue
│       │   │   ├── PropertyPanel.vue
│       │   │   └── widgets/
│       │   │       ├── StatCard.vue
│       │   │       ├── LineChart.vue
│       │   │       ├── BarChart.vue
│       │   │       ├── PieChart.vue
│       │   │       ├── GaugeChart.vue
│       │   │       ├── TableWidget.vue
│       │   │       ├── TextWidget.vue
│       │   │       └── IframeWidget.vue
│       │   └── layout/
│       │       ├── AppLayout.vue
│       │       ├── Sidebar.vue
│       │       └── Header.vue
│       ├── stores/
│       │   ├── auth.ts
│       │   ├── datasource.ts
│       │   ├── monitor.ts
│       │   ├── dashboard.ts             # P2，自定义大屏状态管理
│       │   └── settings.ts
│       ├── api/
│       │   ├── request.ts
│       │   ├── auth.ts
│       │   ├── datasource.ts
│       │   ├── monitor.ts
│       │   ├── host.ts
│       │   ├── dashboard.ts
│       │   ├── alert.ts
│       │   └── webhook.ts
│       ├── utils/
│       │   ├── format.ts
│       │   └── zabbix.ts
│       └── styles/
│           ├── global.css
│           └── dashboard.css
├── nginx/
│   ├── nginx.conf                       # 主配置（user appuser, pid 路径）
│   └── conf.d/
│       └── default.conf                 # 站点配置
├── scripts/
│   └── init_db.py                       # 数据库初始化脚本（建表+默认数据+admin 用户）
└── data/                                # Docker 挂载卷（运行时生成）
    └── zabbixscreen.db                  # SQLite 数据库文件
```

---

## 九、Docker 部署方案（multi-arch）

### 9.1 架构支持

| 架构 | 适用场景 |
|------|---------|
| `linux/amd64` | x86_64 服务器、云主机（主流） |
| `linux/arm64` | 鲲鹏服务器、飞腾 CPU、树莓派 4/5、Apple Silicon（Docker Desktop） |

### 9.2 Dockerfile（multi-arch 单容器）

```dockerfile
# syntax=docker/dockerfile:1

# ── 阶段 1：前端构建 ──────────────────────────────────────────
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --frozen-lockfile
COPY frontend/ ./
RUN npm run build

# ── 阶段 2：后端运行环境 ─────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Nginx + supervisor + 必要工具）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物
COPY --from=frontend-build /app/frontend/dist /app/static

# 复制 Nginx 配置（含 appuser 可写的日志路径）
COPY nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# 复制 supervisor 配置（nginx + uvicorn + scheduler 三个进程）
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制数据库初始化脚本
COPY scripts/ /app/scripts/

# 复制容器入口脚本
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 创建应用用户和数据/日志目录
RUN mkdir -p /app/data /app/logs /app/nginx/logs /app/nginx/run && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /var/lib/nginx && \
    chown -R appuser:appuser /var/log/supervisor && \
    chown appuser:appuser /run

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost/api/v1/health || exit 1

USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

**关键修正说明**：
- **nginx 日志路径**：容器内 nginx 的 error_log 和 access_log 指向 `/app/nginx/logs/`（appuser 可写），而非默认的 `/var/log/nginx/`
- **PID 文件**：nginx pid 指向 `/app/nginx/run/nginx.pid`
- **权限**：`/var/lib/nginx`、`/var/log/supervisor`、`/run` 均 chown 给 appuser
- **入口脚本**：`docker-entrypoint.sh` 在 supervisord 启动前执行数据库初始化

### 9.2.1 docker-entrypoint.sh（容器入口脚本）

```bash
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
    cd /app && alembic upgrade head || echo "[entrypoint] Migration skipped (alembic not configured)"
fi

echo "[entrypoint] Starting services via supervisord..."
exec "$@"
```

**supervisor 配置（supervisord.conf）**：
```ini
[supervisord]
nodaemon=true
logfile=/app/logs/supervisord.log
pidfile=/app/nginx/run/supervisord.pid
user=appuser

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/app/logs/nginx_stdout.log
stderr_logfile=/app/logs/nginx_stderr.log

[program:uvicorn]
command=uvicorn main:app --host 127.0.0.1 --port 5001 --workers 1
directory=/app
autostart=true
autorestart=true
stdout_logfile=/app/logs/uvicorn.log
stderr_logfile=/app/logs/uvicorn_err.log
; 注意：workers=1，不使用 uvicorn 多 worker
; 如需水平扩展，通过 supervisor numprocs 管理多个单 worker 进程：
; numprocs=2
; process_name=uvicorn_%(process_num)s

[program:scheduler]
command=python /app/scheduler_main.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/app/logs/scheduler.log
stderr_logfile=/app/logs/scheduler_err.log
; 调度器作为独立进程，不与 uvicorn worker 共享进程空间
; 避免多 worker 时 APScheduler 重复执行
```

> **架构要点**：
> - 使用 supervisor 代替简单 shell 脚本，实现三个进程（nginx、uvicorn、scheduler）的独立监控和自动重启
> - **uvicorn 使用 `--workers 1`**：多 worker 会导致 APScheduler 重复执行和内存缓存不共享。由 supervisor 的 `numprocs` 负责水平扩展
> - **scheduler 独立进程**：调度器（数据聚合、告警检测、数据清理）在独立进程中运行，通过 `scheduler_main.py` 启动
> - 聚合结果写入 SQLite 缓存表，API worker 读取缓存而非直接调用 Zabbix API

### 9.3 Nginx 配置（nginx/conf.d/default.conf）

```nginx
server {
    listen 80;
    server_name _;

    # 日志路径（appuser 可写）
    error_log /app/nginx/logs/error.log warn;
    access_log /app/nginx/logs/access.log;

    # 前端静态文件
    root /app/static;
    index index.html;

    # SPA 路由（Vue Router history 模式）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;
        proxy_read_timeout 60s;
    }

    # 关闭版本号暴露
    server_tokens off;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1024;
}
```

**nginx 主配置文件（nginx/nginx.conf）**：

```nginx
user appuser;
worker_processes auto;
pid /app/nginx/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    include /etc/nginx/conf.d/*.conf;
}
```

### 9.4 生产部署 docker-compose.yml

```yaml
version: '3.8'

services:
  zabbixscreen:
    image: your-registry/zabbixscreen:latest   # 替换为实际镜像地址
    container_name: zabbixscreen
    ports:
      - "8088:80"
    volumes:
      - ./data:/app/data          # SQLite 数据库持久化
      - ./logs:/app/logs          # 日志持久化
    environment:
      - TZ=Asia/Shanghai
      - APP_SECRET_KEY=your-secret-key-change-this   # 必须修改！
      - DEFAULT_REFRESH_INTERVAL=30
      - ALERT_CHECK_INTERVAL=60
      - DATA_RETENTION_DAYS=30
      - ZABBIX_REQUEST_TIMEOUT=25                    # Zabbix API 单次请求超时（秒）
      - AGGREGATION_TOTAL_TIMEOUT=28                  # 聚合总超时（秒）
      - WEBHOOK_REQUEST_TIMEOUT=10                    # Webhook 推送超时（秒）
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

networks:
  default:
    driver: bridge
```

### 9.5 开发环境 docker-compose.dev.yml

```yaml
version: '3.8'

services:
  zabbixscreen-dev:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: zabbixscreen-dev
    ports:
      - "8088:80"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backend:/app             # 代码热挂载（开发时）
    environment:
      - TZ=Asia/Shanghai
      - APP_SECRET_KEY=dev-secret-key
      - DEBUG=true
      - ZABBIX_REQUEST_TIMEOUT=30
      - AGGREGATION_TOTAL_TIMEOUT=30
    restart: no
```

### 9.6 multi-arch 镜像构建与推送

```bash
# 1. 确保 buildx 可用
docker buildx version

# 2. 创建 multi-arch builder（仅需一次）
docker buildx create --name multiarch-builder --use
docker buildx inspect --bootstrap

# 3. 构建并推送 amd64 + arm64 双架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag your-registry/zabbixscreen:1.0.0 \
  --tag your-registry/zabbixscreen:latest \
  --push \
  .

# 4. 验证镜像支持的架构
docker buildx imagetools inspect your-registry/zabbixscreen:latest
```

### 9.7 快速部署流程（生产）

```bash
# 1. 下载部署文件
git clone https://your-repo/zabbix-screen.git
cd zabbix-screen

# 2. 配置环境
cp .env.example .env
# 编辑 .env 修改 APP_SECRET_KEY 等必要配置

# 3. 创建数据目录
mkdir -p data logs

# 4. 启动服务
docker-compose up -d

# 5. 查看服务状态
docker-compose ps
docker-compose logs -f

# 6. 访问系统
# 浏览器：http://your-server:8088
# 默认账号：admin / admin123（首次登录后请立即修改密码）
```

---

### 4.5 运维门户集成模块

**4.5.1 功能概述**

从 ZBXScreen 统一入口一键跳转 Zabbix 前端和 iTop ITSM 系统，实现自动登录，无需二次输入凭据。

**4.5.2 自动登录机制**

两种策略适应不同目标系统：

| 系统 | 策略 | 实现 |
|------|------|------|
| Zabbix 前端 | 登录桥接页 | ZBXScreen 后端生成自动提交表单，POST 到 Zabbix `index.php`，Nginx 代理反代 |
| iTop ITSM | 直接 POST | 桥接页解析 iTop 原生表单字段（`auth_user`/`auth_pwd`），直接提交到 iTop 服务器 |

**4.5.3 Nginx 反代架构**

```
用户点击"运维监控系统"
  ↓
/integrations/zabbix/login → ZBXScreen 后端生成登录桥接页
  ↓
表单自动 POST → Nginx 代理 /integrations/zabbix/index.php → Zabbix 服务器
  ↓
Zabbix 认证 → 设置 zbx_session Cookie（Path 被 proxy_cookie_path 改写）
  ↓
已登录 Zabbix 前端
```

**4.5.4 侧边栏入口**

```
运维功能 ▾
  ├── 运维监控系统  → /integrations/zabbix/login（新标签页打开）
  └── 运维管理系统  → /integrations/itop/login（新标签页打开）
```

**4.5.5 配置项**

| 配置 | 存储位置 | 说明 |
|------|---------|------|
| Zabbix 数据源凭据 | `datasources` 表（AES 加密） | 容器启动时 entrypoint 自动配置 Nginx 代理 |
| iTop 地址/用户名/密码 | `settings` 表（密码 AES 加密） | 数据源页面 → 运维集成 Tab 配置 |

---

## 十、开发里程碑规划

### 已完成（v1.0 ~ v1.3）

| 版本 | 主要交付 |
|------|---------|
| **v1.0** | 项目脚手架 / 数据源管理 / 监控大屏 / 主机管理 / JWT 认证 / 告警+Webhook / 系统设置 / Docker 部署 |
| **v1.1** | 三层缓存 / 网络设备厂商识别 / 端口流量 / PUT→POST 迁移 / 离线部署包 |
| **v1.2** | 告警引擎重写（event_id 使用 Zabbix lastchange）/ 排序+时间显示修复 / 24h 趋势图 / 主机状态三态显示 / 复合 KPI 卡片 / Scheduler 健康端点 / 品牌统一 / 项目清理 |
| **v1.3** | 运维门户融合（Zabbix/iTop 自动登录）/ 侧边栏菜单重组 / 运维集成配置整合 / Docker 自动配置代理 / 安全加固 |

### 后续规划（P2）

| 阶段 | 内容 |
|------|------|
| P2-1 | 自定义大屏编辑器（拖拽组件 + 属性配置 + 保存/预览） |
| P2-2 | 大屏轮播（多大屏自动切换，配置轮播顺序和间隔） |
| P2-3 | 自定义大屏导入导出（JSON 格式） |
| P2-4 | Webhook 推送格式版本升级（增量字段，向下兼容） |

### 第三期（P3）— 可选增强

| 阶段 | 内容 |
|------|------|
| P3-1 | WebSocket 实时推送（替代前端轮询，降低延迟） |
| P3-2 | 地图告警展示（大屏嵌入中国地图，按省份标注告警主机） |
| P3-3 | 多用户权限管理（只读用户/管理员分离） |

---

## 十一、开发规范

### 11.1 通用规范

- **代码语言**：前端 TypeScript（严格模式），后端 Python 3.11+（类型注解）
- **分支策略**：`main`（生产）/ `develop`（集成）/ `feature/xxx`（功能分支）
- **提交规范**：`feat: 添加 Webhook 推送模块`、`fix: 修复主机卡片内存显示`、`docs: 更新 API 文档`
- **代码审查**：功能分支合并到 develop 需至少 1 人 Review

### 11.2 后端规范（Python/FastAPI）

```python
# 路由层（api/*.py）只做请求验证和响应封装
# 业务逻辑全部放到 services/ 层
# 数据库操作使用 async/await（aiosqlite）

# 统一响应格式
from fastapi.responses import JSONResponse

def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}

def error(code: int, message: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,  # 使用正确的 HTTP 状态码
        content={"code": code, "message": message, "data": None}
    )
```

- **HTTP 状态码规范**：
  - `200`：请求成功（含业务逻辑错误，如 Zabbix 连接失败）
  - `400`：客户端参数错误（请求参数缺失/格式错误）
  - `401`：未授权（Token 无效或过期）
  - `403`：禁止访问（无权限访问资源）
  - `404`：资源不存在
  - `500`：服务端内部错误

- **业务错误码约定**（在响应 body 的 code 字段中）：
  - `0` 成功
  - `1001` 参数错误
  - `1002` 未授权
  - `1003` 资源不存在
  - `2001` Zabbix 连接失败
  - `2002` Zabbix API 调用错误
  - `3001` Webhook 推送失败

- **密码加密**：用户密码 bcrypt，Zabbix 密码 AES-128-CBC（密钥来自 APP_SECRET_KEY）
- **日志规范**：使用 Python logging，区分 INFO/WARNING/ERROR 级别，告警相关日志标记 `[ALERT]`，Webhook 日志标记 `[WEBHOOK]`

### 11.3 前端规范（Vue 3/TypeScript）

- **API 调用**：统一通过 `src/api/` 封装，不允许在 Vue 组件内直接使用 Axios
- **状态管理**：跨组件状态使用 Pinia，组件内部状态用 `ref`/`reactive`
- **样式规范**：大屏背景色 `#0d1b2e`（深蓝），卡片背景 `#1a2a4a`，主色调 `#00d4ff`（科技蓝）
- **ECharts 使用**：统一封装为 Vue 组件，通过 props 传入数据，避免在页面组件中直接操作 DOM
- **响应式**：以 1920×1080 为基准，使用 `vw/vh` 和 `calc()` 适配其他分辨率

### 11.4 测试策略

**后端测试**（pytest + pytest-asyncio）：

| 测试类型 | 工具 | 覆盖目标 | 说明 |
|----------|------|---------|------|
| 单元测试 | pytest + pytest-asyncio | services/ 层核心逻辑 | Mock Zabbix API 响应，验证聚合/告警/Webhook 逻辑 |
| 集成测试 | pytest + httpx (AsyncClient) | api/ 层端到端 | 使用测试数据库（内存 SQLite），验证请求-响应完整性 |
| Mock 策略 | responses / aioresponses | 外部 Zabbix API | 不依赖真实 Zabbix 实例即可运行全部测试 |

```bash
# 运行后端测试
cd backend
pytest tests/ -v                          # 全部测试
pytest tests/test_zabbix_client.py -v    # 单个测试文件
pytest -k "test_aggregate" -v            # 按关键字筛选
pytest --cov=services tests/             # 覆盖率报告（目标 ≥80%）
```

**前端测试**（vitest + @vue/test-utils）：

| 测试类型 | 工具 | 覆盖目标 |
|----------|------|---------|
| 单元测试 | vitest | utils/ 格式化函数、Store actions、API 模块 |
| 组件测试 | @vue/test-utils + vitest | 关键图表组件（HostCard、TopNChart）、EmptyState 组件 |
| E2E（可选）| Playwright | 核心用户流程（登录 → 添加数据源 → 查看大屏） |

```bash
# 运行前端测试
cd frontend
npx vitest run                           # 全部测试
npx vitest run --reporter=verbose        # 详细输出
npx vitest run --coverage                # 覆盖率报告（目标 ≥70%）
```

**测试数据管理**：
- 测试数据库使用 SQLite 内存模式（`:memory:`），每次测试自动创建和销毁
- `conftest.py` 提供 mock Zabbix API fixture，返回固定响应数据
- 前端测试使用 MSW (Mock Service Worker) 拦截 API 请求

### 11.5 数据库迁移（Alembic）

> 所有数据库 schema 变更必须通过 Alembic 管理，禁止直接修改数据库。

```bash
# 初始化 Alembic（项目启动时执行一次）
cd backend
alembic init alembic

# 生成迁移脚本（自动检测模型变更）
alembic revision --autogenerate -m "add monitor_cache table"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

**迁移规则**：
- 迁移脚本纳入 Git，随代码一起提交
- 生产环境由 `docker-entrypoint.sh` 自动执行 `alembic upgrade head`
- P1→P2 新增 `dashboard_widgets` 表时，必须通过 Alembic 迁移而非重建数据库
- 迁移脚本需幂等（使用 `IF NOT EXISTS` 等安全策略）

### 11.6 日志规范

**日志级别使用**：

| 级别 | 使用场景 |
|------|---------|
| DEBUG | Zabbix API 请求/响应详情（开发环境） |
| INFO | 调度器定时任务、数据源连接状态变更、Webhook 推送结果 |
| WARNING | Zabbix API 调用超时、Webhook 重试、数据源响应慢 |
| ERROR | Zabbix 连接失败、Webhook 全部重试失败、数据库写入异常 |

**日志格式**（统一结构化）：

```python
# 格式：时间 | 级别 | 模块 | 请求ID | 消息
# 示例：
# 2026-06-01 10:00:30 | INFO | [SCHEDULER] | - | 数据聚合完成: 3数据源, 45主机, 耗时2.1s
# 2026-06-01 10:01:00 | INFO | [ALERT] | - | 检测到新告警: web-server-01 CPU>90%
# 2026-06-01 10:01:05 | INFO | [WEBHOOK] | - | 推送成功: http://ai-engine/webhook 200 156ms
# 2026-06-01 10:01:10 | WARNING | [WEBHOOK] | - | 推送重试(1/3): http://slow-endpoint 超时
```

**容器日志策略**：
- 所有进程（nginx、uvicorn、scheduler）的 stdout/stderr 由 supervisor 管理
- `docker-compose.yml` 中配置 `logging: driver: "json-file"` + `max-size: "10m"` + `max-file: "3"`
- 生产环境建议通过 Docker logging driver 接入外部日志收集系统（如 Loki、ELK）

### 11.7 环境变量（`.env` / docker-compose environment）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `APP_SECRET_KEY` | ✅ | 无 | JWT 签名密钥 + AES 密码加密密钥，**生产必须修改** |
| `DEFAULT_REFRESH_INTERVAL` | | 30 | 大屏默认刷新间隔（秒） |
| `ALERT_CHECK_INTERVAL` | | 60 | 告警检测间隔（秒） |
| `DATA_RETENTION_DAYS` | | 30 | 告警记录/Webhook 日志保留天数 |
| `ZABBIX_REQUEST_TIMEOUT` | | 25 | 单个 Zabbix API 请求超时（秒） |
| `AGGREGATION_TOTAL_TIMEOUT` | | 28 | 数据聚合总计超时（秒，需 > ZABBIX_REQUEST_TIMEOUT） |
| `WEBHOOK_REQUEST_TIMEOUT` | | 10 | Webhook HTTP 推送超时（秒） |
| `DEFAULT_ADMIN_PASSWORD` | | admin123 | 初始管理员密码，**首次登录后请修改** |
| `TZ` | | Asia/Shanghai | 时区 |
| `DEBUG` | | false | 开启 FastAPI debug 模式（开发环境用） |

---

## 十二、本地开发环境搭建

### 12.1 前置要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| Docker + Docker Compose | Docker 24+，Compose v2 | 容器化部署 |
| Docker Buildx | 0.11+ | multi-arch 构建（可选，发布时用） |
| Zabbix | 5.x / 6.x / 7.x | 数据源（需有一台可访问的 Zabbix） |

### 12.2 后端启动

```bash
# 1. 克隆项目
git clone https://your-repo/zabbix-screen.git
cd zabbix-screen

# 2. 创建 Python 虚拟环境
cd backend
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate            # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
mkdir -p ../data
python ../scripts/init_db.py

# 5. 启动后端（开发模式，自动热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 5001

# 访问 Swagger 文档：http://localhost:5001/docs
```

### 12.3 前端启动

```bash
# 在新终端
cd frontend

# 安装依赖
npm install

# 启动开发服务器（代理 /api/ 到后端 :5001）
npm run dev

# 访问：http://localhost:5173
```

**Vite 代理配置（vite.config.ts）**：
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      }
    }
  }
})
```

### 12.4 运行测试

```bash
# ── 后端测试 ──
cd backend
pytest tests/ -v                              # 全部测试（需要先 pip install pytest pytest-asyncio httpx）
pytest tests/test_zabbix_client.py -v         # 单个测试文件
pytest -k "test_aggregate" -v                 # 按关键字筛选
pytest --cov=services tests/ --cov-report=html  # 覆盖率报告

# ── 前端测试 ──
cd frontend
npx vitest run                                # 全部测试
npx vitest run src/utils/                     # 仅工具函数
npx vitest run --coverage                     # 覆盖率报告
```

### 12.5 一键 Docker 开发环境

```bash
# 使用 docker-compose.dev.yml 本地构建并运行
docker-compose -f docker-compose.dev.yml up --build

# 访问：http://localhost:8088
```

---

## 十三、规模边界与性能考量

### 13.1 适用规模边界

| 维度 | 推荐上限 | 超出后的建议 |
|------|---------|-------------|
| 监控主机数 | ≤500 台 | ≥500 台建议迁移到 PostgreSQL，分离调度器到独立服务 |
| Zabbix 数据源 | ≤10 个 | ≥10 个需调整并发策略和超时配置 |
| 日均告警量 | ≤500 条 | 超出后 SQLite WAL 写入可能成为瓶颈 |
| 并发大屏查看 | ≤20 用户 | API worker 1 个可支撑约 50 QPS（读缓存场景） |

### 13.2 性能关键路径

```
数据聚合（30s 周期）：
  并发拉取 Zabbix API ──→ asyncio.gather() ──→ 总超时 28s
  各数据源独立超时 25s，慢数据源自动跳过
  聚合计算 <500ms（500 台主机规模）
  写入缓存表 <100ms

API 请求（大屏数据）：
  读缓存表（SQLite）──→ <50ms（单表 <1000 行）
  无需调用 Zabbix API（已由调度器预聚合）

Webhook 推送：
  构建 payload（含 context 查询）──→ <200ms
  HTTP POST ──→ 取决于接收端响应速度（超时 10s）
  重试不影响主流程（asyncio.create_task 后台执行）
```

### 13.3 SQLite 调优配置

```python
# database.py — 生产环境推荐配置
PRAGMA journal_mode = WAL;           # 必须：并发读写
PRAGMA synchronous = NORMAL;         # 平衡安全与性能
PRAGMA cache_size = 10000;           # 10MB 页面缓存
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;          # 写入锁等待 5s（默认 0 即立即失败）
PRAGMA wal_autocheckpoint = 1000;    # WAL 文件超过 1000 页时自动 checkpoint
```

### 13.4 扩展路径（P2+ 考虑）

| 扩展方向 | 方案 |
|---------|------|
| 数据库升级 | SQLite → PostgreSQL（SQLAlchemy 仅需修改连接串） |
| 调度器扩展 | 调度器从单进程 → Celery + Redis（分布式任务队列） |
| 前端实时性 | 轮询 → WebSocket（P3-1 已规划） |
| API 水平扩展 | 单容器 → Nginx 负载均衡 + 多容器（k8s/Docker Swarm） |

---

## 附录 A：Zabbix 版本兼容详情

### A.1 各版本 API 差异

| 差异点 | Zabbix 5.x | Zabbix 6.x | Zabbix 7.x | 适配策略 |
|--------|-----------|-----------|-----------|---------|
| 认证流程 | `user.login` 返回 token | 同 5.x | `user.login` → 返回 token，建议后接 `user.checkAuthentication` 验证 | 7.x 检测到后追加 checkAuthentication 调用 |
| `trigger.get` `selectHosts` | 返回 `[{hostid, name}]` | 返回 `[{hostid, host, name}]` | 同 6.x | 统一提取 hostid → 再查 host.get 获取完整信息 |
| `history.get` 时间精度 | 秒级时间戳 | 秒级时间戳 | 支持纳秒时间戳（`time_from`/`time_till` 可传纳秒） | 统一使用秒级，忽略纳秒 |
| `item.get` `selectHosts` | 返回 `[{hostid, name}]` | 返回 `[{hostid, host, name}]` | 同 6.x | 响应解析时做兼容判断 |
| 趋势数据 API | `trend.get` | 同 5.x | 同 5.x | 统一使用，无差异 |
| API 版本号 | `apiinfo.version` 返回 `"5.x.x"` | 返回 `"6.x.x"` | 返回 `"7.x.x"` | 解析 major version 数字分流 |

### A.2 Zabbix Client 版本适配实现

```python
# services/zabbix_client.py
class ZabbixClient:
    async def _detect_version(self) -> int:
        """返回 Zabbix 主版本号（5/6/7）"""
        version_str = await self._call("apiinfo.version", {})
        return int(version_str.split(".")[0])

    async def authenticate(self):
        """版本自适应的认证流程"""
        token = await self._call("user.login", {
            "username": self.username,
            "password": self.password,
        })
        self._auth_token = token

        if await self._detect_version() >= 7:
            # 7.x 建议登录后验证 token 有效性
            await self._call("user.checkAuthentication", {
                "sessionid": token
            })
        return token
```

---

## 附录 B：大屏异常状态展示规范

| 异常场景 | 展示策略 |
|---------|---------|
| 所有数据源离线 | 大屏中央显示"暂无数据 — 所有数据源已离线"，显示最后更新时间，保留框架结构 |
| 部分数据源离线 | 顶部状态栏闪烁离线数据源名称（黄色警告图标），该数据源的主机卡片变灰并标注"离线" |
| 单个 Zabbix 响应超时 | 该数据源的数据保持上次缓存值，卡片右上角显示"数据延迟"标记（橙色圆点） |
| 主机已从 Zabbix 删除 | 在主机列表中标记"已移除"状态，下次聚合时自动清理 |
| 首次启动无数据 | 大屏图表区显示 EmptyState 占位组件（"正在连接数据源，请稍候..."），不显示空白/报错 |
| API 返回错误 | 图表组件捕获错误后渲染 ErrorBoundary，显示"数据加载失败，点击重试"按钮 |

---

## 附录 C：关键技术决策说明

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 数据库选型 | SQLite + WAL 模式 | 单机部署，数据量可控；WAL 模式解决并发读写；零额外服务 |
| 后端框架 | FastAPI + aiosqlite | 原生 async，适合并发 Zabbix API 调用；自带 Swagger 文档 |
| 前端框架 | Vue 3 + TypeScript | 类型安全；ECharts 集成成熟；Element Plus 组件丰富 |
| 容器架构 | 单容器（nginx + uvicorn） | 降低运维复杂度；部署简单；Supervisor 保证进程稳定 |
| 多架构支持 | Docker Buildx multi-arch | 用户环境包含 ARM（鲲鹏/飞腾）服务器；一次构建，多架构可用 |
| Webhook 格式 | 标准化 JSON Schema v1.0 | 为 AI 引擎对接预留；context 字段携带趋势数据，减少 AI 侧回调 |
| 是否保留 AI | 不保留，留 Webhook 出口 | 聚焦大屏展示；AI 分析由专用引擎承接；通过 Webhook 解耦 |
| 告警通知渠道 | 仅 Webhook | 精简复杂度；Webhook 可对接任意平台（企业微信/钉钉/AI引擎等） |

---

> 文档版本：v1.2 | 最后更新：2026-06-01
>
> 如有疑问或需要补充说明，请联系项目负责人。
