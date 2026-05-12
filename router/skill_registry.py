"""Skill Registry — 定义各 Backend 拥有的 Skill 并提供匹配能力"""
from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class SkillDefinition:
    name: str
    backend: str
    aliases: List[str]
    description: str = ""


# --- OpenClaw Skills ---
OPENCLAW_SKILLS = [
    SkillDefinition(
        name="weather",
        backend="openclaw",
        aliases=["weather", "天气", "气温", "下雨", "温度", "多云", "晴天", "下雪",
                  "天气预报", "天气查询", "今天天气", "明天气温", "天气怎么样",
                  "多少度", "空气质量", "台风", "紫外线", "湿度", "雾霾",
                  "污染指数", "沙尘暴", "海啸", "暴雨", "雷暴", "冰雹",
                  "forecast", "temperature", "rain", "snow", "sunny",
                  "humidity", "pollution", "storm", "hurricane", "tsunami"],
        description="天气查询",
    ),
    SkillDefinition(
        name="github",
        backend="openclaw",
        aliases=["github", "GitHub", "GH", "repo", "仓库", "代码仓库", "拉取仓库",
                  "分析仓库", "star", "clone", "fork", "pull request", "PR",
                  "git clone", "git repo", "开源项目", "github.com"],
        description="GitHub 仓库操作",
    ),
    SkillDefinition(
        name="email",
        backend="openclaw",
        aliases=["email", "mail", "邮件", "发邮件", "写邮件", "发送邮件",
                  "回复邮件", "邮件回复", "给.*发邮件", "邮件给", "email to",
                  "send email", "write email", "draft email", "compose email"],
        description="邮件发送",
    ),
    SkillDefinition(
        name="notion",
        backend="openclaw",
        aliases=["notion", "Notion", "新建页面", "知识库页面", "notion 页面",
                  "notion page", "notion 文档", "notion 数据库",
                  "notion database", "更新.*notion", "notion.*更新"],
        description="Notion 文档操作",
    ),
    SkillDefinition(
        name="web_search",
        backend="openclaw",
        aliases=["web_search", "搜索", "搜一下", "查一下", "找一下", "帮我搜", "帮我查", "帮我找",
                  "查资料", "找资料", "查找", "搜索资料", "搜索一下", "在线搜索", "联网搜索",
                  "google", "Google", "百度", "bing", "search for",
                  "look up", "documentation", "docs"],
        description="网页搜索",
    ),
    SkillDefinition(
        name="music",
        backend="openclaw",
        aliases=["music", "音乐", "播放音乐", "放歌", "听歌", "歌曲", "play music",
                  "播放.*歌", "听.*歌", "spotify"],
        description="音乐播放",
    ),
    SkillDefinition(
        name="discord",
        backend="openclaw",
        aliases=["discord", "Discord", "频道", "discord 消息", "discord message",
                  "发.*discord", "discord.*发"],
        description="Discord 消息",
    ),
    SkillDefinition(
        name="file_ops",
        backend="openclaw",
        aliases=["文件操作", "读写文件", "保存文件", "文件读写", "文件编辑",
                  "编辑文件", "打开文件", "写入文件", "file operations",
                  "read file", "write file", "save file", "edit file"],
        description="文件操作",
    ),
    SkillDefinition(
        name="shell",
        backend="openclaw",
        aliases=["shell", "terminal", "终端", "命令行", "执行命令", "运行命令",
                  "bash", "zsh", "命令", "运行脚本", "run command",
                  "execute command", "terminal command"],
        description="终端/Shell 操作",
    ),
]


# --- Hermes Skills ---
HERMES_SKILLS = [
    SkillDefinition(
        name="planning",
        backend="hermes",
        aliases=["plan", "architecture", "roadmap", "路线图", "技术选型",
                  "system design", "架构设计", "方案设计", "技术方案",
                  "project plan", "计划书"],
        description="架构规划与设计",
    ),
    SkillDefinition(
        name="research",
        backend="hermes",
        aliases=["research", "研究", "调研", "论文", "paper", "文献", "资料调研",
                  "技术调研", "对比分析", "技术对比", "evaluate", "评估"],
        description="深度调研与分析",
    ),
]


# Compile regex patterns for alias matching (fuzzy)
def _compile_patterns(skills: list[SkillDefinition]) -> list[tuple[SkillDefinition, list[re.Pattern]]]:
    compiled = []
    for skill in skills:
        patterns = []
        for alias in skill.aliases:
            try:
                # Aliases containing regex metacharacters (like .*) are compiled as-is
                if '.*' in alias or '.*?' in alias or '|' in alias:
                    patterns.append(re.compile(alias, re.IGNORECASE))
                # Add word boundaries for ASCII-only aliases to prevent partial matches
                # (e.g., "repo" matching "monorepo", "search" matching "research")
                # For CJK aliases, match as simple substring (word boundaries don't work for CJK)
                elif alias.isascii():
                    patterns.append(re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE))
                else:
                    patterns.append(re.compile(re.escape(alias), re.IGNORECASE))
            except re.error:
                pass
        compiled.append((skill, patterns))
    return compiled


# Pre-compile
_openclaw_patterns = _compile_patterns(OPENCLAW_SKILLS)
_hermes_patterns = _compile_patterns(HERMES_SKILLS)


def match_skill(text: str) -> Optional[SkillDefinition]:
    """从文本中检测技能匹配，返回第一个命中的 SkillDefinition

    匹配顺序：OpenClaw 技能优先（因为它们是特定功能），然后 Hermes 技能
    """
    if not text:
        return None

    # 优先匹配 OpenClaw 技能（更具体）
    for skill, patterns in _openclaw_patterns:
        for pattern in patterns:
            if pattern.search(text):
                return skill

    # 然后匹配 Hermes 技能
    for skill, patterns in _hermes_patterns:
        for pattern in patterns:
            if pattern.search(text):
                return skill

    return None


def get_skill_backend(text: str) -> Optional[str]:
    """从文本中检测技能并返回对应的 backend

    如果没匹配到任何技能，返回 None（让 normal intent routing 接管）
    """
    skill = match_skill(text)
    return skill.backend if skill else None
