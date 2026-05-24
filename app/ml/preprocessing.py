"""
NLP preprocessing for support tickets.

Pipeline (in order):
    1.  Lowercase
    2.  Strip URLs, emails, phone numbers, order/IDs
    3.  Remove HTML tags
    4.  Replace digits with a NUM token
    5.  Strip non-alpha characters
    6.  Tokenize on whitespace
    7.  Remove English stopwords + custom support-domain stopwords
    8.  Lemmatize via WordNet

All NLTK assets are downloaded lazily on first use so the module is safe to
import in environments without an internet connection at import time.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, List

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_PHONE_RE = re.compile(r"\+?\d[\d \-()]{7,}\d")
_HTML_RE = re.compile(r"<[^>]+>")
_NON_ALPHA_RE = re.compile(r"[^a-z\s]")
_MULTISPACE_RE = re.compile(r"\s+")

_CUSTOM_STOPWORDS = {
    "hi", "hello", "hey", "thanks", "thank", "regards", "team",
    "please", "sir", "ma'am", "ma", "kindly", "dear",
}


@lru_cache(maxsize=1)
def _ensure_nltk_assets() -> None:
    """Idempotently download required NLTK assets on first call."""
    for pkg, path in [
        ("punkt_tab", "tokenizers/punkt_tab"),
        ("punkt", "tokenizers/punkt"),
        ("stopwords", "corpora/stopwords"),
        ("wordnet", "corpora/wordnet"),
        ("omw-1.4", "corpora/omw-1.4"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:  # noqa: BLE001 — offline tolerant
                pass


@lru_cache(maxsize=1)
def _stopwords() -> set[str]:
    _ensure_nltk_assets()
    try:
        sw = set(stopwords.words("english"))
    except Exception:  # noqa: BLE001
        sw = set()
    sw |= _CUSTOM_STOPWORDS
    return sw


@lru_cache(maxsize=1)
def _lemmatizer() -> WordNetLemmatizer:
    _ensure_nltk_assets()
    return WordNetLemmatizer()


def _basic_clean(text: str) -> str:
    text = text.lower()
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _PHONE_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _NON_ALPHA_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.strip()


def _tokenize(text: str) -> List[str]:
    _ensure_nltk_assets()
    try:
        return word_tokenize(text)
    except Exception:  # noqa: BLE001 — fall back if NLTK punkt missing
        return text.split()


def _filter_and_lemmatize(tokens: Iterable[str]) -> List[str]:
    sw = _stopwords()
    lem = _lemmatizer()
    out: List[str] = []
    for tok in tokens:
        if len(tok) < 2 or tok in sw:
            continue
        try:
            out.append(lem.lemmatize(tok, pos=wordnet.VERB))
        except Exception:  # noqa: BLE001
            out.append(tok)
    return out


def preprocess(text: str) -> str:
    """Run the full pipeline and return a space-joined cleaned string."""
    if not text:
        return ""
    cleaned = _basic_clean(text)
    tokens = _tokenize(cleaned)
    tokens = _filter_and_lemmatize(tokens)
    return " ".join(tokens)


def preprocess_many(texts: Iterable[str]) -> List[str]:
    return [preprocess(t) for t in texts]
