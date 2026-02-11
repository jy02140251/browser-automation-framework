"""
Scraping Example.

Demonstrates how to use the browser automation framework
for a basic web scraping task with anti-detection.
"""

import asyncio
import logging

from automation import Browser, AntiDetect, ProxyRotation, PageActions, ScreenshotManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_example():
    """
    Example: Scrape quotes from a demo website.
    
    Demonstrates:
    - Browser launch with anti-detection
    - Page navigation and waiting
    - Element text extraction
    - Screenshot capture
    """
    # Setup components
    anti_detect = AntiDetect(enable_webgl_noise=True)
    screenshot_mgr = ScreenshotManager(output_dir="./output")

    # Optional: setup proxy rotation
    # proxy_pool = ProxyRotation(proxies=["http://proxy1:8080"])

    async with Browser(headless=True) as browser:
        # Create page with anti-detection
        page = await browser.new_page(anti_detect=anti_detect)
        actions = PageActions(page, human_like=True)

        # Navigate to target
        logger.info("Navigating to target page...")
        await page.goto("https://quotes.toscrape.com/")
        await page.wait_for_load_state("networkidle")

        # Take a screenshot
        await screenshot_mgr.capture(page, "quotes_page", full_page=True)

        # Extract quotes
        quotes = await actions.extract_text(".quote .text")
        authors = await actions.extract_text(".quote .author")

        logger.info("Found %d quotes:", len(quotes))
        for quote, author in zip(quotes, authors):
            logger.info("  %s - %s", quote[:80], author)

        # Navigate to next page
        next_btn = await actions.wait_for_element("li.next a")
        if next_btn:
            await next_btn.click()
            await page.wait_for_load_state("networkidle")
            logger.info("Navigated to page 2")

            # Extract more quotes
            more_quotes = await actions.extract_text(".quote .text")
            logger.info("Page 2: Found %d more quotes", len(more_quotes))

        logger.info("Scraping complete!")


if __name__ == "__main__":
    asyncio.run(scrape_example())