"""路由策略引擎 — 支持手动指定、标签匹配、灰度权重三种策略"""
import random
from router.models import AgentRequest, RouteStrategy
from router.registry import NodeRegistry, Node


class RoutingEngine:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    def select_node(self, req: AgentRequest) -> Node | None:
        """
        根据请求的 routing.preferred 和 task.tags 选择目标节点
        
        优先级:
        1. 手动指定 (preferred=openclaw|hermes)
        2. 标签匹配 (tags 包含 planning → hermes, tool-heavy → openclaw)
        3. 灰度权重 (canary_ratio)
        4. 按权重随机选择
        """
        preferred = req.routing.preferred
        tags = req.task.tags
        canary_ratio = req.routing.canary_ratio

        # 策略 1: 手动指定
        if preferred == RouteStrategy.HERMES:
            return self._pick_from_pool("hermes")
        if preferred == RouteStrategy.OPENCLAW:
            return self._pick_from_pool("openclaw")

        # 策略 2: 标签匹配
        if "planning" in tags:
            node = self._pick_from_pool("hermes")
            if node:
                return node
        if "tool-heavy" in tags:
            node = self._pick_from_pool("openclaw")
            if node:
                return node

        # 策略 3: 灰度比例
        if canary_ratio > 0 and random.random() < canary_ratio:
            node = self._pick_from_pool("hermes")
            if node:
                return node

        # 策略 4: 权重随机（默认均匀）
        return self._weighted_random()

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
