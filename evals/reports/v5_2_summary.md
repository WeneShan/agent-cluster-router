# v5.2 Security-aware Routing Summary

## Final Results

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Intent Accuracy | 165/166 = 99.4% | ≥95% | ✅ |
| Skill Routing Accuracy | 53/53 = 100.0% | ≥95% | ✅ |
| Security Routing Accuracy | 16/16 = 100.0% | ≥90% | ✅ |
| Core Backend Accuracy | 184/186 = 98.9% | ≥85% | ✅ |
| Overall Accuracy | 237/239 = 99.2% | ≥95% | ✅ |
| Avg Latency | 2.2ms | ≤300ms | ✅ |

## Unit Tests

- test_security_routing.py: 29/29 ✅
- test_skill_registry.py: passed ✅
- test_routing.py: passed ✅
- Total: 74/74 ✅

## New Features

### L0 Security Routing Layer
Highest priority — runs before all other routing layers. Cannot be overridden.

### Security Rules (5)
| Rule | Action | Examples |
|------|--------|----------|
| credential_theft | REVIEW | API key, token, secret |
| bypass_security | BLOCK | bypass firewall, hack into server, 绕过防火墙 |
| destructive_command | CONFIRM | rm -rf, drop database, production delete, 部署命令 |
| harmful_code | BLOCK | malware, virus, 木马, 病毒 |
| saas_without_review | REVIEW | build me a SaaS product |

### Safety Actions
- **BLOCK**: `selected_backend=null`, request rejected
- **CONFIRM**: routes to hermes, requires user confirmation
- **REVIEW**: routes to hermes, flagged for security review

## Known Remaining Failures (2)
1. intent_023: "这段代码的性能瓶颈在哪里？" — classifier edge case (code→chat)
2. edge_003: "这个项目怎么优化？顺便帮我改一下代码" — policy decision

Both are non-security, non-skill issues.

## Files Added
- `router/security_policy.py`
- `router/security_routing.py`
- `evals/cases/security_cases.yaml`
- `tests/test_security_routing.py`

## Files Modified
- `router/routing.py` — L0 integration, security_action field
- `router/server.py` — security_action in API response, intent="security"
- `evals/run_eval.py` — Security Routing Accuracy, acceptance criteria
- `evals/cases/edge_cases.yaml` — edge_014/033 blocked expectations

## Next Step
v5.3: 测试分层与 CI 稳定性
