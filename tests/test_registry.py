"""NodeRegistry 单元测试"""
import pytest
import sys
sys.path.insert(0, "/srv/agent-cluster")


class TestNodeRegistry:
    def test_loads_both_pools(self, registry):
        assert "openclaw" in registry.pools
        assert "hermes" in registry.pools

    def test_openclaw_pool_has_nodes(self, registry):
        pool = registry.get_pool("openclaw")
        assert pool is not None
        assert len(pool.nodes) >= 1
        assert pool.nodes[0].name == "oc-1"

    def test_hermes_pool_has_nodes(self, registry):
        pool = registry.get_pool("hermes")
        assert pool is not None
        assert len(pool.nodes) >= 1
        assert pool.nodes[0].name == "hm-1"

    def test_get_pool_missing(self, registry):
        assert registry.get_pool("nonexistent") is None

    def test_get_node_by_name(self, registry):
        node = registry.get_node("openclaw", "oc-1")
        assert node is not None
        assert node.base_url == "http://127.0.0.1:8082"

    def test_get_node_missing(self, registry):
        assert registry.get_node("openclaw", "nonexistent") is None

    def test_all_healthy_nodes_initially(self, registry):
        nodes = registry.all_healthy_nodes()
        # oc-1 + hm-1 are healthy; oc-2, hm-2, hm-3 are unhealthy
        assert len(nodes) == 2

    def test_mark_unhealthy(self, registry):
        pool = registry.get_pool("openclaw")
        pool.mark_unhealthy("oc-1")
        assert pool.nodes[0].healthy is False
        assert pool.nodes[0].failure_count == 1

    def test_mark_unhealthy_filters_from_healthy_list(self, registry):
        pool = registry.get_pool("openclaw")
        pool.mark_unhealthy("oc-1")
        healthy = registry.all_healthy_nodes("openclaw")
        assert len(healthy) == 0

    def test_mark_healthy_restores(self, registry):
        pool = registry.get_pool("openclaw")
        pool.mark_unhealthy("oc-1")
        pool.mark_healthy("oc-1")
        assert pool.nodes[0].healthy is True
        assert pool.nodes[0].failure_count == 0

    def test_list_all(self, registry):
        nodes = registry.list_all()
        assert len(nodes) == 5  # oc-1, oc-2, hm-1, hm-2, hm-3
        names = {n["name"] for n in nodes}
        assert names == {"oc-1", "oc-2", "hm-1", "hm-2", "hm-3"}

    def test_health_config_loaded(self, registry):
        assert registry.health_config["interval_seconds"] == 10
        assert registry.health_config["failure_threshold"] == 3

    def test_routing_config_loaded(self, registry):
        assert "default_strategy" in registry.routing_config
