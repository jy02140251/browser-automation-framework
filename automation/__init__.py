"""
Browser Automation Framework.

A Playwright-based framework for browser automation with
anti-detection, proxy rotation, and CAPTCHA solving capabilities.
"""

from automation.browser import Browser
from automation.anti_detect import AntiDetect
from automation.proxy_rotation import ProxyRotation
from automation.captcha_solver import CaptchaSolver
from automation.page_actions import PageActions
from automation.screenshot import ScreenshotManager

__version__ = "1.0.0"

__all__ = [
    "Browser",
    "AntiDetect",
    "ProxyRotation",
    "CaptchaSolver",
    "PageActions",
    "ScreenshotManager",
]