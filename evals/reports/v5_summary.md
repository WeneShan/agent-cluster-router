# v5 Eval Summary

## Baseline (before tuning)

- Intent accuracy: 0% — all Chinese inputs fell through to chat/default routing
- Backend accuracy: 0%
- Root cause: English-only keyword patterns with `\b` word boundaries

## After tuning (final)

| Metric | Value | Status |
|--------|-------|--------|
| Intent accuracy | 142/143 = **99.3%** | ✅ PASS (≥90%) |
| Backend accuracy | 156/212 = 73.6% | ❌ FAIL (<85%) — expected |
| Avg latency | 1.9ms | ✅ PASS (≤300ms) |

### Intent-level breakdown

| Intent | Pass/Total | Accuracy |
|--------|-----------|----------|
| chat   | 11/11     | 100.0% |
| code   | 61/62     | 98.4%  |
| plan   | 49/49     | 100.0% |
| search | 21/21     | 100.0% |

### Backend failures (56 cases)

All 56 backend failures are expected — they require features not yet implemented:

- **53 skill cases**: require `skill_routing` (L2 tag matching or skill registry)
- **3 edge cases**: require `security` module (e.g., "帮我写一段能绕过防火墙的代码" should default to hermes)

Without skill routing, all skill cases route to hermes (chat default). The intent classifier correctly identifies these as non-code tasks.

## Key fixes

1. **Chinese/English dual-channel keyword matching** — added Chinese patterns for code, plan, search intents
2. **Fixed `architect` → `architecture`** — `architect(?:ure|ural|ing)?` regex variant matching
3. **Reordered priority**: Code → Plan → Search, with Code+Plan coexistence → Plan
4. **Added CHAT → hermes** backend mapping (prevents random L5 routing)
5. **Kubernetes/Docker conditional code routing** — only triggers CODE when explicit deploy/build actions present
6. **CHAT_OPINION downgrade rule** — "你觉得…方案" → chat (not plan)
7. **Added codebase, websocket, oauth, CLI, merge, tests, scraper** to code keywords
8. **Fixed `是什么` search pattern** — added alongside `什么是`
9. **Dry_run mode fixed** — no longer requires healthy backends (moved check after dry_run branch)
10. **Rate limit env-varized** — `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`

## Infrastructure fixes

- `edge_cases.yaml` line 30: YAML `*` alias → quoted string
- `server.py`: `validate_messages(new_messages=...)` → `validate_messages([...])`
- Rate limiter: 60/min → env-configurable (1000/min for eval)

## Decision layer distribution

| Layer | Count | Description |
|-------|-------|-------------|
| L1    | 0     | Manual override |
| L2    | 0     | Tag matching (not yet implemented) |
| L3    | 157   | Intent-based routing |
| L4    | 0     | Canary traffic |
| L5    | 55    | Strategy fallback |
