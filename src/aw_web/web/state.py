"""Shared runtime state for the local web interface."""

from aw_web.web.db import WebDatabase


HOST = "127.0.0.1"
PORT = 8765
DB = WebDatabase()
STREAMS: dict[str, dict[str, str]] = {}
CURRENT_PROVIDER: str = ""
