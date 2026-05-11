"""健康检查 — 定期探测节点存活和就绪状态"""
import asyncio
import httpx
import time
from router.registry import NodeRegistry


class HealthChecker:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self._task: asyncio.Task | None = None

    async def start(self):
        """后台启动健康检查循环"""
        interval = self.registry.health_config.get("interval_seconds", 10)
        self._task = asyncio.create_task(self._loop(interval))
        print(f"[health] Started, interval={interval}s")

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self, interval: int):
        while True:
            await self._check_all()
            await asyncio.sleep(interval)

    async def _check_all(self):
        threshold = self.registry.health_config.get("failure_threshold", 3)
        async with httpx.AsyncClient(timeout=5) as client:
            for pool in self.registry.pools.values():
                for node in pool.nodes:
                    healthy = await self._probe_node(client, node)
                    if healthy:
                        if not node.healthy:
                            print(f"[health] {node.cluster}/{node.name} RECOVERED")
                        pool.mark_healthy(node.name)
                    else:
                        node.failure_count += 1
                        if node.failure_count >= threshold:
                            if node.healthy:
                                print(f"[health] {node.cluster}/{node.name} UNHEALTHY (failures={node.failure_count})")
                            pool.mark_unhealthy(node.name)
                    node.last_check = time.time()

    async def _probe_node(self, client: httpx.AsyncClient, node) -> bool:
        """探测单个节点"""
        try:
            resp = await client.get(f"{node.base_url}/health")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("ready", False)
            return False
        except Exception:
            return False
