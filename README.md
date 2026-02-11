# Browser Automation Framework

A professional Playwright-based browser automation framework with built-in anti-detection measures, proxy rotation, CAPTCHA solving integration, and comprehensive page interaction utilities.

## Features

- **Playwright Core**: Async browser control with Chromium, Firefox, and WebKit
- **Anti-Detection**: Fingerprint spoofing, WebGL noise, navigator overrides
- **Proxy Rotation**: Automatic proxy switching with health monitoring
- **CAPTCHA Solving**: Integration with 2Captcha and Anti-Captcha services
- **Page Actions**: High-level utilities for form filling, scrolling, waiting
- **Screenshots**: Full-page and element screenshots with comparison
- **Configurable**: YAML/env-based configuration management

## Installation

```bash
git clone https://github.com/jy02140251/browser-automation-framework.git
cd browser-automation-framework
pip install -r requirements.txt
playwright install chromium
```

## Quick Start

```python
import asyncio
from automation import Browser, AntiDetect, ProxyRotation

async def main():
    proxy_pool = ProxyRotation(proxies=["http://proxy1:8080", "http://proxy2:8080"])
    anti_detect = AntiDetect()
    
    async with Browser(headless=True, proxy_rotation=proxy_pool) as browser:
        page = await browser.new_page(anti_detect=anti_detect)
        await page.goto("https://example.com")
        
        # Take screenshot
        await browser.screenshot(page, "example.png")
        
        content = await page.content()
        print(f"Page loaded: {len(content)} bytes")

asyncio.run(main())
```

## Project Structure

```
browser-automation-framework/
├── automation/
│   ├── __init__.py
│   ├── browser.py          # Core browser management
│   ├── anti_detect.py      # Anti-detection measures
│   ├── proxy_rotation.py   # Proxy pool management
│   ├── captcha_solver.py   # CAPTCHA solving integration
│   ├── page_actions.py     # High-level page utilities
│   └── screenshot.py       # Screenshot utilities
├── config.py               # Configuration management
├── examples/
│   └── scrape_example.py   # Usage example
├── tests/
│   └── test_browser.py     # Unit tests
└── requirements.txt
```

## License

MIT License