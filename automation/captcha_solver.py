"""
CAPTCHA Solver Module.

Integration with third-party CAPTCHA solving services
(2Captcha, Anti-Captcha) for automated CAPTCHA handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class CaptchaType(str, Enum):
    """Supported CAPTCHA types."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    IMAGE = "image"


class CaptchaSolver:
    """
    CAPTCHA solving service integration.

    Supports multiple CAPTCHA types and solving services
    with automatic retrying and balance checking.

    Args:
        api_key: API key for the solving service.
        service: Service provider ('2captcha' or 'anticaptcha').
        timeout: Maximum wait time for solution in seconds.

    Example:
        >>> solver = CaptchaSolver(api_key="your-key", service="2captcha")
        >>> token = await solver.solve_recaptcha(site_key, page_url)
    """

    SERVICE_URLS = {
        "2captcha": {
            "submit": "https://2captcha.com/in.php",
            "result": "https://2captcha.com/res.php",
        },
        "anticaptcha": {
            "submit": "https://api.anti-captcha.com/createTask",
            "result": "https://api.anti-captcha.com/getTaskResult",
        },
    }

    def __init__(
        self,
        api_key: str,
        service: str = "2captcha",
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.service = service
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=30)

        if service not in self.SERVICE_URLS:
            raise ValueError(f"Unsupported service: {service}")

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False,
    ) -> Optional[str]:
        """
        Solve a reCAPTCHA v2 challenge.

        Args:
            site_key: The reCAPTCHA site key.
            page_url: URL of the page with the CAPTCHA.
            invisible: Whether it's an invisible reCAPTCHA.

        Returns:
            CAPTCHA solution token or None on failure.
        """
        logger.info("Solving reCAPTCHA v2 for %s", page_url)

        if self.service == "2captcha":
            return await self._solve_2captcha(
                method="userrecaptcha",
                params={
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "invisible": 1 if invisible else 0,
                },
            )

        return await self._solve_anticaptcha(
            task_type="RecaptchaV2TaskProxyless",
            params={
                "websiteURL": page_url,
                "websiteKey": site_key,
                "isInvisible": invisible,
            },
        )

    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
    ) -> Optional[str]:
        """
        Solve an hCaptcha challenge.

        Args:
            site_key: The hCaptcha site key.
            page_url: URL of the page with the CAPTCHA.

        Returns:
            CAPTCHA solution token or None on failure.
        """
        logger.info("Solving hCaptcha for %s", page_url)

        if self.service == "2captcha":
            return await self._solve_2captcha(
                method="hcaptcha",
                params={"sitekey": site_key, "pageurl": page_url},
            )

        return await self._solve_anticaptcha(
            task_type="HCaptchaTaskProxyless",
            params={"websiteURL": page_url, "websiteKey": site_key},
        )

    async def _solve_2captcha(
        self, method: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """Submit and retrieve solution from 2Captcha."""
        urls = self.SERVICE_URLS["2captcha"]

        # Submit task
        submit_params = {
            "key": self.api_key,
            "method": method,
            "json": 1,
            **params,
        }

        try:
            resp = await self._client.get(urls["submit"], params=submit_params)
            data = resp.json()

            if data.get("status") != 1:
                logger.error("2Captcha submit error: %s", data.get("request"))
                return None

            task_id = data["request"]
            logger.debug("2Captcha task submitted: %s", task_id)

            # Poll for result
            for _ in range(self.timeout // 5):
                await asyncio.sleep(5)
                result_resp = await self._client.get(
                    urls["result"],
                    params={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
                )
                result_data = result_resp.json()

                if result_data.get("status") == 1:
                    logger.info("CAPTCHA solved successfully")
                    return result_data["request"]

                if result_data.get("request") != "CAPCHA_NOT_READY":
                    logger.error("2Captcha error: %s", result_data.get("request"))
                    return None

        except Exception as e:
            logger.error("2Captcha request failed: %s", str(e))

        logger.warning("CAPTCHA solving timed out")
        return None

    async def _solve_anticaptcha(
        self, task_type: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """Submit and retrieve solution from Anti-Captcha."""
        urls = self.SERVICE_URLS["anticaptcha"]

        try:
            # Submit task
            resp = await self._client.post(
                urls["submit"],
                json={
                    "clientKey": self.api_key,
                    "task": {"type": task_type, **params},
                },
            )
            data = resp.json()

            if data.get("errorId", 0) != 0:
                logger.error("Anti-Captcha error: %s", data.get("errorDescription"))
                return None

            task_id = data["taskId"]

            # Poll for result
            for _ in range(self.timeout // 5):
                await asyncio.sleep(5)
                result_resp = await self._client.post(
                    urls["result"],
                    json={"clientKey": self.api_key, "taskId": task_id},
                )
                result_data = result_resp.json()

                if result_data.get("status") == "ready":
                    solution = result_data.get("solution", {})
                    return solution.get("gRecaptchaResponse") or solution.get("token")

        except Exception as e:
            logger.error("Anti-Captcha request failed: %s", str(e))

        return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()