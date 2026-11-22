"""Watchlist, preferiti e progressi salvati."""

from __future__ import annotations

from typing import Literal

from aw_web.anime import Anime
from aw_web.db import DB


def toggle(table: Literal["watchlist", "favorites"], anime: Anime) -> None:
    """Aggiunge o toglie l'anime; se era già stato visto riparte dall'ultimo episodio."""
    if DB.find(table, anime.ref):
        DB.remove(table, anime.ref)
        return
    history = DB.find("watch_history", anime.ref)
    DB.upsert(table, anime.to_dict(), str(history["current_episode"]) if history else "0")


def save_watch_progress(anime: Anime, episode: Anime.Episode) -> None:
    """Segna l'episodio come visto: sempre nella cronologia, e nelle liste dove l'anime c'è già."""
    DB.upsert("watch_history", anime.to_dict(), episode.num)
    for table in ("watchlist", "favorites"):
        if DB.find(table, anime.ref):
            DB.upsert(table, anime.to_dict(), episode.num)
