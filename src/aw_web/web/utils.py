"""Small serialization, escaping, and comparison helpers for web modules."""

from __future__ import annotations

import html
import json
from typing import Any
from urllib.parse import quote, urlencode

from aw_web.anime import Anime, episode_value


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def q(value: object) -> str:
    return quote(str(value), safe="")


def parse_int(value: object, default: int = 0) -> int:
    """Intero da un parametro o da un campo JSON; None o testo non numerico danno `default`."""
    try:
        return int(value) if isinstance(value, (str, int, float)) else default
    except ValueError:
        return default


def anime_to_json(anime: Anime) -> str:
    return json.dumps(anime.to_dict(), ensure_ascii=False)


def anime_from_json(raw: str) -> Anime:
    return Anime.from_dict(json.loads(raw))


def saved_anime(item: dict[str, Any]) -> Anime:
    """L'anime di una riga del database."""
    return anime_from_json(str(item["anime_json"]))


def provider_error(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def anime_url(anime: Anime, *, saved: bool = False) -> str:
    """Link alla pagina dettaglio: il resto lo carica la pagina da AnimeUnity."""
    query = urlencode({"name": anime.name, "ref": anime.ref})
    return f"/anime?saved=1&{query}" if saved else f"/anime?{query}"


def episode_overview(anime: Anime, current_episode: str, latest: list[Anime]) -> tuple[str, str]:
    """Ritorna (ultimo episodio disponibile, prossimo episodio da guardare)."""
    current = episode_value(current_episode)
    candidates = [
        anime.curr_ep,
        anime.last_ep,
        *(ep.num for ep in anime._episodes),
    ]

    for latest_anime in latest:
        if anime == latest_anime:
            candidates.extend([latest_anime.curr_ep, latest_anime.last_ep])
            candidates.extend(ep.num for ep in latest_anime._episodes)

    last_available = max(candidates, key=episode_value, default="0")
    if current_episode.isdigit() and last_available.isdigit():
        next_number = int(current_episode) + 1
        if next_number <= int(last_available):
            candidates.append(str(next_number))

    next_playable = min(
        (candidate for candidate in candidates if episode_value(candidate) > current),
        key=episode_value,
        default=current_episode,
    )
    return last_available, next_playable
