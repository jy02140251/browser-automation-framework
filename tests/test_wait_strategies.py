"""Tests for wait strategy utilities."""

import pytest
import asyncio
from automation.wait_strategies import WaitStrategies, WaitCondition


class TestRetryUntil:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        call_count = 0
        async def action():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await WaitStrategies.retry_until(action, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_retry(self):
        call_count = 0
        async def action():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("not ready")
            return "ok"

        result = await WaitStrategies.retry_until(action, max_retries=3, delay=0.01)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self):
        async def always_fails():
            raise ValueError("permanent error")

        with pytest.raises(ValueError, match="permanent error"):
            await WaitStrategies.retry_until(always_fails, max_retries=2, delay=0.01)


class TestWaitConditionEnum:
    def test_conditions_exist(self):
        assert WaitCondition.VISIBLE.value == "visible"
        assert WaitCondition.HIDDEN.value == "hidden"
        assert WaitCondition.ATTACHED.value == "attached"
        assert WaitCondition.DETACHED.value == "detached"
        assert WaitCondition.STABLE.value == "stable"

    def test_all_conditions(self):
        conditions = list(WaitCondition)
        assert len(conditions) == 5