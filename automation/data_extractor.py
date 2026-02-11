"""Data extraction utilities for structured web scraping."""

import re
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractionRule:
    name: str
    selector: str
    attribute: Optional[str] = None
    transform: Optional[Callable[[str], Any]] = None
    multiple: bool = False
    default: Any = None


@dataclass
class ExtractionResult:
    url: str
    data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    extraction_time_ms: float = 0.0


class DataExtractor:
    """Extract structured data from web pages using configurable rules."""

    def __init__(self):
        self._rules: List[ExtractionRule] = []

    def add_rule(self, rule: ExtractionRule) -> "DataExtractor":
        self._rules.append(rule)
        return self

    def add_text_rule(self, name: str, selector: str, **kwargs) -> "DataExtractor":
        return self.add_rule(ExtractionRule(name=name, selector=selector, **kwargs))

    def add_attribute_rule(self, name: str, selector: str, attribute: str, **kwargs) -> "DataExtractor":
        return self.add_rule(ExtractionRule(name=name, selector=selector, attribute=attribute, **kwargs))

    def add_list_rule(self, name: str, selector: str, **kwargs) -> "DataExtractor":
        return self.add_rule(ExtractionRule(name=name, selector=selector, multiple=True, **kwargs))

    async def extract(self, page) -> ExtractionResult:
        """Extract data from a page based on configured rules."""
        import time
        start = time.perf_counter()
        data = {}
        errors = []

        for rule in self._rules:
            try:
                if rule.multiple:
                    elements = await page.query_selector_all(rule.selector)
                    values = []
                    for el in elements:
                        val = await self._get_value(el, rule)
                        if val is not None:
                            values.append(val)
                    data[rule.name] = values
                else:
                    element = await page.query_selector(rule.selector)
                    if element:
                        data[rule.name] = await self._get_value(element, rule)
                    else:
                        data[rule.name] = rule.default
                        if rule.default is None:
                            errors.append(f"Element not found: {rule.selector}")
            except Exception as e:
                errors.append(f"Error extracting '{rule.name}': {str(e)}")
                data[rule.name] = rule.default

        elapsed = (time.perf_counter() - start) * 1000
        url = page.url

        logger.info(f"Extracted {len(data)} fields from {url} in {elapsed:.1f}ms")
        return ExtractionResult(url=url, data=data, errors=errors, extraction_time_ms=elapsed)

    async def _get_value(self, element, rule: ExtractionRule) -> Any:
        if rule.attribute:
            value = await element.get_attribute(rule.attribute)
        else:
            value = await element.inner_text()

        if value and rule.transform:
            value = rule.transform(value.strip())
        elif value:
            value = value.strip()

        return value

    @staticmethod
    def clean_price(text: str) -> float:
        """Transform function to extract numeric price from text."""
        numbers = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
        return float(numbers[0]) if numbers else 0.0

    @staticmethod
    def clean_number(text: str) -> int:
        """Transform function to extract integer from text."""
        numbers = re.findall(r"\d+", text.replace(",", ""))
        return int(numbers[0]) if numbers else 0