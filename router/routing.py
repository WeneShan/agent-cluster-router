"""路由策略引擎 — 支持加权随机、最少连接、轮询 + 意图/标签/灰度/技能路由"""
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from router.models import AgentRequest, RouteStrategy, TaskIntent
from router.registry import NodeRegistry, Node
from router.skill_registry import match_skill, SkillDefinition
from router.security_routing import evaluate_security, SecurityRoutingResult, SecurityAction


@dataclass
class RoutingResult:
    """路由决策结果"""
    node: Optional[Node] = None
    decision_layer: str = "L6_DEFAULT"
    matched_skill: Optional[str] = None
    security_action: Optional[str] = None
    reason: str = ""


class IntentClassifier:
    """基于关键词的意图分类器 — 支持中英文"""

    # 代码/工程意图 → OpenClaw
    CODE_KEYWORDS = [
        # English（codebase, websocket, cli 等工程术语）
        r'\b(code(?:base)?|function|class|def\b|import\b|debug|refactor|compile|build|deploy|api|endpoint|bug|fix|patch|PR\b|pull request|commit|git|repo|merge|implement(?:ation)?|server|script|test(?:s|ing)?|cli\b|oauth|websocket)\b',
        r'```', r'\.py\b', r'\.js\b', r'\.ts\b', r'\.rs\b', r'\.go\b',
        r'\b(write|create|generate|build|develop|add)\b.*\b(code|function|script|program|app|server|api|component|module|endpoint|scraper|爬虫|工具|爬虫|脚本|sort|排序|算法|algorithm)\b',
        r'\b(unit test|integration test|test case|pytest|jest|mocha)\b',
        r'\b(fix(?:ing)?|patch(?:ing)?|optimiz(?:e|ing)|refactor(?:ing)?)\b',
        r'\b(sql query|database|dockerfile|docker build|npm install|pip install|npm\b|pip\b)\b',
        # 中文（explicit code actions）
        r'(写|编写|实现|创建|生成|开发|搭建|构建|制造).*(代码|函数|脚本|程序|应用|组件|爬虫|API|接口|服务|服务器|工具|爬虫|scraper|查询|SQL|排序|算法)',
        r'(帮我|如何|怎么).*(写|编写|实现|创建|开发|添加).*(代码|函数|API|接口|模块|爬虫|scraper|脚本|查询|SQL|排序|算法)',
        r'(修复|修改|改|调试|重构|优化|合并|merge|提交|编译|部署|实现)',
        r'(bug|错误|报错|异常|error|exception|编译错误|部署|Connection refused|怎么解决|如何解决)',
        r'(单元测试|集成测试|测试用例|写.*测试|pytest)',
        r'\b(k8s|kubernetes|docker)\b.*\b(deploy|build|写|创建|搭建|配置|部署|apply|manifest)\b',
    ]
    # 规划/架构意图 → Hermes
    PLAN_KEYWORDS = [
        r'\b(plan(?:ning)?|design|architect(?:ure|ural|ing)?|strategy|roadmap|milestone|blueprint|structure|organize|approach|proposal|propose|review)\b',
        r'\b(how should|what should|best (?:way|practice|approach)|tech(?:nology)? stack|system design|(?:技术|选型|选什么))',
        r'(设计|规划|架构|方案|策略|技术选型|路线|蓝图|结构|组织|评审|审查|review|技术栈)',
        r'(怎么做|怎么设计|怎么规划|怎么组织|选什么|选型|怎么考虑)',
        r'(项目|系统|平台).*(架构|设计|规划|方案|结构)',
        r'(帮我|如何|怎么).*(设计|规划|架构|review|评审|审查)',
        # 纯技术栈选择是规划
        r'(如何|怎么|选).*(技术栈|技术选型|框架|语言)',
    ]
    # 搜索/知识意图 → Hermes
    SEARCH_KEYWORDS = [
        # English
        r'\b(search|find|lookup|research|define|explain|how does|why is|document(?:ation)?|tutorial|guide)\b',
        r'\b(googling|google|wiki|knowledge)\b',
        r'\b(what is|who is|who created|meaning of)\b',
        # 中文
        r'(搜索|查找|查一下|帮我查|是什么|什么是|是谁|怎么.*工作|是什么意思|帮我找|帮我搜)',
        r'(教程|文档|资料|帮我找.*资料)',
    ]

    @classmethod
    def _has_code(cls, text: str) -> bool:
        return any(re.search(p, text) for p in cls.CODE_KEYWORDS)

    @classmethod
    def _has_plan(cls, text: str) -> bool:
        return any(re.search(p, text) for p in cls.PLAN_KEYWORDS)

    @classmethod
    def _has_search(cls, text: str) -> bool:
        return any(re.search(p, text) for p in cls.SEARCH_KEYWORDS)

    @classmethod
    def classify(cls, text: str, current_intent: TaskIntent = TaskIntent.CHAT) -> TaskIntent:
        if current_intent != TaskIntent.CHAT:
            return current_intent
        text_lower = text.lower()

        has_code = cls._has_code(text_lower)
        has_plan = cls._has_plan(text_lower)

        # 同时有设计和代码意图 → 先规划
        # 例外: implement/algorithm + 动态规划 → CODE（这是 CS 算法术语）
        code_action = bool(re.search(r'\b(implement|algorithm|function|class)\b', text_lower))
        plan_is_cs = bool(re.search(r'动态规划|algorithm|binary search|sort|tree', text_lower))
        if has_plan and has_code:
            if code_action and plan_is_cs:
                return TaskIntent.CODE
            return TaskIntent.PLAN

        if has_code:
            return TaskIntent.CODE

        # 如果匹配规划关键词但用户表达的是主观意见 → 降级为 chat
        CHAT_OPINION = r'(你觉得|你认为|我感觉|我的看法)'
        if has_plan and not re.search(CHAT_OPINION, text_lower):
            return TaskIntent.PLAN
        if has_plan:
            return TaskIntent.CHAT

        # 搜索意图
        if cls._has_search(text_lower):
            return TaskIntent.SEARCH

        return TaskIntent.CHAT

    INTENT_BACKEND = {
        TaskIntent.CODE: "openclaw",
        TaskIntent.PLAN: "hermes",
        TaskIntent.SEARCH: "hermes",
        TaskIntent.TOOL: "openclaw",
        TaskIntent.CHAT: "hermes",
    }


class RoutingEngine:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        # 调度策略
        self.strategy: str = registry.routing_config.get("default_strategy", "weighted")
        # 灰度发布
        self.canary_ratio: float = 0.0
        self.canary_target: str = "hermes"
        self.default_target: str = "openclaw"
        # 请求计数
        self.request_counts: dict[str, int] = {"hermes": 0, "openclaw": 0}
        # 负载均衡状态
        self.active_connections: dict[str, int] = defaultdict(int)  # node_name → count
        self.round_robin_idx: dict[str, int] = defaultdict(int)     # cluster → next index

    def select_node(self, req: AgentRequest, user_text: str = "") -> RoutingResult:
        """
        路由优先级: security → manual → tags → skill → intent → canary → strategy
        """
        preferred = req.routing.preferred
        tags = req.task.tags

        # 0. 安全路由（最高优先级，不可被任何其它层覆盖）
        if user_text:
            sec_result = evaluate_security(user_text)
            if sec_result.matched:
                node = None
                if sec_result.action != SecurityAction.BLOCK:
                    node = self._pick_from_pool(sec_result.selected_backend or "hermes")
                return RoutingResult(
                    node=node,
                    decision_layer="L0_SECURITY",
                    security_action=sec_result.action.value,
                    reason=sec_result.reason,
                )

        # 1. 手动指定
        if preferred == RouteStrategy.HERMES:
            node = self._pick_from_pool("hermes")
            return RoutingResult(
                node=node,
                decision_layer="L1_MANUAL",
                reason=f"manual override to hermes",
            )
        if preferred == RouteStrategy.OPENCLAW:
            node = self._pick_from_pool("openclaw")
            return RoutingResult(
                node=node,
                decision_layer="L1_MANUAL",
                reason=f"manual override to openclaw",
            )

        # 2. 标签匹配
        if "planning" in tags:
            node = self._pick_from_pool("hermes")
            if node:
                return RoutingResult(
                    node=node,
                    decision_layer="L2_TAG",
                    reason="matched tag rule: planning → hermes",
                )
        if "tool-heavy" in tags:
            node = self._pick_from_pool("openclaw")
            if node:
                return RoutingResult(
                    node=node,
                    decision_layer="L2_TAG",
                    reason="matched tag rule: tool-heavy → openclaw",
                )

        # 3. Skill Routing（优先于 Intent Routing）
        if user_text:
            skill = match_skill(user_text)
            if skill:
                node = self._pick_from_pool(skill.backend)
                if node:
                    return RoutingResult(
                        node=node,
                        decision_layer="L3_SKILL",
                        matched_skill=skill.name,
                        reason=f"matched skill '{skill.name}' → {skill.backend}",
                    )

        # 4. 意图路由
        intent = req.task.intent
        if intent in IntentClassifier.INTENT_BACKEND:
            backend = IntentClassifier.INTENT_BACKEND[intent]
            node = self._pick_from_pool(backend)
            if node:
                return RoutingResult(
                    node=node,
                    decision_layer="L4_INTENT",
                    reason=f"matched intent '{intent.value}' → {backend}",
                )

        # 5. 灰度比例
        cluster = self._canary_choice()
        if cluster:
            self.request_counts[cluster] = self.request_counts.get(cluster, 0) + 1
            node = self._pick_from_pool(cluster)
            if node:
                return RoutingResult(
                    node=node,
                    decision_layer="L5_CANARY",
                    reason=f"canary traffic routing to {cluster}",
                )

        # 6. 按策略兜底
        node = self._select_by_strategy()
        return RoutingResult(
            node=node,
            decision_layer="L6_DEFAULT",
            reason=f"strategy-based fallback to {node.cluster if node else 'none'}",
        )

    def _pick_from_pool(self, cluster: str) -> Node | None:
        """从指定集群的健康节点中按策略选择"""
        pool = self.registry.get_pool(cluster)
        if not pool: return None
        healthy = pool.healthy_nodes()
        if not healthy: return None
        return self._select_node_from_list(healthy, cluster)

    def _select_by_strategy(self) -> Node | None:
        """从所有健康节点中按策略选择"""
        all_nodes = self.registry.all_healthy_nodes()
        if not all_nodes: return None
        return self._select_node_from_list(all_nodes)

    def _select_node_from_list(self, nodes: list[Node], cluster: str = "") -> Node | None:
        """根据当前 strategy 从节点列表中选择"""
        if self.strategy == "least_connections":
            return self._least_connections(nodes)
        elif self.strategy == "round_robin":
            return self._round_robin(nodes, cluster)
        else:
            return self._weighted_choice(nodes)

    def _weighted_choice(self, nodes: list[Node]) -> Node:
        """加权随机"""
        total = sum(n.weight for n in nodes)
        r = random.uniform(0, total)
        cumulative = 0
        for node in nodes:
            cumulative += node.weight
            if r <= cumulative:
                return node
        return nodes[-1]

    def _least_connections(self, nodes: list[Node]) -> Node:
        """最少连接数"""
        return min(nodes, key=lambda n: self.active_connections.get(n.name, 0))

    def _round_robin(self, nodes: list[Node], cluster: str = "") -> Node:
        """轮询"""
        if cluster:
            idx = self.round_robin_idx[cluster] % len(nodes)
            self.round_robin_idx[cluster] = idx + 1
        else:
            # 全局轮询 — 用第一个节点的 cluster 做 key
            key = nodes[0].cluster if nodes else "default"
            idx = self.round_robin_idx[key] % len(nodes)
            self.round_robin_idx[key] = idx + 1
        return nodes[idx]

    def acquire_connection(self, node_name: str):
        self.active_connections[node_name] += 1

    def release_connection(self, node_name: str):
        if self.active_connections.get(node_name, 0) > 0:
            self.active_connections[node_name] -= 1

    def set_strategy(self, strategy: str):
        if strategy in ("weighted", "least_connections", "round_robin"):
            self.strategy = strategy

    def get_load_status(self) -> dict:
        return {
            "strategy": self.strategy,
            "active_connections": dict(self.active_connections),
            "round_robin_idx": dict(self.round_robin_idx),
        }

    # --- 灰度发布 ---
    def _canary_choice(self) -> str | None:
        if self.canary_ratio <= 0:
            return self.default_target
        if self.canary_ratio >= 1.0:
            return self.canary_target
        if random.random() < self.canary_ratio:
            return self.canary_target
        return self.default_target

    def set_canary(self, ratio: float, target: str = "hermes"):
        self.canary_ratio = max(0.0, min(1.0, ratio))
        self.canary_target = target
        self.default_target = "openclaw" if target == "hermes" else "hermes"

    def get_canary_status(self) -> dict:
        total = sum(self.request_counts.values())
        return {
            "canary_ratio": self.canary_ratio,
            "canary_target": self.canary_target,
            "default_target": self.default_target,
            "request_counts": self.request_counts,
            "total_canary_requests": total,
        }

    def reset_counts(self):
        self.request_counts = {"hermes": 0, "openclaw": 0}
