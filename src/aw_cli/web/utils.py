"""Small serialization, escaping, and comparison helpers for web modules."""

from __future__ import annotations

import html
import json
from typing import Any
from urllib.parse import quote

from aw_cli.anime import Anime


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def q(value: object) -> str:
    return quote(str(value), safe="")


def anime_to_json(anime: Anime) -> str:
    return json.dumps(anime.to_dict(), ensure_ascii=False)


def anime_from_json(raw: str) -> Anime:
    return Anime.from_dict(json.loads(raw))


def provider_error(exc: BaseException) -> str:
    if isinstance(exc, SystemExit):
        return "Il provider ha interrotto l'operazione. Riprova o cambia provider."
    return str(exc)


def episode_value(value: str) -> float:
    try:
        if "-" in value:
            return float(value.split("-")[-1])
        return float(value)
    except ValueError:
        return 0


def has_new_episode(item: dict[str, Any], latest: list[Anime]) -> bool:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    current = episode_value(str(item["current_episode"]))

    if episode_value(str(item["last_episode"])) > current:
        return True

    if any(episode_value(ep.num) > current for ep in anime._episodes):
        return True

    for latest_anime in latest:
        if anime == latest_anime and episode_value(latest_anime.curr_ep) > current:
            return True

    return False
