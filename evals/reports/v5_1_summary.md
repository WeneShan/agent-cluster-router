# v5.1 Skill Routing Summary

## Final Results

| Metric | Score | Status |
|--------|-------|--------|
| Skill Routing Accuracy | 53/53 = 100.0% | ✅ |
| Core Backend Accuracy | 159/166 = 95.8% | ✅ |
| Overall Accuracy | 212/219 = 96.8% | ✅ |
| Intent Accuracy | 149/150 = 99.3% | ✅ |
| Avg Latency | 2.1ms | ✅ |

## Key Fixes

1. **ASCII word boundaries** — 给 ASCII alias 增加 `\b` 边界，避免 `repo` 匹配 `monorepo`、`search` 匹配 `research` 等误命中
2. **Expanded weather aliases** — 新增：空气质量、台风、紫外线、多少度、湿度、雾霾、沙尘暴、暴雨、雷暴、冰雹、humidity、pollution、storm、hurricane、tsunami
3. **Expanded web_search aliases** — 新增：找一下、帮我找、搜一下、找资料、search for、look up、documentation、docs；移除裸 `search` 和 `搜索引擎`
4. **Narrowed Hermes planning** — 移除过宽的"设计""策略""规划""算法"，改为"架构设计""方案设计""project plan""计划书"等具体短语
5. **Updated test expectations** — 更新 11 条 intent_cases.yaml 和 edge_cases.yaml 期望值，适配新的 skill layer 捕获逻辑

## Known Remaining Failures (7)

| # | Case | Issue | Plan |
|---|------|-------|------|
| 1 | intent_023: "这段代码的性能瓶颈在哪里？" | Classifier 把"性能瓶颈"识别为 chat 而非 code | v5.2 轻量修复 |
| 6 | edge_*: hack、bypass firewall、API key、build SaaS 等 | 正确路由到 CODE→OpenClaw，但缺少安全策略层 | v5.2 Security-aware Routing |

## Decision

Skill Routing 已完成，冻结 v5.1。下一步进入 **v5.2 Security-aware Routing**。
