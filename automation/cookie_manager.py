"""Cookie and session management for browser automation."""

import json
import logging
import os
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CookieManager:
    """Manage browser cookies for persistent sessions across automation runs."""

    def __init__(self, storage_dir: str = "./cookies"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cookies: Dict[str, List[Dict]] = {}

    def _get_cookie_path(self, profile: str) -> Path:
        safe_name = "".join(c if c.isalnum() else "_" for c in profile)
        return self.storage_dir / f"{safe_name}.json"

    async def save_cookies(self, context, profile: str) -> int:
        """Save cookies from a browser context to a file."""
        cookies = await context.cookies()
        cookie_path = self._get_cookie_path(profile)
        data = {
            "profile": profile,
            "saved_at": datetime.utcnow().isoformat(),
            "cookie_count": len(cookies),
            "cookies": cookies,
        }
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        self._cookies[profile] = cookies
        logger.info(f"Saved {len(cookies)} cookies for profile '{profile}'")
        return len(cookies)

    async def load_cookies(self, context, profile: str) -> int:
        """Load cookies from a file into a browser context."""
        cookie_path = self._get_cookie_path(profile)
        if not cookie_path.exists():
            logger.warning(f"No saved cookies for profile '{profile}'")
            return 0

        with open(cookie_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        valid_cookies = self._filter_expired(cookies)

        if valid_cookies:
            await context.add_cookies(valid_cookies)
            self._cookies[profile] = valid_cookies
            logger.info(f"Loaded {len(valid_cookies)} cookies for profile '{profile}'")

        return len(valid_cookies)

    def _filter_expired(self, cookies: List[Dict]) -> List[Dict]:
        """Remove expired cookies from the list."""
        now = datetime.utcnow().timestamp()
        valid = []
        for cookie in cookies:
            expires = cookie.get("expires", -1)
            if expires == -1 or expires > now:
                valid.append(cookie)
        return valid

    def delete_profile(self, profile: str) -> bool:
        """Delete saved cookies for a profile."""
        cookie_path = self._get_cookie_path(profile)
        if cookie_path.exists():
            cookie_path.unlink()
            self._cookies.pop(profile, None)
            logger.info(f"Deleted cookies for profile '{profile}'")
            return True
        return False

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all saved cookie profiles."""
        profiles = []
        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                profiles.append({
                    "profile": data.get("profile", path.stem),
                    "cookie_count": data.get("cookie_count", 0),
                    "saved_at": data.get("saved_at"),
                    "file_size": path.stat().st_size,
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return profiles

    async def clear_cookies(self, context) -> None:
        """Clear all cookies from a browser context."""
        await context.clear_cookies()
        logger.info("Cleared all cookies from context")