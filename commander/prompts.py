"""
Agent Cluster Router — Commander Prompt 模板
为 Commander 的 plan / implement / review / test 阶段生成 prompt
"""


def plan_prompt(goal: str) -> str:
    """生成 Hermes 规划用的 prompt"""
    return (
        f"You are a software architect. Given the following goal, produce "
        f"a structured task breakdown.\n\n"
        f"Goal: {goal}\n\n"
        f"Return a JSON object with:\n"
        f'  "tasks": [{{"title": "...", "description": "...", '
        f'"acceptance_criteria": [{{"description": "..."}}]}}]\n'
        f'  "architect_notes": "..."\n\n'
        f"Each task should be independently implementable. Keep it concise. "
        f"Output ONLY valid JSON, no markdown fences."
    )


def implement_prompt(task_title: str, task_description: str) -> str:
    """生成 OpenClaw 实现用的 prompt"""
    return (
        f"You are a software engineer. Implement the following task.\n\n"
        f"Task: {task_title}\n"
        f"Description: {task_description}\n\n"
        f"Write the complete implementation. If you need clarification, "
        f'prefix your response with "QUESTION:" followed by the question. '
        f"Otherwise, output the code directly."
    )


def review_prompt(task_title: str, implementation: str) -> str:
    """生成 Hermes 审查用的 prompt"""
    return (
        f"You are a code reviewer. Review the following implementation.\n\n"
        f"Task: {task_title}\n"
        f"Implementation:\n```\n{implementation}\n```\n\n"
        f"Return a JSON object with:\n"
        f'  "status": "approved" or "rejected"\n'
        f'  "comment": "review feedback"\n\n'
        f"Output ONLY valid JSON, no markdown fences."
    )


def test_prompt(task_title: str, implementation: str) -> str:
    """生成测试用的 prompt（暂时手动/简单模式）"""
    return (
        f"Given the following implementation, run or check basic tests.\n\n"
        f"Task: {task_title}\n"
        f"Implementation:\n```\n{implementation}\n```\n\n"
        f"Return a JSON object with:\n"
        f'  "status": "passed" or "failed"\n'
        f'  "output": "test output summary"\n\n'
        f"Output ONLY valid JSON, no markdown fences."
    )
