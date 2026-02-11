"""Tests for the data extraction module."""

import pytest
from automation.data_extractor import DataExtractor, ExtractionRule


class TestDataExtractor:
    def test_add_text_rule(self):
        extractor = DataExtractor()
        extractor.add_text_rule("title", "h1.title")
        assert len(extractor._rules) == 1
        assert extractor._rules[0].name == "title"

    def test_add_attribute_rule(self):
        extractor = DataExtractor()
        extractor.add_attribute_rule("link", "a.main", "href")
        assert extractor._rules[0].attribute == "href"

    def test_add_list_rule(self):
        extractor = DataExtractor()
        extractor.add_list_rule("items", "li.item")
        assert extractor._rules[0].multiple is True

    def test_method_chaining(self):
        extractor = DataExtractor()
        result = (
            extractor
            .add_text_rule("title", "h1")
            .add_attribute_rule("img", "img.hero", "src")
            .add_list_rule("tags", "span.tag")
        )
        assert result is extractor
        assert len(extractor._rules) == 3


class TestCleanFunctions:
    def test_clean_price(self):
        assert DataExtractor.clean_price("$19.99") == 19.99
        assert DataExtractor.clean_price("Price: 1,299.00") == 1299.00
        assert DataExtractor.clean_price("Free") == 0.0

    def test_clean_number(self):
        assert DataExtractor.clean_number("42 reviews") == 42
        assert DataExtractor.clean_number("1,234 items") == 1234
        assert DataExtractor.clean_number("none") == 0


class TestExtractionRule:
    def test_default_values(self):
        rule = ExtractionRule(name="test", selector="div")
        assert rule.attribute is None
        assert rule.transform is None
        assert rule.multiple is False
        assert rule.default is None

    def test_custom_values(self):
        rule = ExtractionRule(
            name="price",
            selector="span.price",
            transform=DataExtractor.clean_price,
            default=0.0,
        )
        assert rule.transform is not None
        assert rule.default == 0.0