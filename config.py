"""
Framework Configuration.

Centralized configuration with environment variable support
and sensible defaults for browser automation.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrowserConfig:
    """Browser automation configuration."""

    # Browser settings
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    browser_type: str = os.getenv("BROWSER_TYPE", "chromium")
    timeout_ms: int = int(os.getenv("TIMEOUT_MS", "30000"))

    # Proxy settings
    proxy_list_file: Optional[str] = os.getenv("PROXY_LIST_FILE")
    proxy_check_url: str = os.getenv("PROXY_CHECK_URL", "https://httpbin.org/ip")
    proxy_check_interval: int = int(os.getenv("PROXY_CHECK_INTERVAL", "300"))

    # Anti-detection
    enable_anti_detect: bool = os.getenv("ANTI_DETECT", "true").lower() == "true"
    custom_user_agent: Optional[str] = os.getenv("USER_AGENT")

    # CAPTCHA solving
    captcha_service: str = os.getenv("CAPTCHA_SERVICE", "2captcha")
    captcha_api_key: Optional[str] = os.getenv("CAPTCHA_API_KEY")

    # Screenshots
    screenshot_dir: str = os.getenv("SCREENSHOT_DIR", "./screenshots")
    screenshot_format: str = os.getenv("SCREENSHOT_FORMAT", "png")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")


config = BrowserConfig()