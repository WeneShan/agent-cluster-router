# Agent Cluster Router

> 混合 AI Agent 集群统一路由网关 | Multi-Agent Cluster Gateway

[English](#english) | [中文](#chinese)

---

## English

Agent Cluster Router is a unified entry point that orchestrates multiple AI agent backends (Hermes, OpenClaw) as a single logical cluster. It provides intelligent routing based on task intent, canary deployment control, load balancing, session memory across backends, and real-time metrics.

### Architecture

```
User → Router (:8000) ──→ OpenClaw Pool (:8082, :9082...)
                      ──→ Hermes Pool  (:8081, :9081...)
```

### Features

| Feature | Description |
|---------|-------------|
| **Intent Routing** | Auto-classify messages: code → OpenClaw, plan/search → Hermes |
| **Manual Routing** | `preferred=openclaw` or `preferred=hermes` |
| **Canary Deploy** | Gradual traffic shift via `PUT /canary {ratio, target}` |
| **Session Memory** | Cross-backend chat history — set context on Hermes, query on OpenClaw |
| **Load Balancing** | 3 strategies: weighted, least_connections, round_robin |
| **Health Checks** | Auto-eject unhealthy nodes after N failures |
| **Metrics** | p50/p95/p99 latency, per-backend/intent breakdown, recent errors |
| **In-Hermes Mode** | Hermes itself can classify intents and delegate code to OpenClaw |

### Quick Start

```bash
# Start all services
bash /srv/agent-cluster/start.sh

# Health check
curl http://127.0.0.1:8000/health

# Chat — auto routing
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"write a Python function that sorts a list"}]}'
# → routes to OpenClaw (code intent detected)

# Chat — manual routing
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"preferred":"hermes","messages":[{"role":"user","content":"what is Kubernetes?"}]}'
```

### API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Router health check |
| `GET` | `/status` | Cluster status + metrics summary |
| `GET` | `/nodes` | List all registered nodes |
| `POST` | `/chat` | Send message (supports `session_id`, `preferred`, `intent`) |
| `GET` | `/sessions` | List active sessions |
| `DELETE` | `/sessions/{id}` | Clear a session |
| `GET` | `/metrics` | Full metrics snapshot |
| `POST` | `/metrics/reset` | Reset all counters |
| `GET` | `/canary` | View canary config |
| `PUT` | `/canary` | Set canary ratio and target |
| `GET` | `/strategy` | View load balancing strategy |
| `PUT` | `/strategy` | Switch strategy (weighted/least_connections/round_robin) |

### In-Hermes Mode

From within Hermes CLI, classify and route without the Router:

```bash
# Classify intent
python3 ~/.hermes/scripts/hermes_cluster_router.py --classify-only "write a function"
# → {"intent": "code", "backend_hint": "openclaw"}

# Full route (classify + call OpenClaw)
python3 ~/.hermes/scripts/hermes_cluster_router.py "write a Python function to reverse a string"
```

### Tech Stack

- Python 3.11, FastAPI, uvicorn, httpx, PyYAML
- OpenClaw (Node.js) via subprocess adapter
- Hermes CLI via subprocess adapter
- 61 unit tests (pytest), all passing

### Directory Structure

```
/srv/agent-cluster/
├── config.yaml              # Cluster node configuration
├── start.sh / stop.sh       # Lifecycle scripts
├── router/
│   ├── server.py            # FastAPI Router (main entry)
│   ├── models.py            # Internal request/response protocol
│   ├── registry.py          # Node registry (YAML → pools)
│   ├── routing.py           # Routing engine + IntentClassifier
│   ├── health.py            # Background health checker
│   └── metrics.py           # Metrics collector (latency, rates, errors)
├── adapter/
│   ├── hermes_adapter.py    # Hermes CLI → HTTP wrapper
│   └── openclaw_adapter.py  # OpenClaw CLI → HTTP wrapper
└── tests/                   # 61 pytests (session, routing, registry, API, LB)
```

---

## 中文

Agent Cluster Router 是一个统一入口网关，将多个 AI Agent 后端（Hermes、OpenClaw）编排为单一逻辑集群。提供基于任务意图的智能路由、灰度发布控制、负载均衡、跨后端会话记忆和实时监控。

### 架构

```
用户 → Router (:8000) ──→ OpenClaw 池 (:8082, :9082...)
                      ──→ Hermes 池  (:8081, :9081...)
```

### 功能

| 功能 | 说明 |
|------|------|
| **意图路由** | 自动分类消息：代码 → OpenClaw，计划/搜索 → Hermes |
| **手动路由** | `preferred=openclaw` 或 `preferred=hermes` |
| **灰度发布** | 通过 `PUT /canary` 动态调整流量比例 |
| **会话记忆** | 跨后端聊天历史 — Hermes 设上下文，OpenClaw 读取 |
| **负载均衡** | 3 种策略：加权随机、最少连接、轮询 |
| **健康检查** | 连续失败 N 次后自动剔除节点 |
| **监控面板** | p50/p95/p99 延迟，按后端/意图分组，最近错误 |
| **Hermes 内模式** | Hermes 自身可直接分类意图并委托代码任务给 OpenClaw |

### 快速开始

```bash
# 启动全部服务
bash /srv/agent-cluster/start.sh

# 健康检查
curl http://127.0.0.1:8000/health

# 聊天 — 自动路由
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"写一个Python函数来排序列表"}]}'
# → 自动路由到 OpenClaw（检测到代码意图）

# 聊天 — 手动路由
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"preferred":"hermes","messages":[{"role":"user","content":"Kubernetes是什么？"}]}'
```

### API 参考

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | Router 健康检查 |
| `GET` | `/status` | 集群状态 + 指标摘要 |
| `GET` | `/nodes` | 列出所有注册节点 |
| `POST` | `/chat` | 发送消息（支持 `session_id`、`preferred`、`intent`） |
| `GET` | `/sessions` | 列出活跃会话 |
| `DELETE` | `/sessions/{id}` | 清除指定会话 |
| `GET` | `/metrics` | 完整指标快照 |
| `POST` | `/metrics/reset` | 重置所有计数 |
| `GET` | `/canary` | 查看灰度配置 |
| `PUT` | `/canary` | 设置灰度比例和目标 |
| `GET` | `/strategy` | 查看负载均衡策略 |
| `PUT` | `/strategy` | 切换策略（weighted/least_connections/round_robin） |

### Hermes 内模式

在 Hermes CLI 中直接使用，无需通过 Router：

```bash
# 分类意图
python3 ~/.hermes/scripts/hermes_cluster_router.py --classify-only "写一个函数"
# → {"intent": "code", "backend_hint": "openclaw"}

# 完整路由（分类 + 调用 OpenClaw）
python3 ~/.hermes/scripts/hermes_cluster_router.py "写一个Python函数来反转字符串"
```

### 技术栈

- Python 3.11, FastAPI, uvicorn, httpx, PyYAML
- OpenClaw (Node.js) 通过子进程适配器
- Hermes CLI 通过子进程适配器
- 61 个单元测试 (pytest)，全部通过

### 目录结构

```
/srv/agent-cluster/
├── config.yaml              # 集群节点配置
├── start.sh / stop.sh       # 启停脚本
├── router/
│   ├── server.py            # FastAPI Router（主入口）
│   ├── models.py            # 内部请求/响应协议
│   ├── registry.py          # 节点注册中心（YAML → 节点池）
│   ├── routing.py           # 路由引擎 + 意图分类器
│   ├── health.py            # 后台健康检查
│   └── metrics.py           # 指标收集器（延迟、成功率、错误）
├── adapter/
│   ├── hermes_adapter.py    # Hermes CLI → HTTP 封装
│   └── openclaw_adapter.py  # OpenClaw CLI → HTTP 封装
└── tests/                   # 61 个 pytest（会话、路由、注册中心、API、负载均衡）
```

---

*Built with Hermes Agent + OpenClaw · 61 tests passing · deepseek-v4-pro*
