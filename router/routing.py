"""路由策略引擎 — 支持手动指定、标签匹配、灰度权重三种策略"""
import random
from router.models import AgentRequest, RouteStrategy
from router.registry import NodeRegistry, Node


class RoutingEngine:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        # 灰度发布状态
        self.canary_ratio: float = 0.0      # 0.0 = 全走 default, 1.0 = 全走 canary
        self.canary_target: str = "hermes"   # 灰度目标后端
        self.default_target: str = "openclaw" # 默认后端
        # 请求计数（用于验证分流比例）
        self.request_counts: dict[str, int] = {"hermes": 0, "openclaw": 0}

    def select_node(self, req: AgentRequest) -> Node | None:
        """
        根据请求的 routing.preferred 和 task.tags 选择目标节点
        
        优先级:
        1. 手动指定 (preferred=openclaw|hermes)
        2. 标签匹配 (tags 包含 planning → hermes, tool-heavy → openclaw)
        3. 灰度权重 (canary_ratio) — 全局生效
        4. 按权重随机选择
        """
        preferred = req.routing.preferred
        tags = req.task.tags

        # 策略 1: 手动指定（不计入灰度统计）
        if preferred == RouteStrategy.HERMES:
            return self._pick_from_pool("hermes")
        if preferred == RouteStrategy.OPENCLAW:
            return self._pick_from_pool("openclaw")

        # 策略 2: 标签匹配（不计入灰度统计）
        if "planning" in tags:
            node = self._pick_from_pool("hermes")
            if node:
                return node
        if "tool-heavy" in tags:
            node = self._pick_from_pool("openclaw")
            if node:
                return node

        # 策略 3: 灰度比例（全局 canary_ratio）
        cluster = self._canary_choice()
        if cluster:
            self.request_counts[cluster] = self.request_counts.get(cluster, 0) + 1
            node = self._pick_from_pool(cluster)
            if node:
                return node

        # 策略 4: 权重随机兜底
        node = self._weighted_random()
        if node:
            self.request_counts[node.cluster] = self.request_counts.get(node.cluster, 0) + 1
        return node

    def _canary_choice(self) -> str | None:
        """根据全局 canary_ratio 返回目标集群名"""
        if self.canary_ratio <= 0:
            return self.default_target
        if self.canary_ratio >= 1.0:
            return self.canary_target
        
        if random.random() < self.canary_ratio:
            return self.canary_target
        return self.default_target

    def set_canary(self, ratio: float, target: str = "hermes"):
        """动态设置灰度比例和 canary 目标"""
        self.canary_ratio = max(0.0, min(1.0, ratio))
        self.canary_target = target
        self.default_target = "openclaw" if target == "hermes" else "hermes"

    def get_canary_status(self) -> dict:
        """返回当前灰度状态"""
        total = sum(self.request_counts.values())
        return {
            "canary_ratio": self.canary_ratio,
            "canary_target": self.canary_target,
            "default_target": self.default_target,
            "request_counts": self.request_counts,
            "total_canary_requests": total,
        }

    def reset_counts(self):
        """重置请求计数"""
        self.request_counts = {"hermes": 0, "openclaw": 0}

    def _pick_from_pool(self, cluster: str) -> Node | None:
        """从指定集群的健康节点中按权重选一个"""
        pool = self.registry.get_pool(cluster)
        if not pool:
            return None
        healthy = pool.healthy_nodes()
        if not healthy:
            return None
        return self._weighted_choice(healthy)

    def _weighted_random(self) -> Node | None:
        """从所有健康节点中按权重随机选"""
        all_nodes = self.registry.all_healthy_nodes()
        if not all_nodes:
            return None
        return self._weighted_choice(all_nodes)

    @staticmethod
    def _weighted_choice(nodes: list[Node]) -> Node:
        """按权重加权随机选择"""
        total = sum(n.weight for n in nodes)
        r = random.uniform(0, total)
        cumulative = 0
        for node in nodes:
            cumulative += node.weight
            if r <= cumulative:
                return node
        return nodes[-1]
