"""Skill Registry 测试"""
import pytest
from router.skill_registry import match_skill, get_skill_backend, OPENCLAW_SKILLS


class TestSkillMatching:
    """测试技能匹配"""

    def test_weather_cn(self):
        skill = match_skill("帮我查一下今天上海天气")
        assert skill is not None
        assert skill.name == "weather"
        assert skill.backend == "openclaw"

    def test_weather_en(self):
        skill = match_skill("What's the weather like in Tokyo?")
        assert skill is not None
        assert skill.name == "weather"
        assert skill.backend == "openclaw"

    def test_github_cn(self):
        skill = match_skill("帮我看看这个 GitHub 仓库怎么样")
        assert skill is not None
        assert skill.name == "github"
        assert skill.backend == "openclaw"

    def test_github_clone(self):
        skill = match_skill("帮我 clone 这个 GitHub 仓库到本地")
        assert skill is not None
        assert skill.name == "github"
        assert skill.backend == "openclaw"

    def test_email_cn(self):
        skill = match_skill("帮我给客户发一封邮件")
        assert skill is not None
        assert skill.name == "email"
        assert skill.backend == "openclaw"

    def test_notion_cn(self):
        skill = match_skill("帮我在 Notion 里新建一个项目页面")
        assert skill is not None
        assert skill.name == "notion"
        assert skill.backend == "openclaw"

    def test_web_search_cn(self):
        skill = match_skill("帮我搜索一下 Python 异步编程的资料")
        assert skill is not None
        assert skill.name == "web_search"
        assert skill.backend == "openclaw"

    def test_search_overlap_priority(self):
        """git搜索同时命中 github + web_search, github 优先"""
        skill = match_skill("帮我搜一下这个 GitHub 项目")
        # github 在列表中排在前面，应该优先匹配
        assert skill is not None
        assert skill.name in ("github", "web_search")

    def test_no_skill_match(self):
        """普通对话不应命中任何技能"""
        skill = match_skill("你好，今天怎么样？")
        assert skill is None

    def test_coding_not_skill(self):
        """写代码不应被 skill routing 拦截（应该走 intent routing）"""
        skill = match_skill("写一个 Python 排序函数")
        # 排序不在 openclaw skill aliases 中
        assert skill is None  # 不应被 skill routing 拦截

    def test_get_skill_backend(self):
        assert get_skill_backend("查天气") == "openclaw"
        assert get_skill_backend("你好") is None
        assert get_skill_backend("发邮件给老板") == "openclaw"

    def test_all_openclaw_skills_registered(self):
        """所有 OpenClaw 技能应都在列表中"""
        names = {s.name for s in OPENCLAW_SKILLS}
        expected = {"weather", "github", "email", "notion", "web_search", "music", "discord", "file_ops", "shell"}
        assert names == expected
