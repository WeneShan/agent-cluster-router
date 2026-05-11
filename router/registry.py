"""节点注册中心 — 管理 OpenClaw/Hermes 节点池"""
import yaml
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Node:
    name: str
    cluster: str  # "openclaw" | "hermes"
    base_url: str
    capability: list[str] = field(default_factory=list)
    weight: int = 10
    healthy: bool = True
    failure_count: int = 0
    last_check: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cluster": self.cluster,
            "base_url": self.base_url,
            "capability": self.capability,
            "weight": self.weight,
            "healthy": self.healthy,
            "failure_count": self.failure_count,
        }


@dataclass
class ClusterPool:
    name: str
    nodes: list[Node] = field(default_factory=list)

    def healthy_nodes(self) -> list[Node]:
        return [n for n in self.nodes if n.healthy]

    def mark_unhealthy(self, node_name: str):
        for n in self.nodes:
            if n.name == node_name:
                n.healthy = False
                n.failure_count += 1

    def mark_healthy(self, node_name: str):
        for n in self.nodes:
            if n.name == node_name:
                n.healthy = True
                n.failure_count = 0


class NodeRegistry:
    """全局节点注册中心"""

    def __init__(self, config_path: str = "/srv/agent-cluster/config.yaml"):
        self.config_path = Path(config_path)
        self.pools: dict[str, ClusterPool] = {}  # key: "openclaw" | "hermes"
        self.health_config: dict = {}
        self.routing_config: dict = {}
        self._load()

    def _load(self):
        """从 YAML 加载集群配置"""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        self.pools = {}
        for cluster_name, nodes_config in config.get("clusters", {}).items():
            pool = ClusterPool(name=cluster_name)
            for nc in nodes_config:
                pool.nodes.append(Node(cluster=cluster_name, **nc))
            self.pools[cluster_name] = pool

        self.health_config = config.get("health_check", {})
        self.routing_config = config.get("routing", {})

    def get_pool(self, cluster: str) -> Optional[ClusterPool]:
        return self.pools.get(cluster)

    def get_node(self, cluster: str, node_name: str) -> Optional[Node]:
        pool = self.pools.get(cluster)
        if pool:
            for n in pool.nodes:
                if n.name == node_name:
                    return n
        return None

    def all_healthy_nodes(self, cluster: Optional[str] = None) -> list[Node]:
        """获取所有健康节点，可按集群过滤"""
        nodes = []
        for name, pool in self.pools.items():
            if cluster and name != cluster:
                continue
            nodes.extend(pool.healthy_nodes())
        return nodes

    def list_all(self) -> list[dict]:
        return [n.to_dict() for pool in self.pools.values() for n in pool.nodes]
