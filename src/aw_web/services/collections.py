"""Watchlist and favorites persistence helpers."""

from __future__ import annotations

from aw_web.anime import Anime
from aw_web.web.state import DB


def toggle_watchlist(provider_name: str, anime: Anime, cover_url: str, banner_url: str) -> None:
    existing = DB.find_watch_item(provider_name, anime.ref)
    if existing:
        DB.remove_watch_item_by_ref(provider_name, anime.ref)
        return

    history = DB.find_history_item(provider_name, anime.ref)
    DB.upsert_watch_item(
        provider=provider_name,
        anime_data=anime.to_dict(),
        cover_url=cover_url,
        banner_url=banner_url,
        current_episode=str(history["current_episode"]) if history else "0",
    )


def toggle_favorite(provider_name: str, anime: Anime, cover_url: str, banner_url: str) -> None:
    existing = DB.find_favorite_item(provider_name, anime.ref)
    if existing:
        DB.remove_favorite_item_by_ref(provider_name, anime.ref)
        return

    history = DB.find_history_item(provider_name, anime.ref)
    DB.upsert_favorite_item(
        provider=provider_name,
        anime_data=anime.to_dict(),
        cover_url=cover_url,
        banner_url=banner_url,
        current_episode=str(history["current_episode"]) if history else "0",
    )


def remove_watch_item(item_id: int) -> None:
    if item_id:
        DB.remove_watch_item(item_id)


def remove_favorite_item(item_id: int) -> None:
    if item_id:
        DB.remove_favorite_item(item_id)
