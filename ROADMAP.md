# ZBXScreen 发展路线图

> 版本：v1.0 | 日期：2026-07-20 | 基于 v1.3 现状制定

---

## 一、当前版本概况（v1.3）

### 已完成功能

| 模块 | 功能 |
|------|------|
| 监控大屏 | 数据中心大屏 / 网络监控大屏 / 告警大屏，30s 自动刷新，TOP N 排行，状态饼图，24h 告警趋势 |
| 主机管理 | 主机列表（在线/离线/停用三态）、主机详情（指标卡片 + 趋势图 + 触发器列表） |
| 告警管理 | 告警规则、告警记录、告警统计、Webhook 推送、告警风暴抑制 |
| 运维门户 | Zabbix/iTop 一键跳转 + 自动登录，侧边栏"运维功能"子菜单 |
| 数据源 | Zabbix 多实例接入，密码 AES 加密，运维集成配置 |
| 安全 | JWT 认证、Nginx 安全头+速率限制、iTop 密码加密、URL 协议校验 |
| 部署 | Docker 单容器（Supervisor: Nginx + Uvicorn + Scheduler），amd64/arm64 多架构 |

### 当前技术债务

| 项目 | 说明 | 影响 |
|------|------|------|
| 测试覆盖不足 | `backend/tests/` 仅 test_auth/test_datasource 两个文件，前端零单测 | 回归风险高 |
| 无 CI/CD | 无 GitHub Actions、无 lint、无 pre-commit hook | 代码质量靠人工保障 |
| 版本号硬编码 | `backend/main.py`、`webhook_sender.py`、`frontend/package.json` 多处需手动同步 | 发布时容易遗漏 |
| API version 字段 | `/api/v1/health` 返回的 version 字符串需手动更新 | 同版本号问题 |

---

## 二、发展路线

### Phase 1：夯实基础（1-2 个月）

#### 1.1 测试与 CI/CD

**目标**：建立自动化质量保障体系

| 任务 | 说明 |
|------|------|
| 后端单测 | 核心模块：alert_engine、data_aggregator、webhook_sender，使用 pytest + pytest-asyncio |
| 前端单测 | Dashboard/HostDetail/AlertDetail 关键组件，vitest + @vue/test-utils |
| GitHub Actions | 推送触发：backend pytest + frontend vue-tsc + vite build |
| pre-commit | lint-staged + ESLint + black/formatter |

**验收**：PR 合并前自动跑测试，核心模块覆盖率 ≥ 60%

#### 1.2 后端版本号集中管理

**目标**：单一版本源，一处修改全局生效

- 在 `backend/config.py` 定义 `APP_VERSION = "1.3.0"`
- `main.py`、`webhook_sender.py`、`webhook.py` 统一引用 `settings.app_version`
- `frontend/package.json` 在 CI 中与后端版本对齐

---

### Phase 2：功能增强（2-4 个月）

#### 2.1 单主机大屏

**目标**：为单个主机提供专属大屏视图，适合运维中心轮播展示重点设备

| 功能点 | 说明 |
|--------|------|
| 指标全景 | CPU/内存/磁盘/网络的实时值 + 24h 趋势图整合到一屏 |
| 触发器时间线 | 该主机所有告警的时间线视图（产生→恢复→Webhook 推送） |
| TOP 进程 | 通过 Zabbix `proc.cpu.util` / `proc.mem.util` 获取（需主机配置对应 item） |
| 网络接口详情 | 各接口流量趋势 + 错误计数，自动发现活跃接口 |
| 全屏轮播 | 可配置多个重点主机的独立大屏，自动轮播切换 |

**设计原则**：
- 复用 `backend/api/host.py` 现有接口，优先从 `monitor_cache` 读取
- 前端新建 `HostDashboard.vue`，独立路由 `/hosts/:id/dashboard`
- 顶栏增加"大屏模式"按钮切换

#### 2.2 告警确认与处理工作流

**目标**：形成告警闭环，当前"确认告警"按钮是空操作

| 状态 | 触发条件 | 可操作 |
|------|---------|--------|
| 活跃（active） | Zabbix trigger → PROBLEM | 确认 / 创建工单 |
| 已确认（acknowledged） | 用户手动确认 | 关闭 / 创建工单 |
| 已恢复（recovered） | Zabbix trigger → OK | 归档 |
| 已关闭（closed） | 用户手动关闭 | 归档 |

- AlertRecord 增加 `acknowledged_by` / `acknowledged_at` / `closed_by` / `closed_at`
- 增加操作日志表 `alert_actions`

#### 2.3 iTop 工单闭环

**目标**：从告警记录页直接创建 iTop 工单，回写工单号

- 调用 iTop REST API（`/webservices/rest.php`）创建 UserRequest
- 工单号回写到 AlertRecord
- 告警记录列表显示关联工单号，点击跳转 iTop

---

### Phase 3：体验优化（3-6 个月）

#### 3.1 仪表盘自定义

- 大屏组件化：每块面板（KPI 卡片、TOP N、趋势图、告警列表）作为独立组件
- 用户可拖拽调整布局，添加/删除/缩放面板
- 配置持久化到 `settings` 表（JSON 字段）

#### 3.2 报表与周期报告

- 日报/周报模板：主机可用率、告警统计、TOP N 变化
- 输出格式：PDF（服务端渲染）+ Excel CSV
- 推送方式：邮件 / Webhook（对接企业微信群机器人）

#### 3.3 多 Zabbix 实例分权

- 用户-数据源绑定表 `user_datasource_access`
- 非 admin 用户只能看到已授权的数据源
- 超级管理员可查看全部

---

### Phase 4：平台化（6-12 个月）

#### 4.1 运维门户扩展

框架已就绪（Nginx 反代 + 登录桥接页），接入新系统只需：

1. 分析目标系统登录表单字段
2. 在 `backend/api/integrations.py` 新增桥接端点
3. 在 `nginx/conf.d/integrations.conf` 增加反代规则

建议接入的系统：

| 系统 | 用途 | 登录方式 |
|------|------|---------|
| JumpServer | 堡垒机 | Form POST |
| Grafana | 可视化 | OAuth / Auth Proxy |
| ELK | 日志分析 | Basic Auth |

#### 4.2 告警降噪与根因分析

- 时间窗口内同主机多触发器合并为一条聚合告警
- 父子告警关联（如交换机故障 → 下游主机不可达）
- 告警建议：匹配历史告警处理方案的相似度

#### 4.3 移动端适配

- 大屏页面已用 vw/vh 响应式，移动端基本可用
- 管理页面（Settings、Datasource、AlertRules）需独立移动端布局
- 可考虑移动端轻量 PWA 版本

---

## 三、技术架构演进方向

### 不变的部分

- SQLite + 单容器部署（核心设计决策，保持简洁）
- FastAPI + Vue 3 技术栈
- APScheduler 独立进程调度
- GET/POST only API 约定（客户现场 WAF 兼容）

### 可演进的部分

| 当前 | 未来可考虑 | 触发条件 |
|------|-----------|---------|
| 内存缓存 + SQLite 缓存表 | Redis 缓存层 | 多实例部署或缓存命中率成为瓶颈 |
| 单容器 Supervisor | docker-compose 多服务 | 需要独立扩缩容时 |
| settings 表 KV 存储 | JSON 配置文件 | 配置项超过 20 个 |
| 无前端状态持久化 | localStorage / IndexedDB | 用户个性化配置需求增加 |

---

## 四、给新开发者的上手路径

### 第一周：理解系统

1. 阅读 [项目设计方案](项目设计方案-ZabbixScreen-v1.1.md) 第 1-4 章
2. 搭建本地开发环境（见 README.md 开发环境章节）
3. 访问 `http://localhost:5001/docs` 浏览所有 API
4. 运行 `scripts/init_db.py` 初始化数据库，添加一个测试数据源
5. 理解数据流：scheduler → monitor_cache → API → 前端 Dashboard

### 第二周：小任务

建议从以下任一任务开始熟悉代码：

- 修复一个 Low 优先级的 bug（见 CLAUDE.md 审计报告）
- 给 `backend/utils/cache.py` 添加单元测试
- 给一个前端组件添加 loading/error 状态处理

### 持续参与

- 提交前运行 `cd backend && python -m pytest tests/ -v`
- 提交前运行 `cd frontend && npm run build` 确认构建通过
- Commit message 格式：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:`
- 参考 CLAUDE.md 中的项目约束（GET/POST only、HTTP 方法限制、APP_SECRET_KEY 注意事项）
