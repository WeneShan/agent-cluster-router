<div align="center">

# 🚦 Agent Cluster Router v5.5

**Multi-Agent Collaborative Gateway — Smart Routing · Eval System · Backend Abstraction · Security · Commander State Machine · Test Layering · Real Executor Integration**

[<kbd> <b>🇬🇧 English</b> </kbd>](#en) 
[<kbd> <b>🇨🇳 中文</b> </kbd>](#zh)

</div>

---

<div id="zh">

## 🇨🇳 中文

Agent Cluster Router 将多个 AI Agent 后端（Hermes、OpenClaw）编排为统一智能网关。**v5.0 新增评测体系、通用 Backend 抽象接口、安全可靠性体系、Commander 状态机**。

### v5.0 Release Notes

**已完成能力：**
- ✅ IntentClassifier 高准确率 (99.3%)
- ✅ 中/英文意图识别稳定
- ✅ dry_run eval 框架可跑，报告可复现
- ✅ Commander 状态机存在 (26/26 tests pass)
- ✅ Commander REST API 可用 (9/9 integration tests pass)
- ✅ 平均路由延迟极低 (2.3ms)

**版本演进：**

| 版本 | 功能 | 状态 |
|------|------|------|
| v5.0 | Eval 框架 + Backend 抽象 + 安全基础 + Commander 状态机 | ✅ |
| v5.1 | Skill-aware Backend Routing（9 Skill + L3 层） | ✅ |
| v5.2 | Security-aware Routing（L0 安全层，5 条规则） | ✅ |
| v5.3 | 测试分层 + CI 稳定性（pytest.ini + Makefile + E2E 隔离） | ✅ |
| v5.4 | Commander Continue 执行流（10 状态流转 + Executor 抽象 + FakeExecutor） | ✅ |
| v5.5 | Real Commander Executor Integration（Hermes plan/review → OpenClaw implement，env-switchable factory） | ✅ |

**Known Remaining Issues (2):**
| # | ID | 说明 | 类型 |
|---|-----|------|------|
| 1 | intent_023 | "这段代码的性能瓶颈在哪里？" → 误判为 chat | intent 边缘 case |
| 2 | edge_003 | "这个项目怎么优化？顺便帮我改一下代码" → 策略决策 | policy 边缘 case |

两者均为非阻塞，不影响主线功能。

### v5.5 新增：Real Commander Executor Integration

**真实执行器**：Commander continue 工作流可调用真实 AI 后端

| 角色 | 后端 | 说明 |
|------|------|------|
| plan | Hermes (:8081) | 架构设计 + 任务拆分 |
| implement | OpenClaw (:8082) | 代码实现 |
| review | Hermes (:8081) | 代码审查 |
| test | Hermes (:8081) | 测试检查 |

**环境变量控制**
```bash
COMMANDER_EXECUTOR=fake  # 默认，稳定快速无 AI 依赖
COMMANDER_EXECUTOR=real  # 调用真实 Hermes/OpenClaw
```

**新增文件**: `commander/real_executor.py`, `commander/executor_factory.py`, `commander/prompts.py`

### v5.4 新增：Commander Continue 执行流

**10 种状态流转**：planning → task_dispatched → implementing → (question_pending → user_decision_required →) reviewing → testing → accepted/rejected

| 新增 | 说明 |
|------|------|
| `CommanderExecutor` 抽象 | plan/implement/review/test 四个接口 |
| `FakeCommanderExecutor` | 可配置失败模式的测试执行器 |
| `continue_session()` | 推进 Commander 会话到下个状态 |
| `POST /commander/sessions/{id}/continue` | REST API 端点 |

### v5.3 新增：测试分层与 CI 稳定性

| 模块 | 说明 |
|------|------|
| **pytest.ini** | 注册 unit/integration/e2e/slow 标记，默认跳过 e2e |
| **Makefile** | `make test` / `make test-unit` / `make test-integration` / `make test-e2e` / `make eval` |
| **E2E 隔离** | 4 条 chat/session E2E 测试默认 skip（需 `SKIP_REAL_BACKEND=0`），4 条轻量 E2E 保留 |
| **测试标记** | 全量 183 测试已标记：119 unit + 18 integration + 8 e2e + 38 commander |

```bash
# 快速（默认）— unit + integration，<1 秒
make test

# 仅 unit 测试
make test-unit

# E2E（需要后端运行）
SKIP_REAL_BACKEND=0 make test-e2e

# 评测
make eval
```

### v5.0 新增

| 模块 | 说明 |
|------|------|
| **📊 评测体系 (P0)** | dry_run 路由、212+ 测试用例（意图/Skill/边界/回归）、run_eval.py 一键跑分 |
| **🔌 Backend 抽象 (P1)** | AgentBackend 统一接口，支持 Hermes/OpenClaw/HTTP Agent/CLI Agent 任意接入 |
| **🔒 安全体系 (P2)** | API Key 鉴权、user_id session 隔离、限流、消息大小限制、日志脱敏、熔断器 |
| **🤖 Commander 状态机 (P3)** | CommanderSession/Task 状态定义、合法流转验证、提问分流策略、REST API + 集成测试 |

### 最新评测结果 (v5.5)

| 指标 | 结果 | 状态 |
|------|------|------|
| Overall Accuracy | 237/239 (99.2%) | ✅ ≥ 95% |
| Intent Accuracy | 165/166 (99.4%) | ✅ ≥ 95% |
| Skill Routing Accuracy | 53/53 (100.0%) | ✅ ≥ 95% |
| Security Routing Accuracy | 16/16 (100.0%) | ✅ ≥ 90% |
| Core Backend Accuracy | 184/186 (98.9%) | ✅ ≥ 85% |
| Avg Latency | 2.0ms | ✅ ≤ 300ms |
| Unit Tests | 183/183 PASS | ✅ (8 e2e 按需跳过) |

### 核心功能

| 功能 | 说明 |
|------|------|
| **🧠 指挥官模式** | Hermes（架构师）↔ OpenClaw（工程师）多轮协作 |
| **🎯 七层决策路由** | L0: 安全 → L1: 手动 → L2: 标签 → L3: Skill → L4: 意图 → L5: 灰度 → L6: 兜底 |
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
| `POST` | `/commander/sessions/{id}/continue` | 推进 Commander 会话（v5.4+） |

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
│   ├── skill_registry.py        # Skill 注册与匹配（L3）
│   ├── security_policy.py       # 安全策略规则（L0）
│   ├── security_routing.py      # 安全路由决策（L0）
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
│   │   ├── intent_cases.yaml    # 166 条意图测试用例
│   │   ├── skill_cases.yaml     # 53 条 Skill 测试用例
│   │   ├── edge_cases.yaml      # 41 条边界测试用例
│   │   └── security_cases.yaml  # 20 条安全测试用例
│   ├── reports/                 # 评测报告
│   └── README.md
├── commander/                   # Commander 状态机 + 执行流 (P3)
│   ├── models.py                # CommanderState / CommanderTask / CommanderSession
│   ├── state_machine.py         # 状态流转规则和验证
│   ├── service.py               # Session 生命周期 + continue_session()
│   ├── executor.py              # CommanderExecutor 抽象基类 (v5.4)
│   ├── fake_executor.py         # 测试用假执行器 (v5.4)
│   ├── real_executor.py         # 真实执行器：Hermes plan/review → OpenClaw implement (v5.5)
│   ├── executor_factory.py      # COMMANDER_EXECUTOR 环境变量工厂 (v5.5)
│   ├── prompts.py               # plan/implement/review/test prompt 模板 (v5.5)
│   ├── api.py                   # Commander REST API
│   └── question_policy.yaml     # 提问分流策略
├── adapter/
│   ├── hermes_adapter.py        # Hermes CLI → HTTP
│   └── openclaw_adapter.py      # OpenClaw CLI → HTTP
├── scripts/
│   ├── hermes_cluster_router.py
│   └── hermes_commander.py
├── tests/                       # 测试（分层标记）
│   ├── conftest.py
│   ├── test_routing.py          # unit: 意图分类 + 路由引擎
│   ├── test_skill_registry.py   # unit: Skill 匹配
│   ├── test_security_routing.py # unit: 安全路由
│   ├── test_registry.py         # unit: 节点注册
│   ├── test_session.py          # unit: 会话管理
│   ├── test_commander_state_machine.py  # unit: 状态机
│   ├── test_commander_executor.py       # unit: 假执行器 (v5.4)
│   ├── test_commander_continue.py       # unit: 状态流转 (v5.4)
│   ├── test_commander_executor_factory.py # unit: 工厂 (v5.5)
│   ├── test_real_executor_contract.py     # unit: 真实执行器契约 (v5.5)
│   ├── test_commander_real_e2e.py         # e2e: 真实后端 (v5.5, 默认 skip)
│   ├── test_router_api.py       # integration: Router API
│   ├── test_commander_api.py    # integration: Commander API
│   └── test_e2e.py              # e2e: 端到端（默认跳过）
├── Makefile                     # 测试分层入口
└── pytest.ini                   # Pytest 配置 + 标记注册
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

**v5.5** · 评测体系 + Backend 抽象 + 安全框架 + Commander 状态机 + 测试分层 + 真实执行器集成 · [WeneShan/agent-cluster-router](https://github.com/WeneShan/agent-cluster-router)

</div>

<style>
#zh:target { display: block !important; }
#zh:target ~ #en { display: none; }
</style>
