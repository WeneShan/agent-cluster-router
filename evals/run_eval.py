#!/usr/bin/env python3
"""Agent Cluster Router 评测脚本 — 一键跑所有测试用例 (v5.1: Skill Routing 拆分)"""
import yaml
import time
import requests
import sys
from collections import defaultdict
from pathlib import Path

ROUTER_URL = "http://127.0.0.1:8000/chat"
CASE_DIR = Path(__file__).parent / "cases"


def load_cases(path: Path) -> list:
    """加载 YAML 测试用例"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def eval_case(case: dict, verbose: bool = False) -> dict:
    """评测单个用例"""
    start = time.time()
    try:
        resp = requests.post(
            ROUTER_URL,
            json={
                "messages": [{"role": "user", "content": case["input"]}],
                "dry_run": True,
            },
            timeout=10,
        )
        latency_ms = (time.time() - start) * 1000
        data = resp.json()

        result = {
            "id": case["id"],
            "input": case["input"][:80],
            "expected_backend": case.get("expected_backend"),
            "actual_backend": data.get("selected_backend"),
            "expected_intent": case.get("expected_intent"),
            "actual_intent": data.get("intent"),
            "expected_skill": case.get("expected_skill"),
            "actual_skill": data.get("matched_skill"),
            "expected_security_action": case.get("expected_security_action"),
            "actual_security_action": data.get("security_action"),
            "decision_layer": data.get("decision_layer"),
            "latency_ms": round(latency_ms, 1),
            "status": resp.status_code,
        }

        # 判断通过
        backend_match = (result["actual_backend"] == result["expected_backend"])
        intent_match = True
        if result["expected_intent"]:
            intent_match = result["actual_intent"] == result["expected_intent"]
        # Skill 匹配
        skill_match = True
        if result["expected_skill"]:
            skill_match = result["actual_skill"] == result["expected_skill"]
        # Security action 匹配
        security_match = True
        if result["expected_security_action"]:
            security_match = result["actual_security_action"] == result["expected_security_action"]
        result["pass"] = backend_match and intent_match and skill_match and security_match

        return result

    except requests.ConnectionError:
        return {
            "id": case["id"],
            "input": case["input"][:80],
            "expected_backend": case.get("expected_backend"),
            "actual_backend": None,
            "expected_intent": case.get("expected_intent"),
            "actual_intent": None,
            "expected_skill": case.get("expected_skill"),
            "actual_skill": None,
            "expected_security_action": case.get("expected_security_action"),
            "actual_security_action": None,
            "decision_layer": None,
            "latency_ms": 0,
            "status": "CONNECTION_ERROR",
            "pass": False,
        }
    except Exception as e:
        return {
            "id": case["id"],
            "input": case["input"][:80],
            "expected_backend": case.get("expected_backend"),
            "actual_backend": None,
            "expected_intent": case.get("expected_intent"),
            "actual_intent": None,
            "expected_skill": case.get("expected_skill"),
            "actual_skill": None,
            "expected_security_action": case.get("expected_security_action"),
            "actual_security_action": None,
            "decision_layer": None,
            "latency_ms": 0,
            "status": f"ERROR: {str(e)[:50]}",
            "pass": False,
        }


def main():
    files = [
        CASE_DIR / "intent_cases.yaml",
        CASE_DIR / "skill_cases.yaml",
        CASE_DIR / "edge_cases.yaml",
        CASE_DIR / "security_cases.yaml",
    ]

    # 检查文件存在
    for f in files:
        if not f.exists():
            print(f"[WARN] {f} not found, skipping")

    all_results = []

    for file in files:
        if not file.exists():
            continue
        print(f"\n{'='*60}")
        print(f"Running: {file.name}")
        print(f"{'='*60}")
        cases = load_cases(file)
        for case in cases:
            result = eval_case(case)
            all_results.append(result)
            status = "PASS" if result["pass"] else "FAIL"
            # Show fails and errors
            if not result["pass"]:
                extra = ""
                if result.get("expected_skill"):
                    extra += f" skill: {result['expected_skill']}->{result.get('actual_skill')}"
                print(f"  [{status}] {result['id']}: '{result['input']}'")
                print(f"         expected={result['expected_backend']} actual={result['actual_backend']}"
                      f" intent: {result['expected_intent']}->{result['actual_intent']}{extra}")

    # 统计
    total = len(all_results)
    if total == 0:
        print("\nNo test cases found!")
        return

    passed = sum(1 for r in all_results if r["pass"])
    connection_errors = sum(1 for r in all_results if r["status"] == "CONNECTION_ERROR")

    # 按层统计
    layer_hits = defaultdict(int)
    for r in all_results:
        if r.get("decision_layer"):
            layer_hits[r["decision_layer"]] += 1

    # 意图准确率
    intent_total = sum(1 for r in all_results if r["expected_intent"])
    intent_correct = sum(1 for r in all_results
                         if r["expected_intent"] and r["actual_intent"] == r["expected_intent"])

    # Skill Routing 准确率 (only cases with expected_skill)
    skill_total = sum(1 for r in all_results if r.get("expected_skill"))
    skill_correct = sum(1 for r in all_results
                        if r.get("expected_skill") and r.get("actual_skill") == r["expected_skill"])

    # Security Routing 准确率 (only cases with expected_security_action)
    security_total = sum(1 for r in all_results if r.get("expected_security_action"))
    security_correct = sum(1 for r in all_results
                           if r.get("expected_security_action")
                           and r.get("actual_security_action") == r["expected_security_action"])

    # Core Backend Accuracy (cases WITHOUT expected_skill)
    core_cases = [r for r in all_results if not r.get("expected_skill")
                  and r["status"] != "CONNECTION_ERROR"]
    core_total = len(core_cases)
    core_passed = sum(1 for r in core_cases if r["pass"])

    # 延迟统计
    latencies = [r["latency_ms"] for r in all_results if r["latency_ms"] > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    valid_total = total - connection_errors

    print(f"\n{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total cases:              {total}")
    print(f"Passed:                   {passed}")
    print(f"Failed:                   {total - passed - connection_errors}")
    print(f"Connection err:           {connection_errors}")
    print(f"\nCore Backend Accuracy:     {core_passed}/{core_total} = "
          f"{core_passed/core_total*100:.1f}%" if core_total else "Core Backend Accuracy: N/A")
    print(f"Skill Routing Accuracy:    {skill_correct}/{skill_total} = "
          f"{skill_correct/skill_total*100:.1f}%" if skill_total else "Skill Routing Accuracy: N/A")
    print(f"Security Routing Accuracy: {security_correct}/{security_total} = "
          f"{security_correct/security_total*100:.1f}%" if security_total else "Security Routing Accuracy: N/A")
    print(f"Overall Accuracy:          {passed}/{valid_total} = "
          f"{passed/valid_total*100:.1f}%" if valid_total else "Overall Accuracy: N/A")
    if intent_total > 0:
        print(f"Intent Accuracy:           {intent_correct}/{intent_total} = "
              f"{intent_correct/intent_total*100:.1f}%")
    print(f"\nAvg latency:               {avg_latency:.1f}ms")
    print(f"\nDecision layer hits:")
    layer_order = ["L0_SECURITY", "L1_MANUAL", "L2_TAG", "L3_SKILL", "L4_INTENT", "L5_CANARY", "L6_DEFAULT"]
    for layer in layer_order:
        count = layer_hits.get(layer, 0)
        bar = "#" * min(count, 50)
        print(f"  {layer:15s}: {count:3d} {bar}")

    # 失败案例详情
    failed = [r for r in all_results if not r["pass"] and r["status"] != "CONNECTION_ERROR"]
    if failed:
        print(f"\nFailed cases detail ({len(failed)}):")
        for r in failed:
            extra = ""
            if r.get("expected_skill"):
                extra = f" skill: {r['expected_skill']}->{r.get('actual_skill')}"
            print(f"  [{r['id']}] expected={r['expected_backend']} actual={r['actual_backend']}"
                  f" intent: {r['expected_intent']}->{r['actual_intent']}"
                  f" layer={r['decision_layer']}{extra}")
            print(f"        input: {r['input']}")

    # 准出标准检查
    print(f"\n{'='*60}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'='*60}")
    if valid_total > 0:
        overall_acc = passed / valid_total * 100
        checks = [
            ("Intent Accuracy >= 95%",
             intent_correct / intent_total * 100 >= 95 if intent_total else False),
            ("Skill Routing Accuracy >= 95%",
             skill_correct / skill_total * 100 >= 95 if skill_total else False),
            ("Security Routing Accuracy >= 90%",
             security_correct / security_total * 100 >= 90 if security_total else False),
            ("Core Backend Accuracy >= 85%",
             core_passed / core_total * 100 >= 85 if core_total else False),
            ("Overall Backend Accuracy >= 95%", overall_acc >= 95),
            ("Avg Latency <= 300ms", avg_latency <= 300),
        ]
        for desc, ok in checks:
            print(f"  {'[PASS]' if ok else '[FAIL]'} {desc}")


if __name__ == "__main__":
    main()
