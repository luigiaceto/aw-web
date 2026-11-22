"""AniList seasonal and ranked anime lists."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import httpx

SEASON_ORDER = ("WINTER", "SPRING", "SUMMER", "FALL")
SEASON_LABELS = {
    "WINTER": "Inverno",
    "SPRING": "Primavera",
    "SUMMER": "Estate",
    "FALL": "Autunno",
}
RANKED_LISTS = {
    "popolari": {
        "title": "Popolari",
        "eyebrow": "Anime di tendenza",
        "description": "Gli anime che stanno andando forte ora secondo AniList.",
        "sort": "TRENDING_DESC",
    },
    "top-100": {
        "title": "Top 100",
        "eyebrow": "Migliori di sempre",
        "description": "I cento anime con il punteggio piu alto su AniList.",
        "sort": "SCORE_DESC",
    },
}


_MEDIA_FIELDS = """
          id
          title { romaji english native }
          synonyms
          coverImage { large extraLarge }
          episodes
          genres
          averageScore
          isAdult
"""


@dataclass(frozen=True)
class SeasonalAnime:
    anilist_id: int
    title: str
    title_romaji: str
    title_english: str
    title_native: str
    synonyms: tuple[str, ...]
    cover_url: str
    episodes: int
    genres: tuple[str, ...]
    average_score: int

    @property
    def search_titles(self) -> list[str]:
        titles = [
            self.title,
            self.title_english,
            self.title_romaji,
            *self.synonyms,
            self.title_native,
        ]
        return list(dict.fromkeys(variant for title in titles for variant in seasonal_title_variants(title)))


def current_season(today: date | None = None) -> tuple[int, str]:
    today = today or date.today()
    index = (today.month - 1) // 3
    return today.year, SEASON_ORDER[index]


def adjacent_season(year: int, season: str, offset: int) -> tuple[int, str]:
    years, position = divmod(SEASON_ORDER.index(season) + offset, len(SEASON_ORDER))
    return year + years, SEASON_ORDER[position]


def normalize_season(value: str) -> str:
    season = value.strip().upper()
    return season if season in SEASON_ORDER else current_season()[1]


def seasonal_label(season: str) -> str:
    return SEASON_LABELS.get(season, season.title())


def seasonal_anime(year: int, season: str) -> tuple[SeasonalAnime, ...]:
    return _seasonal_anime(year, normalize_season(season), date.today().isoformat())


@lru_cache(maxsize=24)
def _seasonal_anime(year: int, season: str, day: str) -> tuple[SeasonalAnime, ...]:
    """`day` fa parte della chiave di cache: le liste si aggiornano una volta al giorno."""
    query = (
        """
    query ($year: Int, $season: MediaSeason, $page: Int) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage }
        media(
          type: ANIME,
          seasonYear: $year,
          season: $season,
          sort: [POPULARITY_DESC, TRENDING_DESC]
        ) {"""
        + _MEDIA_FIELDS
        + """        }
      }
    }
    """
    )
    return _fetch_media(query, {"year": year, "season": season}, max_pages=10)


def _seasonal_from_media(data: dict[str, Any]) -> SeasonalAnime:
    titles = data.get("title") or {}
    cover = data.get("coverImage") or {}
    romaji, english, native = (str(titles.get(key) or "") for key in ("romaji", "english", "native"))
    return SeasonalAnime(
        anilist_id=int(data.get("id") or 0),
        title=english or romaji or native,
        title_romaji=romaji,
        title_english=english,
        title_native=native,
        synonyms=tuple(str(synonym) for synonym in data.get("synonyms") or [] if synonym),
        cover_url=str(cover.get("extraLarge") or cover.get("large") or ""),
        episodes=int(data.get("episodes") or 0),
        genres=tuple(str(genre) for genre in (data.get("genres") or [])[:3]),
        average_score=int(data.get("averageScore") or 0),
    )


def _fetch_media(
    query: str,
    variables: dict[str, object],
    *,
    max_pages: int,
    limit: int | None = None,
) -> tuple[SeasonalAnime, ...]:
    """Esegue la query paginata di AniList e converte i media in SeasonalAnime."""
    items: list[SeasonalAnime] = []
    page = 1
    while page <= max_pages:
        response = httpx.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": {**variables, "page": page}},
            timeout=12,
        )
        response.raise_for_status()
        page_data = response.json().get("data", {}).get("Page", {}) or {}
        media = page_data.get("media") or []
        items.extend(_seasonal_from_media(item) for item in media if not _is_adult_media(item))
        if limit is not None and len(items) >= limit:
            break
        page_info = page_data.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        page += 1
    return tuple(items[:limit] if limit is not None else items)


def _is_adult_media(data: dict[str, object]) -> bool:
    if data.get("isAdult"):
        return True
    genres = data.get("genres")
    return isinstance(genres, list) and any(str(genre).lower() == "hentai" for genre in genres)


def seasonal_by_id(year: int, season: str, anilist_id: int) -> SeasonalAnime | None:
    return next((anime for anime in seasonal_anime(year, season) if anime.anilist_id == anilist_id), None)


def normalize_ranked_list(value: str) -> str:
    slug = value.strip().lower()
    return slug if slug in RANKED_LISTS else "popolari"


def ranked_list_label(slug: str) -> str:
    return str(RANKED_LISTS[normalize_ranked_list(slug)]["title"])


def ranked_anime(slug: str) -> tuple[SeasonalAnime, ...]:
    return _ranked_anime(normalize_ranked_list(slug), date.today().isoformat())


@lru_cache(maxsize=8)
def _ranked_anime(slug: str, day: str) -> tuple[SeasonalAnime, ...]:
    """`day` fa parte della chiave di cache: le liste si aggiornano una volta al giorno."""
    sort = str(RANKED_LISTS[slug]["sort"])
    query = (
        """
    query ($page: Int, $sort: [MediaSort]) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage }
        media(
          type: ANIME,
          sort: $sort
        ) {"""
        + _MEDIA_FIELDS
        + """        }
      }
    }
    """
    )
    return _fetch_media(query, {"sort": [sort]}, max_pages=2, limit=100)


def ranked_by_id(slug: str, anilist_id: int) -> SeasonalAnime | None:
    return next((anime for anime in ranked_anime(slug) if anime.anilist_id == anilist_id), None)


def seasonal_title_variants(title: str) -> list[str]:
    clean = title.strip()
    if not clean:
        return []

    variants = [clean]
    match = re.search(r"(?i)(?:[-:]\s*)?(?:(?:season|s)\s*(\d+)|(\d+)(?:st|nd|rd|th)\s+season)\s*$", clean)
    if match and (base := clean[: match.start()].strip(" -:")):
        number = match.group(1) or match.group(2)
        variants += [f"{base}- {number}", f"{base} {number}", base]
    return list(dict.fromkeys(variants))
