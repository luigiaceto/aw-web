"""Shared runtime state for the local web interface."""

from secrets import token_urlsafe
from typing import Any, cast

from aw_web.web.db import WebDatabase


class LazyDatabase:
    def __init__(self) -> None:
        self._database: WebDatabase | None = None

    def _get_database(self) -> WebDatabase:
        if self._database is None:
            self._database = WebDatabase()
        return self._database

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_database(), name)


HOST = "127.0.0.1"
PORT = 8765
_DB = LazyDatabase()
DB = cast(WebDatabase, _DB)
CSRF_TOKEN = token_urlsafe(32)
CURRENT_PROVIDER: str = ""


def reset_lazy_database() -> None:
    _DB._database = None
