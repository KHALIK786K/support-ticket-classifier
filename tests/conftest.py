"""
Shared pytest fixtures.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Ensure tests use an isolated env and don't read a real .env
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def sample_tickets() -> list[tuple[str, str]]:
    """Realistic (text, category) pairs for unit-level tests."""
    return [
        ("Refund of Rs.4999 not received even after 7 days, please help.", "Billing"),
        ("Unable to login to the portal — getting 500 error since morning.", "Technical"),
        ("My salary slip for May is missing on the HR portal.", "HR"),
        ("Please share the GST invoice for order A-2231 for tax filing.", "Finance"),
        ("I forgot my account password and reset email never arrives.", "Account"),
    ]
