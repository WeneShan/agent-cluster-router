# Agent Cluster Router — 评测体系

## 概述

评测体系用于验证 Router 的路由决策是否准确、稳定、低成本。通过 `dry_run` 模式，不实际调用后端 Agent，仅测试路由决策。

## 目录结构

```
evals/
├── cases/
│   ├── intent_cases.yaml    # 意图分类测试用例 (100+)
│   ├── skill_cases.yaml     # Skill 路由测试用例 (50+)
│   └── edge_cases.yaml      # 边界测试用例 (30+)
├── run_eval.py              # 一键评测脚本
└── README.md                # 本文档
```

## 使用方法

### 1. 启动 Router

```bash
cd /srv/agent-cluster
bash start.sh
```

### 2. 安装依赖

```bash
pip install pyyaml requests
```

### 3. 运行评测

```bash
cd /srv/agent-cluster
python3 evals/run_eval.py
```

## 评测指标

- **Backend Accuracy**: 路由到正确后端的比例
- **Intent Accuracy**: 意图分类准确率
- **Average Latency**: 平均路由延迟（不含 Agent 执行）
- **L1-L5 Hit Rate**: 各决策层命中比例

## 验收标准

| 指标 | 目标 |
|------|------|
| Intent routing accuracy | >= 90% |
| Backend routing accuracy | >= 85% |
| L1 hit rate | >= 50% |
| Avg routing latency | <= 300ms |

## 添加新用例

在对应的 YAML 文件中添加用例：

```yaml
- id: intent_999
  input: "你的测试输入"
  expected_intent: "code"       # code | plan | search | chat
  expected_backend: "openclaw"   # openclaw | hermes
```
