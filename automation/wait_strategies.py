"""Advanced wait strategies for reliable browser automation."""

import asyncio
import logging
import time
from typing import Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class WaitCondition(Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    ATTACHED = "attached"
    DETACHED = "detached"
    STABLE = "stable"


class WaitStrategies:
    """Collection of advanced wait strategies for page interactions."""

    @staticmethod
    async def wait_for_network_idle(page, timeout: int = 30000, idle_time: int = 500):
        """Wait until no network requests are made for the specified idle time."""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            logger.warning("Network idle timeout reached, proceeding anyway")

    @staticmethod
    async def wait_for_element(
        page,
        selector: str,
        condition: WaitCondition = WaitCondition.VISIBLE,
        timeout: int = 10000,
    ):
        """Wait for an element to match the specified condition."""
        state_map = {
            WaitCondition.VISIBLE: "visible",
            WaitCondition.HIDDEN: "hidden",
            WaitCondition.ATTACHED: "attached",
            WaitCondition.DETACHED: "detached",
        }
        state = state_map.get(condition, "visible")
        return await page.wait_for_selector(selector, state=state, timeout=timeout)

    @staticmethod
    async def wait_for_text(page, text: str, timeout: int = 10000):
        """Wait for specific text to appear on the page."""
        try:
            await page.wait_for_function(
                f'document.body.innerText.includes("{text}")',
                timeout=timeout,
            )
            return True
        except Exception:
            return False

    @staticmethod
    async def wait_for_url_change(page, current_url: str, timeout: int = 10000):
        """Wait until the page URL changes from the current one."""
        try:
            await page.wait_for_function(
                f'window.location.href !== "{current_url}"',
                timeout=timeout,
            )
            return page.url
        except Exception:
            return None

    @staticmethod
    async def wait_for_dom_stable(page, poll_interval: float = 0.5, stability_time: float = 2.0):
        """Wait until DOM structure stops changing."""
        prev_html = ""
        stable_since = 0.0

        for _ in range(int(30 / poll_interval)):
            current_html = await page.content()
            if current_html == prev_html:
                if stable_since == 0:
                    stable_since = time.time()
                elif time.time() - stable_since >= stability_time:
                    logger.debug("DOM is stable")
                    return True
            else:
                stable_since = 0
                prev_html = current_html
            await asyncio.sleep(poll_interval)

        logger.warning("DOM stability timeout reached")
        return False

    @staticmethod
    async def retry_until(
        action: Callable,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
    ) -> Any:
        """Retry an action until it succeeds or max retries is reached."""
        last_error = None
        current_delay = delay

        for attempt in range(max_retries):
            try:
                result = await action()
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

        raise last_error