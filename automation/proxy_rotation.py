"""
Proxy Rotation Module.

Manages a pool of proxy servers with health monitoring
and multiple rotation strategies for browser automation.
"""

import time
import random
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """Information about a single proxy server."""
    url: str
    is_healthy: bool = True
    latency_ms: float = 0.0
    fail_count: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0


class ProxyRotation:
    """
    Proxy pool manager with health monitoring and rotation.

    Maintains a pool of proxies, checks their health periodically,
    and rotates between healthy proxies for each request.

    Args:
        proxies: List of proxy URLs.
        check_url: URL to use for health checks.
        check_interval: Seconds between health checks.
        max_failures: Max failures before marking proxy as unhealthy.

    Example:
        >>> rotation = ProxyRotation(proxies=["http://1.2.3.4:8080"])
        >>> proxy = rotation.get_next()
        >>> await rotation.health_check()
    """

    def __init__(
        self,
        proxies: List[str],
        check_url: str = "https://httpbin.org/ip",
        check_interval: int = 300,
        max_failures: int = 3,
    ):
        self._proxies: List[ProxyInfo] = [
            ProxyInfo(url=url) for url in proxies
        ]
        self.check_url = check_url
        self.check_interval = check_interval
        self.max_failures = max_failures
        self._index: int = 0
        self._stats: Dict[str, int] = {"rotations": 0, "failures": 0}

    def get_next(self, strategy: str = "round_robin") -> Optional[str]:
        """
        Get the next proxy URL using the specified strategy.

        Args:
            strategy: Rotation strategy ('round_robin', 'random', 'least_used').

        Returns:
            Proxy URL string or None if no healthy proxies.
        """
        healthy = [p for p in self._proxies if p.is_healthy]
        if not healthy:
            logger.warning("No healthy proxies available")
            return None

        if strategy == "random":
            proxy = random.choice(healthy)
        elif strategy == "least_used":
            proxy = min(healthy, key=lambda p: p.last_used)
        else:  # round_robin
            self._index = self._index % len(healthy)
            proxy = healthy[self._index]
            self._index += 1

        proxy.last_used = time.time()
        self._stats["rotations"] += 1
        logger.debug("Proxy selected: %s", proxy.url)
        return proxy.url

    def report_failure(self, proxy_url: str) -> None:
        """Report a proxy failure to update health status."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.fail_count += 1
                self._stats["failures"] += 1
                if proxy.fail_count >= self.max_failures:
                    proxy.is_healthy = False
                    logger.warning("Proxy marked unhealthy: %s", proxy_url)
                break

    def report_success(self, proxy_url: str) -> None:
        """Report a proxy success to reset failure count."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.fail_count = 0
                proxy.is_healthy = True
                break

    async def health_check(self) -> Dict[str, int]:
        """
        Run health check on all proxies.

        Returns:
            Dict with 'healthy' and 'unhealthy' counts.
        """
        tasks = [self._check_single(p) for p in self._proxies]
        await asyncio.gather(*tasks, return_exceptions=True)

        healthy = sum(1 for p in self._proxies if p.is_healthy)
        result = {"healthy": healthy, "unhealthy": len(self._proxies) - healthy}
        logger.info("Health check: %d/%d healthy", healthy, len(self._proxies))
        return result

    async def _check_single(self, proxy: ProxyInfo) -> None:
        """Check a single proxy's health."""
        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.check_url, proxy=proxy.url) as resp:
                    if resp.status == 200:
                        proxy.latency_ms = (time.time() - start) * 1000
                        proxy.is_healthy = True
                        proxy.fail_count = 0
                        proxy.last_checked = time.time()
                        return
        except Exception as e:
            logger.debug("Health check failed for %s: %s", proxy.url, str(e))

        proxy.fail_count += 1
        if proxy.fail_count >= self.max_failures:
            proxy.is_healthy = False
        proxy.last_checked = time.time()

    @property
    def pool_size(self) -> int:
        """Total number of proxies in pool."""
        return len(self._proxies)

    @property
    def healthy_count(self) -> int:
        """Number of healthy proxies."""
        return sum(1 for p in self._proxies if p.is_healthy)

    @property
    def stats(self) -> Dict[str, int]:
        """Get rotation statistics."""
        return {**self._stats, "pool_size": self.pool_size, "healthy": self.healthy_count}