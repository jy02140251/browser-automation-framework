"""
Core Browser Management Module.

Provides the main Browser class for creating and managing
Playwright browser instances with proxy and anti-detection support.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser as PWBrowser, Page, BrowserContext

from automation.anti_detect import AntiDetect
from automation.proxy_rotation import ProxyRotation

logger = logging.getLogger(__name__)


class Browser:
    """
    Main browser automation controller.

    Manages Playwright browser lifecycle with integrated
    proxy rotation and anti-detection features.

    Args:
        headless: Run browser in headless mode.
        browser_type: Browser engine ('chromium', 'firefox', 'webkit').
        proxy_rotation: Optional ProxyRotation instance.
        user_data_dir: Optional persistent browser profile directory.
        timeout: Default navigation timeout in milliseconds.

    Example:
        >>> async with Browser(headless=True) as browser:
        ...     page = await browser.new_page()
        ...     await page.goto("https://example.com")
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        proxy_rotation: Optional[ProxyRotation] = None,
        user_data_dir: Optional[str] = None,
        timeout: int = 30000,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.proxy_rotation = proxy_rotation
        self.user_data_dir = user_data_dir
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional[PWBrowser] = None
        self._contexts: List[BrowserContext] = []

    async def __aenter__(self):
        """Async context manager entry - launch browser."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close browser."""
        await self.close()

    async def launch(self) -> None:
        """Launch the Playwright browser instance."""
        self._playwright = await async_playwright().start()

        launcher = getattr(self._playwright, self.browser_type)
        launch_options: Dict[str, Any] = {
            "headless": self.headless,
        }

        # Add proxy if available
        if self.proxy_rotation:
            proxy = self.proxy_rotation.get_next()
            if proxy:
                launch_options["proxy"] = {"server": proxy}
                logger.info("Launching browser with proxy: %s", proxy)

        self._browser = await launcher.launch(**launch_options)
        logger.info(
            "Browser launched: %s (headless=%s)",
            self.browser_type,
            self.headless,
        )

    async def new_page(
        self,
        anti_detect: Optional[AntiDetect] = None,
        viewport: Optional[Dict[str, int]] = None,
        locale: str = "en-US",
        timezone: Optional[str] = None,
    ) -> Page:
        """
        Create a new browser page with optional anti-detection.

        Args:
            anti_detect: AntiDetect instance for fingerprint masking.
            viewport: Custom viewport size {'width': int, 'height': int}.
            locale: Browser locale setting.
            timezone: Timezone override.

        Returns:
            Configured Playwright Page instance.
        """
        if not self._browser:
            raise RuntimeError("Browser not launched. Call launch() first.")

        context_options: Dict[str, Any] = {
            "viewport": viewport or {"width": 1920, "height": 1080},
            "locale": locale,
            "ignore_https_errors": True,
        }

        if timezone:
            context_options["timezone_id"] = timezone

        # Apply anti-detection settings
        if anti_detect:
            context_options["user_agent"] = anti_detect.get_user_agent()
            if anti_detect.extra_headers:
                context_options["extra_http_headers"] = anti_detect.extra_headers

        # Set proxy for this context if rotation enabled
        if self.proxy_rotation:
            proxy = self.proxy_rotation.get_next()
            if proxy:
                context_options["proxy"] = {"server": proxy}

        context = await self._browser.new_context(**context_options)
        self._contexts.append(context)

        page = await context.new_page()
        page.set_default_timeout(self.timeout)

        # Inject anti-detection scripts
        if anti_detect:
            await anti_detect.apply_to_page(page)

        logger.debug("New page created with viewport %s", context_options["viewport"])
        return page

    async def screenshot(
        self,
        page: Page,
        path: str,
        full_page: bool = False,
        element_selector: Optional[str] = None,
    ) -> str:
        """
        Take a screenshot of the page or specific element.

        Args:
            page: Target page.
            path: Output file path.
            full_page: Capture full scrollable page.
            element_selector: CSS selector for element screenshot.

        Returns:
            Path to the saved screenshot.
        """
        if element_selector:
            element = page.locator(element_selector)
            await element.screenshot(path=path)
        else:
            await page.screenshot(path=path, full_page=full_page)

        logger.info("Screenshot saved: %s", path)
        return path

    async def close(self) -> None:
        """Close all contexts and the browser."""
        for context in self._contexts:
            await context.close()
        self._contexts.clear()

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Browser closed")

    @property
    def is_running(self) -> bool:
        """Check if browser is currently running."""
        return self._browser is not None and self._browser.is_connected()