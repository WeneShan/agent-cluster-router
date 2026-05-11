<div align="center">

# 🚦 Agent Cluster Router v4.0

**Multi-Agent Collaborative Gateway — Smart Routing · Commander Mode · Skill-Aware Delegation**

[<kbd> <b>🇬🇧 English</b> </kbd>](#en) 
[<kbd> <b>🇨🇳 中文</b> </kbd>](#zh)

</div>

---

<!-- Chinese content (hidden by default, shown when #zh is in URL) -->
<div id="zh" style="display:none">

## 🇨🇳 中文

Agent Cluster Router 将多个 AI Agent 后端（Hermes、OpenClaw）编排为统一智能网关。**v4 新增指挥官模式** — Hermes 设计架构，OpenClaw 编码实现，双向协作交互。同时配备**三层决策路由**和**Skill 感知委托**：当 OpenClaw 拥有相关技能时自动转交任务。

### 核心功能

| 功能 | 说明 |
|------|------|
| **🧠 指挥官模式** | Hermes（架构师）↔ OpenClaw（工程师）多轮协作。Hermes 设计方案，OpenClaw 编码实现，可随时提问，Hermes 审查迭代。 |
| **🎯 三层决策路由** | L1: 正则+skill匹配（0ms, 0 token）→ L2: Hermes LLM自主判断（~1s）→ L3: 直接询问 OpenClaw（兜底） |
| **🔧 Skill 感知路由** | 自动检测 OpenClaw 技能（天气、GitHub、音乐、邮件等）并路由任务。42+ 技能支持中文别名触发。 |
| **📋 意图路由** | 自动分类：代码/调试/重构 → OpenClaw，规划/搜索/闲聊 → Hermes |
| **⚖️ 负载均衡** | 加权随机 / 最少连接 / 轮询，运行时动态切换 |
| **💾 会话记忆** | 跨后端对话历史 — Hermes 设上下文，OpenClaw 查询，同一会话跨后端 |
| **📊 监控指标** | p50/p95/p99 延迟、按后端/意图分组统计 |
| **🩺 健康检查** | 每 30s 检查，自动剔除不健康节点 |
| **🚦 灰度发布** | 动态调整流量比例，平滑迁移 |

### 架构

```
┌─────────────────────────────────────────────────────┐
│                  Agent Cluster Router               │
│                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────┐ │
│  │ 三层决策      │   │ 指挥官协议    │   │ Skill   │ │
│  │ 引擎         │   │ (Hermes↔Claw)│   │ 索引    │ │
│  └──────┬───────┘   └──────┬───────┘   └────┬────┘ │
│         │                  │                 │      │
│         ▼                  ▼                 ▼      │
│  ┌──────────────────────────────────────────────┐   │
│  │              路由引擎                         │   │
│  │   加权 · 最少连接 · 轮询                       │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│         ┌───────────┴───────────┐                    │
│         ▼                       ▼                    │
│  ┌─────────────┐         ┌─────────────┐            │
│  │  OpenClaw   │         │   Hermes    │            │
│  │  (工程师)   │         │  (架构师)   │            │
│  └─────────────┘         └─────────────┘            │
└─────────────────────────────────────────────────────┘
```

### 快速开始

```bash
# 启动全部服务
bash /srv/agent-cluster/start.sh

# 健康检查
curl http://127.0.0.1:8000/health

# 聊天 — 自动路由（代码意图→OpenClaw）
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"写一个Python排序函数"}]}'

# 指挥官模式 — 协作会话
python3 scripts/hermes_commander.py --new-session "搭建博客系统"
python3 scripts/hermes_commander.py --send <id> "任务1：创建FastAPI项目结构..."
```

### 指挥官模式

Hermes 设计架构、拆分任务，OpenClaw 逐项实现，全程互动交流：

```
用户："帮我做一个完整的博客系统"
  │
  ├─ Hermes：设计架构 → 拆分为 6 个子任务
  │
  ├─ Hermes → OpenClaw："任务1：搭建 FastAPI 项目..."
  │   OpenClaw：交付代码，同时问："用异步还是同步路由？"
  │   Hermes 判断：架构决策 → 转发给用户
  │   用户选"异步" → Hermes 回传 OpenClaw
  │
  ├─ Hermes：验证通过 → "任务2：定义数据模型..."
  │
  └─ ... 循环直至全部完成
```

**提问分流规则：**

| Hermes 直接回答 | 转发给用户决策 |
|-----------------|---------------|
| "文件名用什么？" | "数据库用 SQLite 还是 PG？" |
| "加不加类型注解？" | "缓存用 Redis 还是内存？" |
| "f-string 还是 .format()？" | "前后端要不要拆成两个仓库？" |
| "保存到哪个路径？" | "认证用 JWT 还是 Session？" |

> **原则：犹豫一秒就转发。** 猜错的代价比多问一句大得多。

| 脚本 | 用途 |
|------|------|
| `scripts/hermes_commander.py` | 多轮协作协议（会话管理、提问检测、交付分析） |
| `scripts/hermes_cluster_router.py` | 意图分类 + 三层决策 + Skill索引 + 中文别名 |

### API 参考

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | Router 健康检查 |
| `GET` | `/status` | 集群状态 + 指标摘要 |
| `GET` | `/nodes` | 所有注册节点 |
| `POST` | `/chat` | 发送消息（`session_id`, `preferred`, `strategy`, `intent`） |
| `GET` | `/sessions` | 活跃会话列表 |
| `DELETE` | `/sessions/{id}` | 清除指定会话 |
| `GET` | `/metrics` | 完整指标快照 |
| `POST` | `/metrics/reset` | 重置计数 |
| `GET` | `/strategy` | 当前负载均衡策略 |
| `PUT` | `/strategy` | 切换策略（weighted/least_connections/round_robin） |

### 目录结构

```
agent-cluster-router/
├── config.yaml                  # 节点配置
├── start.sh / stop.sh           # 启停脚本
├── router/
│   ├── server.py                # FastAPI Router（主入口）
│   ├── routing.py               # 路由引擎 + 意图分类 + 委托决策
│   ├── registry.py              # 节点注册中心（YAML → 节点池）
│   ├── health.py                # 健康检查
│   └── metrics.py               # 指标收集器
├── adapter/
│   ├── hermes_adapter.py        # Hermes CLI → HTTP
│   └── openclaw_adapter.py      # OpenClaw CLI → HTTP
├── scripts/
│   ├── hermes_cluster_router.py # In-Hermes 路由（三层决策 + Skill索引 + 中文别名）
│   └── hermes_commander.py      # 指挥官协作协议
└── tests/                       # 61 个 pytest
```

### 技术栈

Python 3.11 · FastAPI · uvicorn · httpx · PyYAML · pytest (61/61 通过) · deepseek-v4-pro

</div>

<!-- English content (visible by default) -->
<div id="en">

## 🇬🇧 English

Agent Cluster Router orchestrates multiple AI agent backends (Hermes, OpenClaw) as a unified intelligent gateway. **v4 adds Commander Mode** — Hermes designs architecture, OpenClaw implements, with bidirectional collaboration. Also features **three-layer decision routing** and **skill-aware delegation**: automatically routes to OpenClaw when it has a relevant skill.

### Key Features

| Feature | Description |
|---------|-------------|
| **🧠 Commander Mode** | Hermes (Architect) ↔ OpenClaw (Engineer) multi-turn collaboration. Hermes designs, OpenClaw builds, asks questions, Hermes reviews and iterates. |
| **🎯 Three-Layer Routing** | L1: Regex + skill match (0ms, 0 token) → L2: Hermes LLM judgment (~1s) → L3: Ask OpenClaw directly (fallback) |
| **🔧 Skill-Aware Routing** | Auto-detects OpenClaw skills (weather, GitHub, Spotify, email, Notion, etc.) and routes tasks there. 42+ skills with Chinese aliases. |
| **📋 Intent Routing** | Auto-classify: code/debug/refactor → OpenClaw, plan/search/chat → Hermes |
| **⚖️ Load Balancing** | Weighted / least_connections / round_robin, runtime switchable |
| **💾 Session Memory** | Cross-backend conversation history — set context on Hermes, query OpenClaw |
| **📊 Metrics** | p50/p95/p99 latency, per-backend/intent breakdown |
| **🩺 Health Checks** | Auto-eject unhealthy nodes, 30s interval |
| **🚦 Canary Deploy** | Gradual traffic shift between backends |

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Agent Cluster Router               │
│                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────┐ │
│  │ 3-Layer      │   │ Commander    │   │ Skill   │ │
│  │ Decision     │   │ Protocol     │   │ Index   │ │
│  │ Engine       │   │ (Hermes↔Claw)│   │ (42 CN) │ │
│  └──────┬───────┘   └──────┬───────┘   └────┬────┘ │
│         │                  │                 │      │
│         ▼                  ▼                 ▼      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Routing Engine                   │   │
│  │   weighted · least_conn · round_robin        │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│         ┌───────────┴───────────┐                    │
│         ▼                       ▼                    │
│  ┌─────────────┐         ┌─────────────┐            │
│  │  OpenClaw   │         │   Hermes    │            │
│  │  (Engineer) │         │ (Architect) │            │
│  └─────────────┘         └─────────────┘            │
└─────────────────────────────────────────────────────┘
```

### Quick Start

```bash
# Start all services
bash /srv/agent-cluster/start.sh

# Health check
curl http://127.0.0.1:8000/health

# Chat — auto routing (code intent → OpenClaw)
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"write a Python function that sorts a list"}]}'

# Commander Mode — collaborative session
python3 scripts/hermes_commander.py --new-session "Build a blog system"
python3 scripts/hermes_commander.py --send <id> "Task 1: Create FastAPI project structure..."
```

### Commander Mode

Hermes designs the architecture, breaks work into subtasks, OpenClaw implements them with continuous Q&A:

```
User: "Build a complete blog system"
  │
  ├─ Hermes: Design architecture → 6 subtasks
  │
  ├─ Hermes → OpenClaw: "Task 1: Set up FastAPI project..."
  │   OpenClaw: delivers code + asks "Use async or sync routes?"
  │   Hermes judges: architectural decision → forwards to user
  │   User picks "async" → Hermes relays to OpenClaw
  │
  ├─ Hermes: validates → "Task 2: Define data models..."
  │
  └─ ... iterate until all tasks complete
```

**Question triage rules:**

| Hermes answers directly | Forward to user |
|------------------------|-----------------|
| "What filename?" | "SQLite or PostgreSQL?" |
| "Add type hints?" | "Redis or in-memory cache?" |
| "f-string or .format()?" | "Monorepo or separate repos?" |
| "Which file path?" | "JWT or session auth?" |

> **Rule of thumb: if you hesitate, forward it.** A forwarded question costs one round-trip. A wrong assumption costs a rewrite.

| Script | Purpose |
|--------|---------|
| `scripts/hermes_commander.py` | Multi-turn collaboration protocol (session mgmt, question detection, deliverable analysis) |
| `scripts/hermes_cluster_router.py` | Intent classification + 3-layer decision + skill index + CN aliases |

### API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Router health |
| `GET` | `/status` | Cluster status + metrics |
| `GET` | `/nodes` | All registered nodes |
| `POST` | `/chat` | Send message (`session_id`, `preferred`, `strategy`, `intent`) |
| `GET` | `/sessions` | Active sessions |
| `DELETE` | `/sessions/{id}` | Clear session |
| `GET` | `/metrics` | Full metrics snapshot |
| `POST` | `/metrics/reset` | Reset counters |
| `GET` | `/strategy` | Current LB strategy |
| `PUT` | `/strategy` | Switch strategy (weighted/least_connections/round_robin) |

### Directory Structure

```
agent-cluster-router/
├── config.yaml                  # Node configuration
├── start.sh / stop.sh           # Lifecycle
├── router/
│   ├── server.py                # FastAPI Router
│   ├── routing.py               # Routing engine + IntentClassifier + DelegationCheck
│   ├── registry.py              # Node registry (YAML → pools)
│   ├── health.py                # Health checker
│   └── metrics.py               # Metrics collector
├── adapter/
│   ├── hermes_adapter.py        # Hermes CLI → HTTP
│   └── openclaw_adapter.py      # OpenClaw CLI → HTTP
├── scripts/
│   ├── hermes_cluster_router.py # In-Hermes router (3-layer + skill index + CN aliases)
│   └── hermes_commander.py      # Commander collaboration protocol
└── tests/                       # 61 pytests
```

### Tech Stack

Python 3.11 · FastAPI · uvicorn · httpx · PyYAML · pytest (61/61 passing) · deepseek-v4-pro

</div>

<div align="center">

**v4.0** · Built with Hermes + OpenClaw · 61 tests passing · [WeneShan/agent-cluster-router](https://github.com/WeneShan/agent-cluster-router)

</div>

<style>
#zh:target { display: block !important; }
#zh:target ~ #en { display: none; }
</style>
