"""
Agent Cluster Router — 安全模块
提供 API Key 鉴权、敏感信息脱敏、消息大小验证
"""
import os
import re
from fastapi import Header, HTTPException, Request

# --- 配置 ---
API_KEY = os.getenv("AGENT_ROUTER_API_KEY", "")

MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "20000"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", str(1024 * 1024)))  # 1MB


# --- API Key 鉴权 ---
async def verify_api_key(
    request: Request,
    x_api_key: str = Header(default=None),
) -> bool:
    """验证 API Key
    
    如果未设置 AGENT_ROUTER_API_KEY，则跳过验证。
    Header: X-API-Key
    """
    if not API_KEY:
        return True  # 未配置，跳过鉴权

    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. Set AGENT_ROUTER_API_KEY to disable auth.",
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return True


# --- 敏感信息脱敏 ---
SENSITIVE_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "[REDACTED:OPENAI_KEY]"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED:ANTHROPIC_KEY]"),
    (re.compile(r"ghp_[A-Za-z0-9_]{20,}"), "[REDACTED:GITHUB_TOKEN]"),
    (re.compile(r"gho_[A-Za-z0-9_]{20,}"), "[REDACTED:GITHUB_OAUTH]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\.\-_=]{20,}"), "[REDACTED:BEARER_TOKEN]"),
    (re.compile(r"xox[bpras]-[A-Za-z0-9-]{10,}"), "[REDACTED:SLACK_TOKEN]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:AWS_ACCESS_KEY]"),
    (re.compile(r"eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*"), "[REDACTED:JWT]"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "[REDACTED:PRIVATE_KEY]"),
]


def redact_sensitive(text: str) -> str:
    """脱敏敏感信息
    
    匹配并替换：OpenAI/Anthropic API Key、GitHub Token、
    Bearer Token、Slack Token、AWS Access Key、JWT、私钥等。
    """
    if not text:
        return text

    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


# --- 消息大小验证 ---
def validate_messages(messages: list[dict], max_chars: int = None) -> None:
    """验证消息总长度不超过限制"""
    if max_chars is None:
        max_chars = MAX_MESSAGE_CHARS

    total = sum(len(m.get("content", "")) for m in messages)
    if total > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Message too large: {total} chars (max {max_chars})",
        )
