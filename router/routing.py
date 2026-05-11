"""路由策略引擎 — 支持加权随机、最少连接、轮询 + 意图/标签/灰度路由"""
import random
import re
import time
from collections import defaultdict
from router.models import AgentRequest, RouteStrategy, TaskIntent
from router.registry import NodeRegistry, Node


class IntentClassifier:
    """基于关键词的意图分类器"""

    CODE_KEYWORDS = [
        r'\b(code|function|class|def |import |debug|refactor|compile|build|deploy|api|endpoint|bug|fix|patch|PR|pull request|commit|git|repo)\b',
        r'```', r'\.py\b', r'\.js\b', r'\.ts\b', r'\.rs\b', r'\.go\b',
        r'\b(write|implement|create|generate)\b.*\b(code|function|script|program|app)\b',
    ]
    PLAN_KEYWORDS = [
        r'\b(plan|design|architect|strategy|roadmap|milestone|blueprint|structure|organize|how should|what should|approach|proposal)\b',
    ]
    SEARCH_KEYWORDS = [
        r'\b(search|find|lookup|research|what is|who is|define|explain|how does|why is|document|tutorial|guide)\b',
        r'\b(googling|google|wiki|docs?|knowledge)\b',
    ]

    @classmethod
    def classify(cls, text: str, current_intent: TaskIntent = TaskIntent.CHAT) -> TaskIntent:
        if current_intent != TaskIntent.CHAT:
            return current_intent
        text_lower = text.lower()
        for pattern in cls.CODE_KEYWORDS:
            if re.search(pattern, text_lower):
                return TaskIntent.CODE
        for pattern in cls.PLAN_KEYWORDS:
            if re.search(pattern, text_lower):
                return TaskIntent.PLAN
        for pattern in cls.SEARCH_KEYWORDS:
            if re.search(pattern, text_lower):
                return TaskIntent.SEARCH
        return TaskIntent.CHAT

    INTENT_BACKEND = {
        TaskIntent.CODE: "openclaw",
        TaskIntent.PLAN: "hermes",
        TaskIntent.SEARCH: "hermes",
        TaskIntent.TOOL: "openclaw",
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

    def select_node(self, req: AgentRequest) -> Node | None:
        """
        路由优先级: manual → tags → intent → canary → strategy
        """
        preferred = req.routing.preferred
        tags = req.task.tags

        # 1. 手动指定
        if preferred == RouteStrategy.HERMES:
            return self._pick_from_pool("hermes")
        if preferred == RouteStrategy.OPENCLAW:
            return self._pick_from_pool("openclaw")

        # 2. 标签匹配
        if "planning" in tags:
            node = self._pick_from_pool("hermes")
            if node: return node
        if "tool-heavy" in tags:
            node = self._pick_from_pool("openclaw")
            if node: return node

        # 3. 意图路由
        intent = req.task.intent
        if intent in IntentClassifier.INTENT_BACKEND:
            backend = IntentClassifier.INTENT_BACKEND[intent]
            node = self._pick_from_pool(backend)
            if node: return node

        # 4. 灰度比例
        cluster = self._canary_choice()
        if cluster:
            self.request_counts[cluster] = self.request_counts.get(cluster, 0) + 1
            node = self._pick_from_pool(cluster)
            if node: return node

        # 5. 按策略兜底
        return self._select_by_strategy()

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
