<div align="center">

# 🚦 Agent Cluster Router v5.0

**Multi-Agent Collaborative Gateway — Smart Routing · Eval System · Backend Abstraction · Security · Commander State Machine**

[<kbd> <b>🇬🇧 English</b> </kbd>](#en) 
[<kbd> <b>🇨🇳 中文</b> </kbd>](#zh)

</div>

---

<div id="zh">

## 🇨🇳 中文

Agent Cluster Router 将多个 AI Agent 后端（Hermes、OpenClaw）编排为统一智能网关。**v5.0 新增评测体系、通用 Backend 抽象接口、安全可靠性体系、Commander 状态机**。

### v5.0 新增

| 模块 | 说明 |
|------|------|
| **📊 评测体系 (P0)** | dry_run 路由、212+ 测试用例（意图/Skill/边界/回归）、run_eval.py 一键跑分 |
| **🔌 Backend 抽象 (P1)** | AgentBackend 统一接口，支持 Hermes/OpenClaw/HTTP Agent/CLI Agent 任意接入 |
| **🔒 安全体系 (P2)** | API Key 鉴权、user_id session 隔离、限流、消息大小限制、日志脱敏、熔断器 |
| **🤖 Commander 状态机 (P3)** | CommanderSession/Task 状态定义、合法流转验证、提问分流策略、REST API + 集成测试 |

### 最新评测结果 (v5 final)

| 指标 | 结果 | 状态 |
|------|------|------|
| Intent Accuracy | 149/150 (99.3%) | ✅ ≥ 90% |
| Backend Accuracy | 163/219 (74.4%) | ⚠️ Skill 路由层待追加 |
| Avg Latency | 2.3ms | ✅ ≤ 300ms |
| Unit Tests | 94/96 PASS | ✅ (2 条 canary 历史遗留) |

### 核心功能

| 功能 | 说明 |
|------|------|
| **🧠 指挥官模式** | Hermes（架构师）↔ OpenClaw（工程师）多轮协作 |
| **🎯 五层决策路由** | L1: 手动指定 → L2: 标签匹配 → L3: 意图路由 → L4: 灰度 → L5: 策略兜底 |
| **🔧 Skill 感知路由** | 自动检测 OpenClaw 技能（天气、GitHub、音乐、邮件等）并路由 |
| **📋 意图路由** | 代码/调试/重构 → OpenClaw，规划/搜索/闲聊 → Hermes |
| **⚖️ 负载均衡** | 加权随机 / 最少连接 / 轮询，运行时动态切换 |
| **💾 会话记忆** | 跨后端对话历史，user_id 隔离 |
| **📊 监控指标** | p50/p95/p99 延迟、按后端/意图分组统计 |
| **🩺 健康检查** | 自动剔除不健康节点 |

### 快速开始

```bash
# 启动全部服务
bash /srv/agent-cluster/start.sh

# 健康检查
curl http://127.0.0.1:8000/health

# 聊天 — 自动路由
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"写一个Python排序函数"}]}'

# dry_run 路由评测（不调用后端）
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"帮我设计系统架构"}],"dry_run":true}'

# 运行评测
pip install pyyaml requests
python3 evals/run_eval.py
```

### API 参考

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | Router 健康检查 |
| `GET` | `/status` | 集群状态 + 指标摘要 |
| `GET` | `/nodes` | 所有注册节点 |
| `POST` | `/chat` | 发送消息（支持 `dry_run`, `user_id`, `session_id`） |
| `GET` | `/sessions` | 活跃会话列表 |
| `DELETE` | `/sessions/{id}` | 清除指定会话 |
| `GET` | `/metrics` | 完整指标快照 |
|| `POST` | `/metrics/reset` | 重置计数 |
|| `GET` | `/strategy` | 当前负载均衡策略 |
|| `PUT` | `/strategy` | 切换策略 |
|| **Commander API** | | |
|| `POST` | `/commander/sessions` | 创建 Commander 会话 |
|| `GET` | `/commander/sessions/{id}` | 查询会话（user_id 隔离） |
|| `GET` | `/commander/sessions/{id}/tasks` | 查询任务列表 |
|| `POST` | `/commander/sessions/{id}/answer` | 提交用户决策 |

### 鉴权

```bash
# 可选：启用 API Key 鉴权
export AGENT_ROUTER_API_KEY="your-secret-key"
# 请求时携带
curl -H "X-API-Key: your-secret-key" ...
```

### 目录结构

```
agent-cluster-router/
├── config.yaml                  # 统一配置（Backend + 安全 + Commander）
├── start.sh / stop.sh           # 启停脚本
├── router/
│   ├── server.py                # FastAPI Router（主入口，dry_run + 鉴权 + 限流）
│   ├── routing.py               # 路由引擎 + 意图分类
│   ├── registry.py              # 节点注册中心
│   ├── health.py                # 健康检查
│   ├── metrics.py               # 指标收集器
│   ├── security.py              # API Key 鉴权 + 脱敏 + 消息验证 (P2)
│   ├── rate_limit.py            # 内存限流器 (P2)
│   ├── errors.py                # 统一错误 + 重试 + 熔断器 (P2)
│   ├── middleware.py            # 请求大小限制 (P2)
│   └── backends/                # Backend 抽象接口 (P1)
│       ├── base.py              # AgentBackend 基类
│       ├── hermes.py            # HermesBackend
│       ├── openclaw.py          # OpenClawBackend
│       ├── http_agent.py        # HttpAgentBackend
│       └── cli_agent.py         # CliAgentBackend
├── evals/                       # 评测体系 (P0)
│   ├── run_eval.py              # 一键评测脚本
│   ├── cases/
│   │   ├── intent_cases.yaml    # 125 条意图测试用例
│   │   ├── skill_cases.yaml     # 53 条 Skill 测试用例
│   │   └── edge_cases.yaml      # 34 条边界测试用例
│   └── README.md
├── commander/                   # Commander 状态机 (P3)
│   ├── models.py                # CommanderState / CommanderTask / CommanderSession
│   ├── state_machine.py         # 状态流转规则和验证
│   ├── service.py               # Session 生命周期管理
│   ├── prompts.py               # 提示词模板
│   └── question_policy.yaml     # 提问分流策略
├── adapter/
│   ├── hermes_adapter.py        # Hermes CLI → HTTP
│   └── openclaw_adapter.py      # OpenClaw CLI → HTTP
├── scripts/
│   ├── hermes_cluster_router.py
│   └── hermes_commander.py
└── tests/
```

### 技术栈

Python 3.11 · FastAPI · uvicorn · httpx · PyYAML · pytest · deepseek-v4-pro

</div>

<div id="en">

## 🇬🇧 English

Agent Cluster Router orchestrates multiple AI agent backends (Hermes, OpenClaw) as a unified intelligent gateway. **v5.0 adds evaluation system, generic Backend abstraction, security framework, and Commander state machine**.

### v5.0 New

| Module | Description |
|--------|-------------|
| **📊 Eval System (P0)** | dry_run routing, 180+ test cases (intent/skill/edge), run_eval.py one-click scoring |
| **🔌 Backend Abstraction (P1)** | AgentBackend interface, pluggable Hermes/OpenClaw/HTTP Agent/CLI Agent |
| **🔒 Security (P2)** | API Key auth, user_id session isolation, rate limiting, message validation, log redaction, circuit breaker |
| **🤖 Commander State Machine (P3)** | CommanderSession/Task states, transition validation, question triage policy, acceptance criteria |

### Quick Start

```bash
# Start all services
bash /srv/agent-cluster/start.sh

# dry_run eval
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"design a system architecture"}],"dry_run":true}'

# Run evaluation suite
pip install pyyaml requests
python3 evals/run_eval.py
```

### Tech Stack

Python 3.11 · FastAPI · uvicorn · httpx · PyYAML · pytest · deepseek-v4-pro

</div>

<div align="center">

**v5.0** · 评测体系 + Backend 抽象 + 安全框架 + Commander 状态机 · [WeneShan/agent-cluster-router](https://github.com/WeneShan/agent-cluster-router)

</div>

<style>
#zh:target { display: block !important; }
#zh:target ~ #en { display: none; }
</style>
