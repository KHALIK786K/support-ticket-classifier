"""
Misc helpers.
"""
from __future__ import annotations

import hashlib


def text_hash(text: str) -> str:
    """Stable hash for cache keys — SHA-1 is fine here (not a security token)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
