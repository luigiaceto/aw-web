"""AniList-backed seasonal anime and cover metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import httpx

from aw_web.web.state import DB


SEASON_ORDER = ("WINTER", "SPRING", "SUMMER", "FALL")
SEASON_LABELS = {
    "WINTER": "Inverno",
    "SPRING": "Primavera",
    "SUMMER": "Estate",
    "FALL": "Autunno",
}


def _as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if not isinstance(value, (str, int, float)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class SeasonalAnime:
    anilist_id: int
    title: str
    title_romaji: str
    title_english: str
    title_native: str
    synonyms: tuple[str, ...]
    cover_url: str
    banner_url: str
    status: str
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
        result: list[str] = []
        for title in titles:
            for clean in seasonal_title_variants(title):
                if clean and clean not in result:
                    result.append(clean)
        return result


def current_season(today: date | None = None) -> tuple[int, str]:
    today = today or date.today()
    index = (today.month - 1) // 3
    return today.year, SEASON_ORDER[index]


def adjacent_season(year: int, season: str, offset: int) -> tuple[int, str]:
    if season not in SEASON_ORDER:
        season = current_season()[1]
    position = SEASON_ORDER.index(season) + offset
    while position < 0:
        year -= 1
        position += len(SEASON_ORDER)
    while position >= len(SEASON_ORDER):
        year += 1
        position -= len(SEASON_ORDER)
    return year, SEASON_ORDER[position]


def normalize_season(value: str) -> str:
    season = value.strip().upper()
    return season if season in SEASON_ORDER else current_season()[1]


def seasonal_label(season: str) -> str:
    return SEASON_LABELS.get(season, season.title())


@lru_cache(maxsize=24)
def seasonal_anime(year: int, season: str) -> tuple[SeasonalAnime, ...]:
    season = normalize_season(season)
    query = """
    query ($year: Int, $season: MediaSeason, $page: Int) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage }
        media(
          type: ANIME,
          seasonYear: $year,
          season: $season,
          sort: [POPULARITY_DESC, TRENDING_DESC]
        ) {
          id
          title { romaji english native }
          synonyms
          coverImage { large extraLarge }
          bannerImage
          status
          episodes
          genres
          averageScore
          isAdult
        }
      }
    }
    """
    items: list[SeasonalAnime] = []
    page = 1
    while page <= 10:
        response = httpx.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": {"year": year, "season": season, "page": page}},
            timeout=12,
        )
        response.raise_for_status()
        page_data = response.json().get("data", {}).get("Page", {}) or {}
        media = page_data.get("media") or []
        items.extend(_seasonal_from_media(item) for item in media if not _is_adult_media(item))
        page_info = page_data.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        page += 1
    return tuple(items)


def _seasonal_from_media(data: dict[str, object]) -> SeasonalAnime:
    title_data = data.get("title") if isinstance(data.get("title"), dict) else {}
    cover_data = data.get("coverImage") if isinstance(data.get("coverImage"), dict) else {}
    title_romaji = str(title_data.get("romaji") or "") if isinstance(title_data, dict) else ""
    title_english = str(title_data.get("english") or "") if isinstance(title_data, dict) else ""
    title_native = str(title_data.get("native") or "") if isinstance(title_data, dict) else ""
    synonyms_data = data.get("synonyms")
    genres_data = data.get("genres")
    return SeasonalAnime(
        anilist_id=_as_int(data.get("id")),
        title=title_english or title_romaji or title_native,
        title_romaji=title_romaji,
        title_english=title_english,
        title_native=title_native,
        synonyms=tuple(str(item) for item in synonyms_data if item) if isinstance(synonyms_data, list) else (),
        cover_url=str(cover_data.get("extraLarge") or cover_data.get("large") or "") if isinstance(cover_data, dict) else "",
        banner_url=str(data.get("bannerImage") or ""),
        status=str(data.get("status") or ""),
        episodes=_as_int(data.get("episodes")),
        genres=tuple(str(item) for item in genres_data[:3]) if isinstance(genres_data, list) else (),
        average_score=_as_int(data.get("averageScore")),
    )


def _is_adult_media(data: dict[str, object]) -> bool:
    if data.get("isAdult"):
        return True
    genres = data.get("genres")
    return isinstance(genres, list) and any(str(genre).lower() == "hentai" for genre in genres)


def seasonal_by_id(year: int, season: str, anilist_id: int) -> SeasonalAnime | None:
    for anime in seasonal_anime(year, season):
        if anime.anilist_id == anilist_id:
            return anime
    return None


def seasonal_title_variants(title: str) -> list[str]:
    clean = title.strip()
    if not clean:
        return []

    variants = [clean]
    season_match = re.search(r"(?i)(?:[-:]\s*)?(?:season|s)\s*(\d+)\s*$", clean)
    if season_match:
        number = season_match.group(1)
        base = clean[: season_match.start()].strip(" -:")
        if base:
            variants.append(f"{base}- {number}")
            variants.append(f"{base} {number}")
            variants.append(base)

    ordinal_match = re.search(r"(?i)(?:[-:]\s*)?(\d+)(?:st|nd|rd|th)\s+season\s*$", clean)
    if ordinal_match:
        number = ordinal_match.group(1)
        base = clean[: ordinal_match.start()].strip(" -:")
        if base:
            variants.append(f"{base}- {number}")
            variants.append(f"{base} {number}")
            variants.append(base)

    result: list[str] = []
    for variant in variants:
        if variant and variant not in result:
            result.append(variant)
    return result


def cover_cache_key(anilist_id: int, title: str) -> str:
    if anilist_id:
        return f"anilist:{anilist_id}"
    return f"title:{title.strip().lower()}"


def get_cover(anilist_id: int, title: str, *, allow_title_lookup: bool = True) -> dict[str, str]:
    key = cover_cache_key(anilist_id, title)
    cached = DB.get_cover(key)
    if cached:
        return {
            "cover_url": str(cached["cover_url"]),
            "banner_url": str(cached["banner_url"]),
            "color": str(cached["color"]),
        }

    if not anilist_id and (not title.strip() or not allow_title_lookup):
        return {"cover_url": "", "banner_url": "", "color": ""}

    if anilist_id:
        query = """
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            id
            title { romaji english native }
            coverImage { large extraLarge color }
            bannerImage
          }
        }
        """
        variables: dict[str, object] = {"id": anilist_id}
    else:
        query = """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            id
            title { romaji english native }
            coverImage { large extraLarge color }
            bannerImage
          }
        }
        """
        variables = {"search": title}

    try:
        response = httpx.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
            timeout=10,
        )
        response.raise_for_status()
        media = response.json().get("data", {}).get("Media") or {}
    except Exception:
        media = {}

    media_title = media.get("title") or {}
    cover = media.get("coverImage") or {}
    resolved_id = int(media.get("id") or anilist_id or 0)
    resolved_title = (
        media_title.get("english") or media_title.get("romaji") or media_title.get("native") or title
    )
    result = {
        "cover_url": str(cover.get("extraLarge") or cover.get("large") or ""),
        "banner_url": str(media.get("bannerImage") or ""),
        "color": str(cover.get("color") or ""),
    }
    DB.set_cover(
        cache_key=key,
        anilist_id=resolved_id,
        title=str(resolved_title),
        cover_url=result["cover_url"],
        banner_url=result["banner_url"],
        color=result["color"],
    )
    return result
