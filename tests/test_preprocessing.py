"""
Tests for the NLP preprocessing pipeline.
"""
from __future__ import annotations

from app.ml.preprocessing import preprocess


def test_preprocess_lowercases_and_strips() -> None:
    out = preprocess("Hello, THIS is a TEST.")
    assert out == out.lower()
    assert "test" in out


def test_preprocess_removes_urls_and_emails() -> None:
    out = preprocess("contact me at foo@bar.com or visit https://example.com today")
    assert "foo" not in out  # email stripped
    assert "example" not in out  # URL stripped
    assert "http" not in out


def test_preprocess_removes_digits() -> None:
    out = preprocess("Invoice INV-12345 was generated yesterday")
    assert "12345" not in out
    assert "inv" in out  # alpha component preserved


def test_preprocess_empty_input() -> None:
    assert preprocess("") == ""
    assert preprocess("   ") == ""


def test_preprocess_idempotent() -> None:
    s = "Unable to login to the portal since morning."
    once = preprocess(s)
    twice = preprocess(once)
    assert once == twice
