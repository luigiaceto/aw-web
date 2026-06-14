"""Shared runtime state for the local web interface."""

from aw_cli.web.db import WebDatabase


HOST = "127.0.0.1"
PORT = 8765
DB = WebDatabase()
STREAMS: dict[str, dict[str, str]] = {}
