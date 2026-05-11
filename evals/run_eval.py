#!/usr/bin/env python3
"""Agent Cluster Router 评测脚本 — 一键跑所有测试用例"""
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
            "decision_layer": data.get("decision_layer"),
            "latency_ms": round(latency_ms, 1),
            "status": resp.status_code,
        }

        # 判断通过
        backend_match = result["actual_backend"] == result["expected_backend"]
        intent_match = True
        if result["expected_intent"]:
            intent_match = result["actual_intent"] == result["expected_intent"]
        result["pass"] = backend_match and intent_match

        return result

    except requests.ConnectionError:
        return {
            "id": case["id"],
            "input": case["input"][:80],
            "expected_backend": case.get("expected_backend"),
            "actual_backend": None,
            "expected_intent": case.get("expected_intent"),
            "actual_intent": None,
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
            "latency_ms": 0,
            "status": f"ERROR: {str(e)[:50]}",
            "pass": False,
        }


def main():
    files = [
        CASE_DIR / "intent_cases.yaml",
        CASE_DIR / "skill_cases.yaml",
        CASE_DIR / "edge_cases.yaml",
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
            # 只打印失败或所有
            if not result["pass"]:
                print(f"  [{status}] {result['id']}: '{result['input']}'")
                print(f"         expected={result['expected_backend']} actual={result['actual_backend']} "
                      f"intent: {result['expected_intent']}→{result['actual_intent']}")

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
        if r["decision_layer"]:
            layer_hits[r["decision_layer"]] += 1

    # 意图准确率
    intent_total = sum(1 for r in all_results if r["expected_intent"])
    intent_correct = sum(1 for r in all_results if r["expected_intent"] and r["actual_intent"] == r["expected_intent"])

    # 延迟统计
    latencies = [r["latency_ms"] for r in all_results if r["latency_ms"] > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print(f"\n{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total cases:     {total}")
    print(f"Passed:          {passed}")
    print(f"Failed:          {total - passed - connection_errors}")
    print(f"Connection err:  {connection_errors}")
    print(f"\nBackend Accuracy: {passed}/{total-connection_errors} = {passed/(total-connection_errors)*100:.1f}%"
          if total > connection_errors else "Backend Accuracy: N/A (no connection)")
    if intent_total > 0:
        print(f"Intent Accuracy:   {intent_correct}/{intent_total} = {intent_correct/intent_total*100:.1f}%")
    print(f"\nAvg latency:      {avg_latency:.1f}ms")
    print(f"\nDecision layer hits:")
    for layer in ["L1", "L2", "L3", "L4", "L5"]:
        count = layer_hits.get(layer, 0)
        bar = "█" * min(count, 50)
        print(f"  {layer}: {count:3d} {bar}")

    # 按 intent 分拆准确率
    print(f"\nIntent-level accuracy:")
    intent_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in all_results:
        if r["expected_intent"]:
            intent_stats[r["expected_intent"]]["total"] += 1
            if r["actual_intent"] == r["expected_intent"]:
                intent_stats[r["expected_intent"]]["correct"] += 1
    for intent, stats in sorted(intent_stats.items()):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {intent:10s}: {stats['correct']:3d}/{stats['total']:3d} = {acc:.1f}%")

    # 失败案例详情
    failed = [r for r in all_results if not r["pass"] and r["status"] != "CONNECTION_ERROR"]
    if failed:
        print(f"\nFailed cases detail ({len(failed)}):")
        for r in failed:
            print(f"  [{r['id']}] expected={r['expected_backend']} actual={r['actual_backend']} "
                  f"intent: {r['expected_intent']}→{r['actual_intent']} layer={r['decision_layer']}")
            print(f"        input: {r['input']}")

    # 准出标准检查
    print(f"\n{'='*60}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'='*60}")
    if total > connection_errors:
        accuracy = passed / (total - connection_errors) * 100
        checks = [
            ("Intent accuracy >= 90%", intent_correct / intent_total * 100 >= 90 if intent_total else False),
            ("Backend accuracy >= 85%", accuracy >= 85),
            ("Avg latency <= 300ms", avg_latency <= 300),
        ]
        for desc, ok in checks:
            print(f"  {'[PASS]' if ok else '[FAIL]'} {desc}")


if __name__ == "__main__":
    main()
