#!/usr/bin/env python3
"""
Hermes Commander — 多轮协作协议
Hermes (指挥官/架构师) ↔ OpenClaw (工程师/执行者)

用法:
  # 开始新会话
  python3 hermes_commander.py --new-session "任务描述"
  # → 返回 session_id

  # 发送消息到 OpenClaw
  python3 hermes_commander.py --send <session_id> "消息内容"
  # → 返回 OpenClaw 的回复 + 分析 (是否有提问/是否交付)

  # 用 stdin 发送多行消息
  echo "消息" | python3 hermes_commander.py --send <session_id>

  # 获取会话历史
  python3 hermes_commander.py --history <session_id>

  # 查看会话状态
  python3 hermes_commander.py --status <session_id>

协议标记 (OpenClaw 回复中用自然语言检测):
  - 提问检测: 问号结尾 / "怎么" / "哪个" / "What" / "How"
  - 交付检测: 代码块 / "完成" / "done" / "写好了"
"""

import sys
import json
import re
import time
import os
import urllib.request
import urllib.error
from pathlib import Path

ADAPTER_URL = "http://127.0.0.1:8082/chat"
STATE_DIR = Path(os.path.expanduser("~/.hermes/commander"))
STATE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
#  Session Management
# ============================================================

def session_path(session_id: str) -> Path:
    return STATE_DIR / f"{session_id}.json"


def load_session(session_id: str) -> dict:
    if session_path(session_id).exists():
        return json.loads(session_path(session_id).read_text())
    return {"session_id": session_id, "messages": [], "tasks": [], "created_at": time.time()}


def save_session(session: dict):
    session["updated_at"] = time.time()
    session_path(session["session_id"]).write_text(json.dumps(session, ensure_ascii=False, indent=2))


# ============================================================
#  OpenClaw Communication
# ============================================================

def send_to_openclaw(session_id: str, message: str, timeout: int = 120) -> dict:
    """发送消息到 OpenClaw adapter，返回完整响应"""
    session = load_session(session_id)

    payload = json.dumps({
        "messages": [{"role": "user", "content": message}],
        "session_id": session_id,
        "timeout_ms": timeout * 1000,
    }).encode()

    try:
        req = urllib.request.Request(ADAPTER_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())

        # 记录到会话
        session["messages"].append({"role": "hermes", "content": message, "ts": time.time()})
        session["messages"].append({
            "role": "openclaw",
            "content": data.get("content", ""),
            "success": data.get("success", False),
            "tokens": data.get("tokens_used", 0),
            "ts": time.time(),
        })
        save_session(session)

        return {
            "success": data.get("success", False),
            "content": data.get("content", ""),
            "tokens": data.get("tokens_used", 0),
            "elapsed_ms": data.get("elapsed_ms", 0),
        }
    except urllib.error.URLError as e:
        err_msg = f"OpenClaw adapter unreachable: {e}"
        session["messages"].append({"role": "system", "content": err_msg, "ts": time.time()})
        save_session(session)
        return {"success": False, "content": err_msg, "tokens": 0}
    except Exception as e:
        return {"success": False, "content": str(e), "tokens": 0}


# ============================================================
#  Response Analysis
# ============================================================

QUESTION_PATTERNS = [
    r'\?$', r'？$',
    r'\b(which|what|how|should I|do you want|prefer)\b',
    r'(请问|怎么|如何|哪个|哪种|要不要|需不需要|是不是)',
]

DELIVERABLE_PATTERNS = [
    r'```',  # code block
    r'\b(done|完成|写好了|做好了|搞定了|以上是|下面是|创建了|生成了)\b',
    r"\b(here's|here is|this is|I've created|I created)\b",
]

REVIEW_REQUEST_PATTERNS = [
    r'\b(review|检查|看看|审阅|verify|check|confirm|look good)\b',
    r'(这样.*可以吗|这样.*行吗|需要.*调整吗)',
]


def analyze_response(text: str) -> dict:
    """分析 OpenClaw 回复：是否有提问、是否交付、是否请求审查"""
    t = text.lower()

    has_question = any(re.search(p, t) for p in QUESTION_PATTERNS)
    has_deliverable = any(re.search(p, t) for p in DELIVERABLE_PATTERNS)
    needs_review = any(re.search(p, t.lower()) for p in REVIEW_REQUEST_PATTERNS)

    # 提取问题
    questions = []
    if has_question:
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if re.search(r'[?？]$', stripped) and len(stripped) > 3:
                questions.append(stripped)

    return {
        "has_question": has_question,
        "has_deliverable": has_deliverable,
        "needs_review": needs_review,
        "questions": questions[:5],
        "summary": text[:200].replace('\n', ' ') + ("..." if len(text) > 200 else ""),
    }


# ============================================================
#  CLI
# ============================================================

def main():
    args = sys.argv[1:]

    if not args:
        print("Hermes Commander — usage:")
        print("  --new-session <description>    创建新协作会话")
        print("  --send <session_id> <msg>      发送消息到 OpenClaw")
        print("  --history <session_id>         查看会话历史")
        print("  --status <session_id>          查看会话状态和分析")
        print("  --list                         列出所有会话")
        return

    # --list
    if "--list" in args:
        sessions = sorted(STATE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
        if not sessions:
            print("No sessions found.")
            return
        for sp in sessions[:10]:
            s = json.loads(sp.read_text())
            sid = sp.stem
            n = len([m for m in s.get("messages", []) if m["role"] == "openclaw"])
            created = time.strftime("%m-%d %H:%M", time.localtime(s.get("created_at", 0)))
            print(f"  {sid[:12]}...  {n} turns  {created}")
        return

    # --new-session
    if "--new-session" in args:
        desc = " ".join(a for a in args if a != "--new-session")
        import uuid
        sid = uuid.uuid4().hex[:16]
        session = {"session_id": sid, "messages": [], "tasks": [],
                   "description": desc, "created_at": time.time()}
        save_session(session)
        print(json.dumps({"session_id": sid, "description": desc}))
        return

    # --status
    if "--status" in args:
        sid = [a for a in args if a != "--status"][0] if len(args) > 1 else None
        if not sid:
            print("Usage: --status <session_id>")
            return
        session = load_session(sid)
        oc_msgs = [m for m in session.get("messages", []) if m["role"] == "openclaw"]
        last_oc = oc_msgs[-1]["content"] if oc_msgs else ""

        print(f"Session: {sid}")
        print(f"Turns:   {len(oc_msgs)}")
        print(f"Tokens:  {sum(m.get('tokens', 0) for m in oc_msgs):,}")
        if last_oc:
            analysis = analyze_response(last_oc)
            print(f"Status:  has_question={analysis['has_question']}, "
                  f"has_deliverable={analysis['has_deliverable']}, "
                  f"needs_review={analysis['needs_review']}")
            if analysis["questions"]:
                print(f"Pending questions:")
                for q in analysis["questions"]:
                    print(f"  → {q}")
        print(json.dumps(session, ensure_ascii=False, indent=2) if "--verbose" in args else "")
        return

    # --history
    if "--history" in args:
        sid = [a for a in args if a != "--history"][0] if len(args) > 1 else None
        if not sid:
            print("Usage: --history <session_id>")
            return
        session = load_session(sid)
        for m in session.get("messages", []):
            role = m["role"].upper()
            content = m["content"][:300]
            print(f"\n[{role}] {content}")
        return

    # --send (default)
    if "--send" in args:
        rest = [a for a in args if a != "--send"]
        if len(rest) < 2 and sys.stdin.isatty():
            print("Usage: --send <session_id> <message>")
            print("   or: echo 'message' | hermes_commander.py --send <session_id>")
            return

        sid = rest[0]
        if len(rest) > 1:
            msg = " ".join(rest[1:])
        else:
            msg = sys.stdin.read().strip()

        if not msg:
            print(json.dumps({"error": "empty message"}))
            return

        result = send_to_openclaw(sid, msg)
        content = result.get("content", "")
        analysis = analyze_response(content)

        output = {
            "success": result["success"],
            "tokens": result["tokens"],
            "elapsed_ms": result["elapsed_ms"],
            "analysis": analysis,
            "content": content,
        }
        # 如果只是查看输出，直接打印内容
        if "--raw" in args:
            print(content)
        elif "--analysis-only" in args:
            print(json.dumps(analysis, ensure_ascii=False))
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    print(f"Unknown command. Use --help or see usage above.")


if __name__ == "__main__":
    main()
