"""
Anti-Detection Module.

Implements browser fingerprint masking techniques to avoid
bot detection systems. Includes WebGL noise, navigator
overrides, and user agent rotation.
"""

import random
import logging
from typing import Dict, Optional, List

from playwright.async_api import Page
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Common screen resolutions for realism
COMMON_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864),
    (1440, 900), (1280, 720), (2560, 1440),
]

# WebGL vendor/renderer pairs
WEBGL_CONFIGS = [
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce GTX 1060)"),
    ("Google Inc. (AMD)", "ANGLE (AMD Radeon RX 580)"),
    ("Google Inc. (Intel)", "ANGLE (Intel HD Graphics 630)"),
]


class AntiDetect:
    """
    Anti-detection configuration for browser fingerprint masking.

    Applies various techniques to make automated browsing appear
    as regular user traffic to bot detection systems.

    Args:
        custom_user_agent: Override the randomly generated user agent.
        enable_webgl_noise: Add noise to WebGL fingerprinting.
        enable_canvas_noise: Add noise to canvas fingerprinting.

    Example:
        >>> anti = AntiDetect(enable_webgl_noise=True)
        >>> ua = anti.get_user_agent()
        >>> await anti.apply_to_page(page)
    """

    def __init__(
        self,
        custom_user_agent: Optional[str] = None,
        enable_webgl_noise: bool = True,
        enable_canvas_noise: bool = True,
    ):
        self._ua_generator = UserAgent()
        self._custom_ua = custom_user_agent
        self._enable_webgl = enable_webgl_noise
        self._enable_canvas = enable_canvas_noise
        self._webgl_config = random.choice(WEBGL_CONFIGS)
        self._resolution = random.choice(COMMON_RESOLUTIONS)

    @property
    def extra_headers(self) -> Dict[str, str]:
        """Generate realistic HTTP headers."""
        return {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

    def get_user_agent(self) -> str:
        """Get a realistic user agent string."""
        if self._custom_ua:
            return self._custom_ua
        return self._ua_generator.chrome

    async def apply_to_page(self, page: Page) -> None:
        """
        Apply all anti-detection measures to a page.

        Injects JavaScript to override browser APIs commonly
        used for bot detection.

        Args:
            page: Playwright page to configure.
        """
        scripts = []

        # Override navigator.webdriver
        scripts.append("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        # Override navigator.plugins (appear to have plugins)
        scripts.append("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Override navigator.languages
        scripts.append("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

        # Chrome runtime mock
        scripts.append("""
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {},
            };
        """)

        # Override permissions query
        scripts.append("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);
        """)

        # WebGL fingerprint masking
        if self._enable_webgl:
            vendor, renderer = self._webgl_config
            scripts.append(f"""
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) return '{vendor}';
                    if (parameter === 37446) return '{renderer}';
                    return getParameter.call(this, parameter);
                }};
            """)

        # Canvas fingerprint noise
        if self._enable_canvas:
            scripts.append("""
                const toBlob = HTMLCanvasElement.prototype.toBlob;
                const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toBlob = function() {
                    const context = this.getContext('2d');
                    if (context) {
                        const shift = { r: Math.floor(Math.random() * 10) - 5,
                                       g: Math.floor(Math.random() * 10) - 5,
                                       b: Math.floor(Math.random() * 10) - 5 };
                        const width = this.width, height = this.height;
                        if (width && height) {
                            const imageData = context.getImageData(0, 0, Math.min(width, 10), 1);
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                imageData.data[i] += shift.r;
                            }
                            context.putImageData(imageData, 0, 0);
                        }
                    }
                    return toBlob.apply(this, arguments);
                };
            """)

        # Apply all scripts via init script
        combined_script = "\n".join(scripts)
        await page.add_init_script(combined_script)

        logger.info("Anti-detection measures applied to page")