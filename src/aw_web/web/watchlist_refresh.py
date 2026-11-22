"""Watchlist episode availability refresh helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from aw_web.providers import Animeunity
from aw_web.web.db import WebDatabase, db_timestamp, parse_db_timestamp
from aw_web.web.utils import saved_anime


WATCHLIST_REFRESH_INTERVAL = timedelta(hours=6)


def should_refresh_watch_item(item: dict[str, Any], now: datetime | None = None) -> bool:
    checked_at = parse_db_timestamp(item.get("episodes_checked_at"))
    if checked_at is None:
        return True
    return (now or datetime.now(timezone.utc)) - checked_at >= WATCHLIST_REFRESH_INTERVAL


def refresh_watchlist_availability(
    db: WebDatabase,
    items: list[dict[str, Any]],
    provider: Animeunity,
    *,
    now: datetime | None = None,
) -> None:
    checked_at = now or datetime.now(timezone.utc)
    checked_at_value = db_timestamp(checked_at)
    for item in items:
        ref = str(item["ref"])
        if not should_refresh_watch_item(item, checked_at):
            continue

        try:
            anime = saved_anime(item)
            provider.info_anime(anime)
            provider.episodes(anime)
            db.update_watch_item_availability(
                ref=ref,
                anime_data=anime.to_dict(),
                checked_at=checked_at_value,
            )
        except Exception:
            db.mark_watch_item_episodes_checked(ref, checked_at_value)
