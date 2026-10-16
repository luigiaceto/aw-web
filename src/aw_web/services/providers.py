"""Provider selection for the local web interface."""

from __future__ import annotations

from functools import lru_cache

from aw_web import providers
from aw_web.web import state as _state


@lru_cache(maxsize=4)
def get_provider(name: str) -> providers.Provider:
    return providers.create_provider(name)


def default_provider_name() -> str:
    if _state.CURRENT_PROVIDER in providers.PROVIDERS_AVAILABLE:
        return _state.CURRENT_PROVIDER
    return "animeunity"


def set_current_provider(name: str) -> None:
    """Persist the active provider for the current session."""
    if name in providers.PROVIDERS_AVAILABLE:
        _state.CURRENT_PROVIDER = name
