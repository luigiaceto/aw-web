"""Small serialization, escaping, and comparison helpers for web modules."""

from __future__ import annotations

import html
import json
from typing import Any
from urllib.parse import quote

from aw_web.anime import Anime


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def q(value: object) -> str:
    return quote(str(value), safe="")


def parse_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if not isinstance(value, (str, int, float)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def anime_to_json(anime: Anime) -> str:
    return json.dumps(anime.to_dict(), ensure_ascii=False)


def anime_from_json(raw: str) -> Anime:
    return Anime.from_dict(json.loads(raw))


def provider_error(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def episode_value(value: str) -> float:
    try:
        if "-" in value:
            return float(value.split("-")[-1])
        return float(value)
    except ValueError:
        return 0


def has_new_episode(item: dict[str, Any], latest: list[Anime]) -> bool:
    current = episode_value(str(item["current_episode"]))
    return episode_value(available_last_episode(item, latest)) > current


def available_last_episode(item: dict[str, Any], latest: list[Anime]) -> str:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    candidates = [
        str(item["last_episode"]),
        anime.last_ep,
        *(ep.num for ep in anime._episodes),
    ]

    for latest_anime in latest:
        if anime == latest_anime:
            candidates.extend([latest_anime.curr_ep, latest_anime.last_ep])
            candidates.extend(ep.num for ep in latest_anime._episodes)

    return max(candidates, key=episode_value, default="0")


def next_playable_episode(item: dict[str, Any], latest: list[Anime]) -> str:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    current_episode = str(item["current_episode"])
    current = episode_value(current_episode)
    candidates = [
        str(item["last_episode"]),
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

    if current <= 0:
        return min(
            (candidate for candidate in candidates if episode_value(candidate) > 0),
            key=episode_value,
            default=current_episode,
        )

    return min(
        (candidate for candidate in candidates if episode_value(candidate) > current),
        key=episode_value,
        default=current_episode,
    )
