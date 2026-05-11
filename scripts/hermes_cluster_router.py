#!/usr/bin/env python3
"""
Hermes 内部集群路由 v2 — 支持 OpenClaw Skill 感知
用法:
  python3 hermes_cluster_router.py [--classify-only] [--refresh-skills] <prompt>
  echo '{"messages": [...], "session_id": "..."}' | python3 hermes_cluster_router.py --json

路由优先级（新）:
  1. OpenClaw Skill 匹配（用户在 Claw 里装了 GitHub skill → 说 github 就转 Claw）
  2. CODE 意图 → OpenClaw
  3. PLAN / SEARCH 意图 → Hermes
  4. 其他 → Hermes 自己处理
"""
import sys
import json
import re
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

CACHE_FILE = Path(os.path.expanduser("~/.hermes/cache/openclaw_skills.json"))


# ============================================================
#  OpenClaw Skill Index
# ============================================================

def fetch_openclaw_skills() -> list[dict]:
    """运行 openclaw skills list --json 获取完整技能列表"""
    try:
        result = subprocess.run(
            ["openclaw", "skills", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("skills", [])
    except Exception:
        return []


def load_skill_index(force_refresh: bool = False) -> dict:
    """
    加载/缓存 OpenClaw skill 索引
    返回: { "skill_name": {"keywords": [...], "description": "...", "ready": bool} }
    """
    if not force_refresh and CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass

    skills = fetch_openclaw_skills()
    index = {}
    for s in skills:
        name = s.get("name", "")
        desc = s.get("description", "")
        ready = s.get("ready", False)

        # 从 skill 名称和描述中提取关键词
        keywords = set()

        # 名称中的关键词（拆分连字符和驼峰）
        name_parts = re.split(r'[-_ ]', name)
        for part in name_parts:
            if len(part) >= 2:
                keywords.add(part.lower())

        # 描述中提取显著词汇
        desc_lower = desc.lower()
        # 提取技术栈关键词
        for kw in ["github", "git", "notion", "obsidian", "spotify", "slack",
                    "discord", "whatsapp", "trello", "gmail", "calendar", "drive",
                    "browser", "coding", "codex", "claude code", "opencode",
                    "email", "imap", "smtp", "pdf", "weather", "whisper", "tts",
                    "speech", "audio", "video", "image", "rss", "blog",
                    "1password", "password", "hue", "lights", "tmux",
                    "summarize", "transcribe", "youtube", "podcast",
                    "task", "workflow", "todo", "issues", "pr", "pull request"]:
            if kw in desc_lower:
                keywords.add(kw.replace(" ", "_"))

        index[name] = {
            "keywords": sorted(keywords),
            "description": desc[:200],
            "ready": ready,
        }

    # 缓存
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(index, ensure_ascii=False))
    return index


def match_openclaw_skill(text: str, skill_index: dict) -> str | None:
    """
    检查用户消息是否匹配某个 OpenClaw skill
    返回匹配的 skill name，或 None
    """
    t = text.lower()
    best_match = None
    best_score = 0

    for name, info in skill_index.items():
        score = 0
        # 关键词命中计分
        for kw in info["keywords"]:
            if kw in t:
                score += 1
        # skill 名直接出现加分（连字符替换匹配）
        name_normalized = name.replace("-", " ").replace("_", " ")
        if name_normalized in t or name.replace("-", "").replace("_", "") in t:
            score += 5

        # 中文别名映射
        cn_aliases = CHINESE_SKILL_ALIASES.get(name, [])
        for alias in cn_aliases:
            if alias in t:
                score += 3

        if score > best_score:
            best_score = score
            best_match = name

    # 阈值：skill 名直接出现(≥5) 或 命中 ≥2 个关键词 或 命中中文别名(≥3)
    if best_score >= 2:
        return best_match
    return None


# 中文关键词 → OpenClaw skill 名映射
CHINESE_SKILL_ALIASES = {
    "weather": ["天气", "气温", "下雨", "刮风", "预报", "温度", "多少度", "几度", "摄氏度"],
    "spotify-player": ["音乐", "播放", "听歌", "歌曲", "专辑", "歌单"],
    "github": ["仓库", "推送", "提交", "拉取请求", "分支"],
    "gh-issues": ["issue", "问题追踪", "bug报告"],
    "notion": ["笔记", "文档", "知识库", "数据库"],
    "obsidian": ["黑曜石", "markdown笔记", "双向链接"],
    "himalaya": ["邮件", "收件箱", "发邮件", "收信"],
    "summarize": ["总结", "摘要", "概括", "视频总结"],
    "taskflow": ["工作流", "任务流", "多步骤", "自动化"],
    "tmux": ["终端复用", "会话管理"],
    "browser-automation": ["浏览器", "网页", "自动填表", "爬虫"],
    "coding-agent": ["代理编码", "委托编码"],
    "nano-pdf": ["编辑pdf", "修改pdf", "pdf文档"],
    "discord": ["dc", "频道"],
    "slack": ["消息", "频道"],
    "trello": ["看板", "卡片", "列表"],
    "voice-call": ["打电话", "语音通话", "电话"],
    "video-frames": ["视频帧", "截图", "提取帧"],
    "songsee": ["频谱", "音频可视化", "波形"],
    "xurl": ["推特", "twitter", "发推", "x平台"],
    "gog": ["谷歌文档", "google文档", "表格", "幻灯片"],
    "healthcheck": ["安全检查", "安全审计", "加固"],
    "clawhub": ["技能商店", "安装技能", "技能搜索"],
    "find-skills": ["找技能", "技能发现", "安装插件"],
    "openai-whisper": ["语音转文字", "录音转文字", "识别语音", "语音识别", "录音", "转录"],
    "openai-whisper-api": ["语音转文字api", "whisper api录音"],
    "openhue": ["灯", "灯光", "智能灯", "飞利浦", "灯泡"],
    "gemini": ["gemini", "谷歌ai"],
    "gifgrep": ["gif", "动图", "表情包"],
    "imsg": ["短信", "imessage", "发短信", "苹果消息"],
    "sag": ["朗读", "语音合成", "文字转语音", "读给我听"],
    "camsnap": ["摄像头", "监控画面", "抓拍"],
    "skill-creator": ["创建技能", "编写技能", "写个技能"],
    "sonoscli": ["音响", "扬声器", "sonos"],
    "bluebubbles": ["imessage", "苹果消息", "蓝色气泡"],
    "blogwatcher": ["rss", "订阅", "博客监控"],
    "peekaboo": ["mac自动化", "ui自动化", "屏幕自动化"],
    "sherpa-onnx-tts": ["离线语音", "本地语音合成", "无需联网朗读"],
    "blucli": ["蓝声", "bluos", "无线音箱"],
    "session-logs": ["会话日志", "聊天记录搜索"],
    "taskflow-inbox-triage": ["任务分流", "收件箱整理"],
    "skillhub-preference": ["技能商店偏好"],
}


# ============================================================
#  Intent Classifier
# ============================================================

CODE_KEYWORDS = [
    r'\b(code|function|class|def |import |debug|refactor|compile|build|deploy|api|endpoint|bug|fix|patch|PR|pull request|commit|git|repo)\b',
    r'```', r'\.py\b', r'\.js\b', r'\.ts\b', r'\.rs\b', r'\.go\b',
    r'\b(write|implement|create|generate)\b.*\b(code|function|script|program|app)\b',
    # 中文
    r'(写|编写|帮我写|写一个|修复|调试|重构|代码|函数|脚本|程序)',
]
PLAN_KEYWORDS = [
    r'\b(plan|design|architect|strategy|roadmap|milestone|blueprint|structure|organize|how should|what should|approach|proposal)\b',
    r'(规划|设计|架构|方案|蓝图|路线图|怎么|如何|建议)',
]
SEARCH_KEYWORDS = [
    r'\b(search|find|lookup|research|what is|who is|define|explain|how does|why is|document|tutorial|guide)\b',
    r'(什么是|是谁|解释|怎么|为什么|文档|教程|指南|搜索|查找)',
]


def classify(text: str) -> str:
    """返回 code|plan|search|chat"""
    t = text.lower()
    for pat in CODE_KEYWORDS:
        if re.search(pat, t):
            return "code"
    for pat in PLAN_KEYWORDS:
        if re.search(pat, t):
            return "plan"
    for pat in SEARCH_KEYWORDS:
        if re.search(pat, t):
            return "search"
    return "chat"


# ============================================================
#  Proactive Delegation Check
# ============================================================

# 复杂度信号：这些模式表示"OpenClaw 可能做得更好"
COMPLEXITY_PATTERNS = [
    # 多步骤工作流
    (r'(然后|接着|之后|再|并且|同时).*(然后|接着|之后|再|并且|同时)', "multi-step workflow", 5),
    (r'(first|then|after|and then|next|also).*(then|after|next)', "multi-step workflow", 5),
    (r'(\d+)\s*(个|步|steps?|tasks?)', "multiple steps", 3),
    # 大范围操作
    (r'(重构|重写|全部|所有|整个|大规模|大改)', "large scope", 6),
    (r'(refactor|rewrite|all|entire|whole|massive)', "large scope", 6),
    # Git 重度操作
    (r'(merge|rebase|cherry[\s-]?pick|conflict|branch|reset|stash|squash)', "git-heavy", 7),
    (r'(合并|变基|冲突|分支|回退)', "git-heavy", 7),
    # PR / Code Review
    (r'(review|PR|pull request|code review|审查|检查代码)', "code review", 6),
    # 浏览器自动化
    (r'(去|打开|访问).*(网站|网页|页面|官网|登录|填写|填表)', "browser automation", 8),
    (r'(browser|navigate|scrape|fill.?form|automate).*(site|page|web)', "browser automation", 8),
    # 项目脚手架
    (r'(从头|从零|初始化|搭建|创建项目|新建项目|scaffold|init)', "project scaffolding", 5),
    # 复杂调试
    (r'(debug|traceback|stack trace|segfault|core dump|内存泄漏|死锁)', "complex debugging", 7),
    # 跨文件操作
    (r'(多.*文件|所有.*\.py|所有.*\.js|across files|all files)', "cross-file", 4),
    # CI/CD / 部署
    (r'(deploy|CI|CD|pipeline|docker|k8s|kubernetes|部署|容器|流水线)', "devops", 5),
]

def check_delegation(text: str, skill_index: dict | None = None) -> dict:
    """
    三层决策引擎 — 第 1 层（正则 + skill 匹配）

    返回:
      should_delegate: bool
      confidence: "high" (score≥8) | "medium" (4-7) | "low" (0-3)
      decision: "openclaw" | "hermes" | "ask_hermes" (拿不准，交第 2 层)
      reasons, score, intent, skill_matched
    """
    t = text.lower()
    reasons = []
    total_score = 0

    # 1. 复杂度信号
    for pattern, reason, score in COMPLEXITY_PATTERNS:
        if re.search(pattern, t):
            reasons.append(reason)
            total_score += score

    # 2. OpenClaw skill 匹配
    matched_skill = None
    if skill_index:
        matched_skill = match_openclaw_skill(text, skill_index)
        if matched_skill:
            reasons.append(f"OpenClaw skill: {matched_skill}")
            total_score += 10  # skill match 是强信号

    # 3. code 意图
    intent = classify(text)
    if intent == "code":
        reasons.append("code intent")
        total_score += 8

    # 置信度分层
    if total_score >= 8:
        confidence = "high"
        decision = "openclaw"
    elif total_score >= 4:
        confidence = "medium"
        decision = "openclaw"
    elif total_score > 0:
        confidence = "low"
        decision = "ask_hermes"  # 有微弱信号但不够 — 让第 2 层定
    else:
        confidence = "low"
        decision = "ask_hermes"  # 完全无信号 — 让 Hermes 自己判断

    return {
        "should_delegate": decision == "openclaw",
        "confidence": confidence,
        "decision": decision,
        "score": total_score,
        "reasons": reasons,
        "intent": intent,
        "skill_matched": matched_skill,
        "recommendation": {"openclaw": "OpenClaw", "ask_hermes": "Let Hermes decide (Layer 2)", "hermes": "Hermes"}[decision],
    }


# ============================================================
#  Routing
# ============================================================

INTENT_BACKEND = {
    "code": "openclaw",
    "plan": "hermes",
    "search": "hermes",
    "tool": "openclaw",
    "chat": "auto",
}

ADAPTER_URLS = {
    "openclaw": "http://127.0.0.1:8082/chat",
    "hermes": "http://127.0.0.1:8081/chat",
}


def route_to_backend(intent: str, messages: list[dict],
                     session_id: str = "", timeout: int = 120) -> dict:
    backend = INTENT_BACKEND.get(intent, "auto")
    if backend == "auto":
        return {"routed": False, "intent": intent, "reason": "handled locally"}

    url = ADAPTER_URLS.get(backend)
    if not url:
        return {"routed": False, "intent": intent, "reason": f"no adapter for {backend}"}

    try:
        payload = json.dumps({
            "messages": messages,
            "session_id": session_id,
            "timeout_ms": timeout * 1000,
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return {
            "routed": True,
            "intent": intent,
            "backend": backend,
            "content": data.get("content", ""),
            "success": data.get("success", True),
        }
    except urllib.error.URLError as e:
        return {"routed": True, "intent": intent, "backend": backend, "error": str(e), "success": False}
    except Exception as e:
        return {"routed": True, "intent": intent, "backend": backend, "error": str(e), "success": False}


# ============================================================
#  Main
# ============================================================

def list_missing_aliases(skill_index: dict) -> list[str]:
    """找出有 skill 但没有中文别名的"""
    return sorted(name for name in skill_index if name not in CHINESE_SKILL_ALIASES)


def main():
    args = sys.argv[1:]
    refresh_skills = "--refresh-skills" in args
    args = [a for a in args if a != "--refresh-skills"]

    # --list-skills mode
    if "--list-skills" in args:
        skill_index = load_skill_index(force_refresh=refresh_skills)
        missing = list_missing_aliases(skill_index)
        for name, info in sorted(skill_index.items()):
            ready = "✓" if info["ready"] else "△"
            has_cn = " " if name in CHINESE_SKILL_ALIASES else "!"
            print(f" {has_cn}{ready} {name}: {info['description'][:80]}")
        if missing:
            print(f"\n⚠ {len(missing)} skills missing Chinese aliases: {', '.join(missing[:10])}")
            print(f"  Run --missing-aliases to see full list.")
        return

    # --missing-aliases mode
    if "--missing-aliases" in args:
        skill_index = load_skill_index(force_refresh=refresh_skills)
        missing = list_missing_aliases(skill_index)
        if missing:
            print(f"{len(missing)} skills without Chinese aliases:")
            for name in missing:
                info = skill_index.get(name, {})
                desc = info.get("description", "")[:100]
                print(f"  - {name}: {desc}")
        else:
            print("All skills have Chinese aliases. ✓")
        return

    # --classify-only
    if "--classify-only" in args:
        prompt = " ".join(a for a in args if a != "--classify-only")
        if not prompt and not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()

        skill_index = load_skill_index(force_refresh=refresh_skills)
        matched = match_openclaw_skill(prompt, skill_index) if skill_index else None

        intent = classify(prompt)
        result = {
            "intent": intent,
            "backend_hint": INTENT_BACKEND.get(intent, "auto"),
            "openclaw_skill_matched": matched,
        }
        if matched:
            result["backend_hint"] = "openclaw"
            result["reason"] = f"OpenClaw skill matched: {matched}"
        print(json.dumps(result, ensure_ascii=False))
        return

    # --check-delegation mode
    if "--check-delegation" in args:
        prompt = " ".join(a for a in args if a != "--check-delegation")
        if not prompt and not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()

        skill_index = load_skill_index(force_refresh=refresh_skills)
        result = check_delegation(prompt, skill_index)
        print(json.dumps(result, ensure_ascii=False))
        return

    # --json mode
    if "--json" in args:
        raw = sys.stdin.read()
        req = json.loads(raw)
        messages = req.get("messages", [])
        session_id = req.get("session_id", "")

        user_text = " ".join(m["content"] for m in messages if m.get("role") == "user")

        skill_index = load_skill_index(force_refresh=refresh_skills)
        delegation = check_delegation(user_text, skill_index)

        if delegation["decision"] == "openclaw":
            result = route_to_backend("code", messages, session_id)
            result["intent"] = delegation["intent"]
            result["delegation_reasons"] = delegation["reasons"]
            result["skill_matched"] = delegation["skill_matched"]
            result["confidence"] = delegation["confidence"]
        elif delegation["decision"] == "ask_hermes":
            # 不路由，返回分类结果让 Hermes 自己判断
            result = {
                "routed": False,
                "intent": delegation["intent"],
                "reason": "Layer 1 uncertain — let Hermes decide (Layer 2)",
                "delegation": delegation,
            }
        else:
            result = route_to_backend(delegation["intent"], messages, session_id)
            result["intent"] = delegation["intent"]

        print(json.dumps(result, ensure_ascii=False))
        return

    # Default: prompt arg mode
    prompt = " ".join(args) if args else sys.stdin.read().strip()
    if not prompt:
        print(json.dumps({"error": "no prompt provided"}))
        sys.exit(1)

    skill_index = load_skill_index(force_refresh=refresh_skills)
    delegation = check_delegation(prompt, skill_index)

    if delegation["decision"] == "openclaw":
        result = route_to_backend("code", [{"role": "user", "content": prompt}])
        result["intent"] = delegation["intent"]
        result["delegation_reasons"] = delegation["reasons"]
        result["skill_matched"] = delegation["skill_matched"]
        result["confidence"] = delegation["confidence"]
    elif delegation["decision"] == "ask_hermes":
        result = {
            "routed": False,
            "intent": delegation["intent"],
            "reason": "Layer 1 uncertain — let Hermes decide (Layer 2)",
            "delegation": delegation,
        }
    else:
        result = route_to_backend(delegation["intent"], [{"role": "user", "content": prompt}])

    result["intent"] = delegation["intent"]
    if result.get("routed"):
        print(result.get("content", json.dumps(result)))
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
