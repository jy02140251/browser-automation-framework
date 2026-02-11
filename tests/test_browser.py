"""
Browser Automation Framework Tests.

Unit tests for proxy rotation, anti-detection configuration,
and screenshot management.
"""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from automation.proxy_rotation import ProxyRotation
from automation.anti_detect import AntiDetect
from automation.screenshot import ScreenshotManager


class TestProxyRotation:
    """Tests for proxy rotation module."""

    def test_round_robin_rotation(self):
        rotation = ProxyRotation(proxies=["http://a:80", "http://b:80", "http://c:80"])
        results = [rotation.get_next("round_robin") for _ in range(3)]
        assert results == ["http://a:80", "http://b:80", "http://c:80"]

    def test_report_failure_marks_unhealthy(self):
        rotation = ProxyRotation(
            proxies=["http://a:80"],
            max_failures=2,
        )
        rotation.report_failure("http://a:80")
        rotation.report_failure("http://a:80")
        assert rotation.get_next() is None

    def test_report_success_resets_failures(self):
        rotation = ProxyRotation(proxies=["http://a:80"], max_failures=3)
        rotation.report_failure("http://a:80")
        rotation.report_failure("http://a:80")
        rotation.report_success("http://a:80")
        assert rotation.get_next() is not None

    def test_empty_pool_returns_none(self):
        rotation = ProxyRotation(proxies=[])
        assert rotation.get_next() is None

    def test_pool_stats(self):
        rotation = ProxyRotation(proxies=["http://a:80", "http://b:80"])
        stats = rotation.stats
        assert stats["pool_size"] == 2
        assert stats["healthy"] == 2


class TestAntiDetect:
    """Tests for anti-detection module."""

    def test_get_user_agent_returns_string(self):
        anti = AntiDetect()
        ua = anti.get_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_custom_user_agent(self):
        custom_ua = "Custom/1.0"
        anti = AntiDetect(custom_user_agent=custom_ua)
        assert anti.get_user_agent() == custom_ua

    def test_extra_headers(self):
        anti = AntiDetect()
        headers = anti.extra_headers
        assert "Accept-Language" in headers
        assert "Sec-Fetch-Dest" in headers


class TestScreenshotManager:
    """Tests for screenshot manager."""

    def test_output_dir_creation(self, tmp_path):
        output_dir = str(tmp_path / "screenshots")
        manager = ScreenshotManager(output_dir=output_dir)
        assert os.path.exists(output_dir)

    def test_cleanup_empty_dir(self, tmp_path):
        manager = ScreenshotManager(output_dir=str(tmp_path))
        removed = manager.cleanup(max_age_hours=0)
        assert removed == 0