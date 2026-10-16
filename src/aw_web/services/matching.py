"""Matching between AniList seasonal entries and provider search results."""

from __future__ import annotations

from difflib import SequenceMatcher

from aw_web.anime import Anime
from aw_web.services.anilist import SeasonalAnime
from aw_web.services.providers import get_provider


def find_seasonal_matches(provider_name: str, seasonal: SeasonalAnime) -> list[Anime]:
    provider = get_provider(provider_name)
    found: list[Anime] = []
    for title in seasonal.search_titles[:5]:
        try:
            for anime in provider.search(title):
                if not any(_same_provider_result(anime, existing) for existing in found):
                    found.append(anime)
        except Exception:
            continue
        if any(_is_exact_seasonal_match(anime, seasonal) for anime in found):
            break
    return sorted(found, key=lambda anime: _seasonal_match_score(anime, seasonal), reverse=True)[:6]


def best_seasonal_match(provider_name: str, seasonal: SeasonalAnime) -> tuple[Anime | None, list[Anime]]:
    matches = find_seasonal_matches(provider_name, seasonal)
    if not matches:
        return None, []
    best = matches[0]
    best_score = _seasonal_match_score(best, seasonal)
    second_score = _seasonal_match_score(matches[1], seasonal) if len(matches) > 1 else 0.0
    if best_score >= 1.0 or (best_score >= 0.82 and best_score - second_score >= 0.08):
        return best, matches
    return None, matches


def _same_provider_result(first: Anime, second: Anime) -> bool:
    return first.ref == second.ref or first == second


def _is_exact_seasonal_match(anime: Anime, seasonal: SeasonalAnime) -> bool:
    return bool(anime.anilist_id and anime.anilist_id == seasonal.anilist_id)


def _seasonal_match_score(anime: Anime, seasonal: SeasonalAnime) -> float:
    if _is_exact_seasonal_match(anime, seasonal):
        return 1.0
    anime_title = _normalize_title(anime.name)
    scores = [
        SequenceMatcher(None, anime_title, _normalize_title(title)).ratio()
        for title in seasonal.search_titles
    ]
    return max(scores or [0.0])


def _normalize_title(value: str) -> str:
    keep = [char.lower() if char.isalnum() else " " for char in value.replace("(ITA)", "")]
    return " ".join("".join(keep).split())
