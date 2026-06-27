"""Provider selection and application startup configuration."""

from __future__ import annotations

from functools import lru_cache

from aw_web import providers, utilities as ut
from aw_web.web import state as _state


def ensure_config() -> None:
    ut.config_data = {
        "general": {"specials": False},
        "provider": {"source": "animeunity"},
    }


@lru_cache(maxsize=4)
def get_provider(name: str) -> providers.Provider:
    return providers.create_provider(name)


def default_provider_name() -> str:
    if _state.CURRENT_PROVIDER in providers.PROVIDERS_AVAILABLE:
        return _state.CURRENT_PROVIDER
    configured = str(ut.config_data.get("provider", {}).get("source", "animeunity"))
    if configured in providers.PROVIDERS_AVAILABLE:
        return configured
    return "animeunity"


def set_current_provider(name: str) -> None:
    """Persist the active provider for the current session."""
    if name in providers.PROVIDERS_AVAILABLE:
        _state.CURRENT_PROVIDER = name
