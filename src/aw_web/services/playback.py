"""Media URL validation helpers."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlparse



_BLOCKED_HOSTS = {"localhost"}


def validate_media_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("URL video non valido.")
    if parsed.username or parsed.password:
        raise RuntimeError("URL video non valido.")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTS or hostname.endswith(".localhost"):
        raise RuntimeError("URL video non consentito.")

    try:
        address = ip_address(hostname)
    except ValueError:
        return url

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise RuntimeError("URL video non consentito.")
    return url
