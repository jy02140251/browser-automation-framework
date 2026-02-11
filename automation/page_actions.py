"""
Page Actions Module.

High-level utilities for common page interactions like
form filling, scrolling, waiting, and element extraction.
"""

import asyncio
import random
import logging
from typing import Optional, List, Dict, Any

from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class PageActions:
    """
    High-level page interaction utilities.

    Provides human-like interaction methods with random delays
    and realistic typing patterns.

    Args:
        page: Playwright Page instance.
        human_like: Enable human-like delays and typing.
    """

    def __init__(self, page: Page, human_like: bool = True):
        self.page = page
        self.human_like = human_like

    async def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
    ) -> None:
        """
        Type text into an input field with human-like delays.

        Args:
            selector: CSS selector for the input field.
            text: Text to type.
            clear_first: Clear existing content before typing.
        """
        element = self.page.locator(selector)
        await element.click()

        if clear_first:
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.press("Backspace")
            await self._random_delay(100, 300)

        if self.human_like:
            for char in text:
                await self.page.keyboard.type(char)
                await self._random_delay(50, 150)
        else:
            await element.fill(text)

        logger.debug("Typed text into %s", selector)

    async def click_element(
        self,
        selector: str,
        wait_after: bool = True,
    ) -> None:
        """
        Click an element with optional post-click delay.

        Args:
            selector: CSS selector for the element.
            wait_after: Wait a random delay after clicking.
        """
        element = self.page.locator(selector)
        await element.wait_for(state="visible")

        if self.human_like:
            await self._random_delay(200, 500)

        await element.click()

        if wait_after:
            await self._random_delay(500, 1500)

        logger.debug("Clicked element: %s", selector)

    async def scroll_page(
        self,
        direction: str = "down",
        amount: int = 500,
        smooth: bool = True,
    ) -> None:
        """
        Scroll the page in a specified direction.

        Args:
            direction: Scroll direction ('down', 'up', 'bottom', 'top').
            amount: Pixel amount for incremental scrolling.
            smooth: Enable smooth scrolling behavior.
        """
        if direction == "bottom":
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "top":
            await self.page.evaluate("window.scrollTo(0, 0)")
        else:
            delta = amount if direction == "down" else -amount
            if smooth:
                steps = 5
                step_amount = delta // steps
                for _ in range(steps):
                    await self.page.mouse.wheel(0, step_amount)
                    await self._random_delay(50, 150)
            else:
                await self.page.mouse.wheel(0, delta)

        await self._random_delay(300, 700)
        logger.debug("Scrolled %s by %dpx", direction, amount)

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10000,
        state: str = "visible",
    ) -> Optional[Locator]:
        """
        Wait for an element to reach a specific state.

        Args:
            selector: CSS selector.
            timeout: Max wait time in ms.
            state: Expected state ('visible', 'hidden', 'attached').

        Returns:
            Locator if found, None on timeout.
        """
        try:
            element = self.page.locator(selector)
            await element.wait_for(state=state, timeout=timeout)
            return element
        except Exception:
            logger.warning("Element not found: %s (timeout: %dms)", selector, timeout)
            return None

    async def extract_text(self, selector: str) -> List[str]:
        """Extract text content from all matching elements."""
        elements = self.page.locator(selector)
        count = await elements.count()
        texts = []
        for i in range(count):
            text = await elements.nth(i).text_content()
            if text:
                texts.append(text.strip())
        return texts

    async def fill_form(self, fields: Dict[str, str]) -> None:
        """
        Fill a form with multiple fields.

        Args:
            fields: Dict mapping CSS selectors to values.
        """
        for selector, value in fields.items():
            await self.type_text(selector, value)
            await self._random_delay(200, 500)
        logger.info("Form filled with %d fields", len(fields))

    async def _random_delay(self, min_ms: int, max_ms: int) -> None:
        """Add a random delay for human-like behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)