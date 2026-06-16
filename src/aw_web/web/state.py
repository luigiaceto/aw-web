"""Shared runtime state for the local web interface."""

from secrets import token_urlsafe
from typing import Any

from aw_web.web.db import WebDatabase


HOST = "127.0.0.1"
PORT = 8765
DB = WebDatabase()
CSRF_TOKEN = token_urlsafe(32)
STREAMS: dict[str, dict[str, Any]] = {}
CURRENT_PROVIDER: str = ""
