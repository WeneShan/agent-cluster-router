"""共享 fixtures"""
import pytest
import sys
sys.path.insert(0, "/srv/agent-cluster")

from router.registry import NodeRegistry
from router.routing import RoutingEngine


@pytest.fixture
def registry():
    """返回一个已加载的 NodeRegistry 实例"""
    return NodeRegistry()


@pytest.fixture
def routing_engine(registry):
    """返回 RoutingEngine 实例"""
    return RoutingEngine(registry)
