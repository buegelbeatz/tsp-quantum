"""Shared link validation predicates.

Purpose:
    Centralized link validation and classification to reduce duplication across
    i2d_link modules.

Security:
    Pure validation functions with no mutable state or side effects.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


def is_valid_http_url(url: str) -> bool:
    """Check if string is a valid HTTP(S) URL.

    Args:
        url: URL string to validate.

    Returns:
        True if url starts with http:// or https://, else False.
    """
    if not url or not isinstance(url, str):
        return False
    return url.lower().startswith(("http://", "https://"))


def is_internal_link(url: str, domain_allowlist: set[str] | None = None) -> bool:
    """Check if URL is internal or from allowlisted domains.

    Args:
        url: URL to check.
        domain_allowlist: Optional set of allowed internal domains.

    Returns:
        True if URL is internal (no protocol) or from allowlist.
    """
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        return True
    if domain_allowlist:
        try:
            parsed = urlparse(url)
            return parsed.netloc in domain_allowlist
        except (ValueError, AttributeError):
            return False
    return False


def is_likely_email_address(text: str) -> bool:
    """Check if text looks like an email address.

    Args:
        text: Text to check.

    Returns:
        True if text matches basic email pattern.
    """
    if not text:
        return False
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, text.strip()))


def normalize_url(url: str) -> str:
    """Normalize URL by stripping whitespace and removing fragment.

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL string.
    """
    if not url:
        return ""
    normalized = url.strip()
    if "#" in normalized:
        normalized = normalized.split("#")[0]
    return normalized


def classify_link_type(url: str) -> str:
    """Classify link type based on URL format.

    Args:
        url: URL to classify.

    Returns:
        One of: 'http', 'internal', 'email', 'unknown'.
    """
    if is_valid_http_url(url):
        return "http"
    if is_likely_email_address(url):
        return "email"
    if is_internal_link(url):
        return "internal"
    return "unknown"
