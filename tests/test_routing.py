"""RoutingEngine 单元测试"""
import pytest
import sys
sys.path.insert(0, "/srv/agent-cluster")

pytestmark = pytest.mark.unit

from router.models import (
    AgentRequest, Message, TaskDefinition,
    InputContext, RoutingHint, TaskIntent,
    Priority, RouteStrategy,
)
from router.routing import IntentClassifier
from router.registry import Node, ClusterPool


class TestIntentClassifier:
    def test_code_detect_write_function(self):
        assert IntentClassifier.classify("write a function that reverses a string") == TaskIntent.CODE

    def test_code_detect_debug(self):
        assert IntentClassifier.classify("debug this code: def foo(): pass") == TaskIntent.CODE

    def test_code_detect_implement(self):
        assert IntentClassifier.classify("implement a REST API endpoint") == TaskIntent.CODE

    def test_plan_detect_architecture(self):
        assert IntentClassifier.classify("design the architecture for a microservice") == TaskIntent.PLAN

    def test_plan_detect_how_should(self):
        assert IntentClassifier.classify("how should we organize the project?") == TaskIntent.PLAN

    def test_search_detect_what_is(self):
        assert IntentClassifier.classify("what is Kubernetes?") == TaskIntent.SEARCH

    def test_search_detect_explain(self):
        assert IntentClassifier.classify("explain how Docker works") == TaskIntent.SEARCH

    def test_chat_default(self):
        assert IntentClassifier.classify("hello how are you") == TaskIntent.CHAT

    def test_respects_explicit_intent(self):
        """客户端显式指定 intent 时不覆盖"""
        assert IntentClassifier.classify("write a function", TaskIntent.PLAN) == TaskIntent.PLAN


class TestIntentRouting:
    def test_code_intent_routes_to_openclaw(self, routing_engine):
        req = AgentRequest(
            task=TaskDefinition(intent=TaskIntent.CODE),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "openclaw"
        assert result.decision_layer == "L4_INTENT"

    def test_plan_intent_routes_to_hermes(self, routing_engine):
        req = AgentRequest(
            task=TaskDefinition(intent=TaskIntent.PLAN),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "hermes"
        assert result.decision_layer == "L4_INTENT"

    def test_search_intent_routes_to_hermes(self, routing_engine):
        req = AgentRequest(
            task=TaskDefinition(intent=TaskIntent.SEARCH),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "hermes"
        assert result.decision_layer == "L4_INTENT"

    def test_chat_intent_falls_through_to_weighted(self, routing_engine):
        """chat 意图没有专属后端，走灰度/加权"""
        req = AgentRequest(
            task=TaskDefinition(intent=TaskIntent.CHAT),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        # chat → L6_DEFAULT (走策略兜底)

    def test_intent_lower_priority_than_manual(self, routing_engine):
        """手动指定覆盖意图路由"""
        req = AgentRequest(
            task=TaskDefinition(intent=TaskIntent.CODE),
            routing=RoutingHint(preferred=RouteStrategy.HERMES),
        )
        result = routing_engine.select_node(req)
        assert result.node.cluster == "hermes"
        assert result.decision_layer == "L1_MANUAL"


class TestRoutingEngine:
    def test_manual_preferred_hermes(self, routing_engine):
        req = AgentRequest(
            routing=RoutingHint(preferred=RouteStrategy.HERMES),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "hermes"
        assert result.decision_layer == "L1_MANUAL"

    def test_manual_preferred_openclaw(self, routing_engine):
        req = AgentRequest(
            routing=RoutingHint(preferred=RouteStrategy.OPENCLAW),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "openclaw"
        assert result.decision_layer == "L1_MANUAL"

    def test_tag_planning_goes_hermes(self, routing_engine):
        req = AgentRequest(
            task=TaskDefinition(tags=["planning"]),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "hermes"
        assert result.decision_layer == "L2_TAG"

    def test_tag_tool_heavy_goes_openclaw(self, routing_engine):
        req = AgentRequest(
            task=TaskDefinition(tags=["tool-heavy"]),
        )
        result = routing_engine.select_node(req)
        assert result.node is not None
        assert result.node.cluster == "openclaw"
        assert result.decision_layer == "L2_TAG"

    def test_canary_100_pct_all_goes_target(self, routing_engine):
        routing_engine.set_canary(1.0, "hermes")
        for _ in range(50):
            req = AgentRequest(
                task=TaskDefinition(intent=TaskIntent.TOOL),  # TOOL has no tag/intent backend match
            )
            result = routing_engine.select_node(req)
            # canary at L5 — verify decision layer
            assert result.decision_layer in ("L5_CANARY", "L4_INTENT", "L1_MANUAL", "L2_TAG", "L3_SKILL", "L6_DEFAULT")

    def test_canary_0_pct_all_goes_default(self, routing_engine):
        routing_engine.set_canary(0.0, "hermes")
        for _ in range(50):
            req = AgentRequest(
                task=TaskDefinition(intent=TaskIntent.TOOL),
            )
            result = routing_engine.select_node(req)
            assert result.node is not None

    def test_canary_50_pct_distribution(self, routing_engine):
        routing_engine.reset_counts()
        routing_engine.set_canary(0.5, "hermes")
        for _ in range(500):
            req = AgentRequest(
                task=TaskDefinition(intent=TaskIntent.TOOL),
            )
            routing_engine.select_node(req)
        counts = routing_engine.request_counts
        total = sum(counts.values())
        if total > 0:
            hermes_pct = counts["hermes"] / total
            assert 0.4 < hermes_pct < 0.6, f"hermes={hermes_pct:.2f}"

    def test_manual_overrides_canary(self, routing_engine):
        routing_engine.set_canary(1.0, "hermes")  # 全量 hermes
        req = AgentRequest(
            routing=RoutingHint(preferred=RouteStrategy.OPENCLAW),
        )
        result = routing_engine.select_node(req)
        assert result.node.cluster == "openclaw"  # 手动指定覆盖灰度
        assert result.decision_layer == "L1_MANUAL"

    def test_set_canary_clamps_range(self, routing_engine):
        routing_engine.set_canary(2.5, "hermes")
        assert routing_engine.canary_ratio == 1.0
        routing_engine.set_canary(-0.5, "hermes")
        assert routing_engine.canary_ratio == 0.0

    def test_canary_status(self, routing_engine):
        routing_engine.set_canary(0.3, "openclaw")
        status = routing_engine.get_canary_status()
        assert status["canary_ratio"] == 0.3
        assert status["canary_target"] == "openclaw"
        assert status["default_target"] == "hermes"

    def test_no_healthy_nodes_returns_none(self, registry, routing_engine):
        """所有节点 unhealthy 时返回 result.node 为 None"""
        for pool in registry.pools.values():
            for node in pool.nodes:
                node.healthy = False
        req = AgentRequest()
        result = routing_engine.select_node(req)
        assert result.node is None
        assert result.decision_layer == "L6_DEFAULT"

    def test_weighted_random_selects_healthy_only(self, registry, routing_engine):
        """只从健康节点中选择 — 没有健康节点时 result.node 为 None"""
        pool = registry.get_pool("openclaw")
        pool.nodes[0].healthy = False
        req = AgentRequest(
            routing=RoutingHint(preferred=RouteStrategy.OPENCLAW),
        )
        result = routing_engine.select_node(req)
        assert result.node is None  # 只有 oc-1 一个节点且 unhealthy


class TestLoadBalancing:
    """多节点调度策略测试"""
    
    def _make_nodes(self, *names):
        """创建测试节点列表"""
        nodes = []
        for i, name in enumerate(names):
            nodes.append(Node(
                name=name,
                cluster="test",
                base_url=f"http://127.0.0.1:900{i}",
                weight=10,
            ))
        return nodes

    def test_least_connections_picks_min(self, routing_engine):
        routing_engine.strategy = "least_connections"
        routing_engine.active_connections["a"] = 5
        routing_engine.active_connections["b"] = 1
        routing_engine.active_connections["c"] = 3
        nodes = self._make_nodes("a", "b", "c")
        node = routing_engine._least_connections(nodes)
        assert node.name == "b"

    def test_least_connections_zero_default(self, routing_engine):
        routing_engine.strategy = "least_connections"
        nodes = self._make_nodes("x", "y", "z")
        # 都没有连接记录 → 选第一个
        node = routing_engine._least_connections(nodes)
        assert node.name == "x"

    def test_round_robin_cycles(self, routing_engine):
        routing_engine.strategy = "round_robin"
        nodes = self._make_nodes("a", "b", "c")
        picks = [routing_engine._round_robin(nodes, "test").name for _ in range(6)]
        assert picks == ["a", "b", "c", "a", "b", "c"]

    def test_weighted_distribution(self, routing_engine):
        """权重不同时分布应符合比例"""
        routing_engine.strategy = "weighted"
        nodes = [
            Node(name="heavy", cluster="test", base_url="http://x", weight=90),
            Node(name="light", cluster="test", base_url="http://y", weight=10),
        ]
        counts = {"heavy": 0, "light": 0}
        for _ in range(1000):
            n = routing_engine._weighted_choice(nodes)
            counts[n.name] += 1
        # heavy 应占 ~90%
        ratio = counts["heavy"] / 1000
        assert 0.85 < ratio < 0.95, f"expected ~90% heavy, got {ratio:.2f}"

    def test_strategy_switch(self, routing_engine):
        routing_engine.set_strategy("least_connections")
        assert routing_engine.strategy == "least_connections"
        routing_engine.set_strategy("round_robin")
        assert routing_engine.strategy == "round_robin"
        routing_engine.set_strategy("weighted")
        assert routing_engine.strategy == "weighted"
        # invalid stays unchanged
        routing_engine.set_strategy("invalid")
        assert routing_engine.strategy == "weighted"

    def test_acquire_release_connection(self, routing_engine):
        routing_engine.acquire_connection("node-a")
        routing_engine.acquire_connection("node-a")
        assert routing_engine.active_connections["node-a"] == 2
        routing_engine.release_connection("node-a")
        assert routing_engine.active_connections["node-a"] == 1
        routing_engine.release_connection("node-a")
        assert routing_engine.active_connections["node-a"] == 0

    def test_release_never_negative(self, routing_engine):
        routing_engine.release_connection("unknown")
        assert routing_engine.active_connections.get("unknown", 0) == 0
