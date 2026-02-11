"""
Screenshot Management Module.

Provides utilities for taking, comparing, and managing
screenshots during browser automation tasks.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """
    Screenshot utility for browser automation.

    Manages screenshot capture, storage, and basic
    image comparison for visual regression detection.

    Args:
        output_dir: Directory for saving screenshots.
        format: Image format ('png' or 'jpeg').
        quality: JPEG quality (1-100), only for JPEG format.

    Example:
        >>> manager = ScreenshotManager(output_dir="./screenshots")
        >>> path = await manager.capture(page, "homepage")
        >>> is_same = await manager.compare(path, "baseline.png")
    """

    def __init__(
        self,
        output_dir: str = "./screenshots",
        format: str = "png",
        quality: int = 80,
    ):
        self.output_dir = Path(output_dir)
        self.format = format
        self.quality = quality
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def capture(
        self,
        page: Page,
        name: str,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> str:
        """
        Capture a screenshot with auto-generated filename.

        Args:
            page: Playwright Page to capture.
            name: Base name for the screenshot file.
            full_page: Capture full scrollable page.
            selector: CSS selector for element screenshot.

        Returns:
            Path to the saved screenshot file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.{self.format}"
        filepath = self.output_dir / filename

        screenshot_options = {
            "path": str(filepath),
            "type": self.format,
        }

        if self.format == "jpeg":
            screenshot_options["quality"] = self.quality

        if selector:
            element = page.locator(selector)
            await element.screenshot(**screenshot_options)
        else:
            screenshot_options["full_page"] = full_page
            await page.screenshot(**screenshot_options)

        logger.info("Screenshot saved: %s", filepath)
        return str(filepath)

    async def capture_element(
        self,
        page: Page,
        selector: str,
        name: str,
    ) -> Optional[str]:
        """
        Capture a screenshot of a specific element.

        Args:
            page: Playwright Page.
            selector: CSS selector for the target element.
            name: Base name for the file.

        Returns:
            File path or None if element not found.
        """
        try:
            element = page.locator(selector)
            await element.wait_for(state="visible", timeout=5000)
            return await self.capture(page, name, selector=selector)
        except Exception as e:
            logger.error("Failed to capture element %s: %s", selector, str(e))
            return None

    def compare(
        self,
        image_path_a: str,
        image_path_b: str,
        threshold: float = 0.95,
    ) -> Tuple[bool, float]:
        """
        Compare two screenshots for visual similarity.

        Uses pixel-by-pixel comparison with a similarity threshold.

        Args:
            image_path_a: Path to first image.
            image_path_b: Path to second image.
            threshold: Minimum similarity score (0.0-1.0).

        Returns:
            Tuple of (is_similar, similarity_score).
        """
        try:
            from PIL import Image
            import numpy as np

            img_a = np.array(Image.open(image_path_a).convert("RGB"))
            img_b = np.array(Image.open(image_path_b).convert("RGB"))

            if img_a.shape != img_b.shape:
                logger.warning("Image dimensions differ, cannot compare")
                return False, 0.0

            # Calculate similarity
            diff = np.abs(img_a.astype(float) - img_b.astype(float))
            max_diff = 255.0 * 3  # RGB channels
            similarity = 1.0 - (diff.sum() / (img_a.size * max_diff / 3))

            is_similar = similarity >= threshold
            logger.info(
                "Image comparison: %.2f%% similar (%s)",
                similarity * 100,
                "PASS" if is_similar else "FAIL",
            )
            return is_similar, round(similarity, 4)

        except ImportError:
            logger.error("Pillow and numpy required for image comparison")
            return False, 0.0

    def cleanup(self, max_age_hours: int = 24) -> int:
        """
        Remove screenshots older than max_age_hours.

        Returns:
            Number of files removed.
        """
        import time

        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0

        for filepath in self.output_dir.iterdir():
            if filepath.is_file() and filepath.stat().st_mtime < cutoff:
                filepath.unlink()
                removed += 1

        logger.info("Cleaned up %d old screenshots", removed)
        return removed