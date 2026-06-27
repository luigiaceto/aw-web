"""Compatibility facade for application services used by the web interface."""

from __future__ import annotations

from aw_web.services.anilist import (
    SEASON_LABELS,
    SEASON_ORDER,
    SeasonalAnime,
    adjacent_season,
    cover_cache_key,
    current_season,
    get_cover,
    normalize_season,
    seasonal_anime,
    seasonal_by_id,
    seasonal_label,
    seasonal_title_variants,
)
from aw_web.services.matching import (
    best_seasonal_match,
    find_seasonal_matches,
    seasonal_open_url,
)
from aw_web.services.playback import validate_media_url
from aw_web.services.progress import save_watch_progress
from aw_web.services.providers import (
    default_provider_name,
    ensure_config,
    get_provider,
    set_current_provider,
)
from aw_web.services.streams import (
    MAX_STREAMS,
    STREAM_TTL_SECONDS,
    prune_streams,
    resolve_episode_url,
    stream_context,
    stream_token,
)
from aw_web.web.state import DB, STREAMS


__all__ = [
    "DB",
    "MAX_STREAMS",
    "SEASON_LABELS",
    "SEASON_ORDER",
    "STREAMS",
    "STREAM_TTL_SECONDS",
    "SeasonalAnime",
    "adjacent_season",
    "best_seasonal_match",
    "cover_cache_key",
    "current_season",
    "default_provider_name",
    "ensure_config",
    "find_seasonal_matches",
    "get_cover",
    "get_provider",
    "normalize_season",
    "prune_streams",
    "resolve_episode_url",
    "save_watch_progress",
    "seasonal_anime",
    "seasonal_by_id",
    "seasonal_label",
    "seasonal_open_url",
    "seasonal_title_variants",
    "set_current_provider",
    "stream_context",
    "stream_token",
    "validate_media_url",
]
