"""Backend services for providers, cover metadata, playback, and watch progress."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import quote, urlparse
from uuid import uuid4

import httpx

from aw_web import providers, utilities as ut
from aw_web.anime import Anime
from aw_web.web import state as _state
from aw_web.web.state import DB, STREAMS
from aw_web.web.utils import anime_from_json, anime_to_json


SEASON_ORDER = ("WINTER", "SPRING", "SUMMER", "FALL")
SEASON_LABELS = {
    "WINTER": "Inverno",
    "SPRING": "Primavera",
    "SUMMER": "Estate",
    "FALL": "Autunno",
}
STREAM_TTL_SECONDS = 2 * 60 * 60
MAX_STREAMS = 200
_BLOCKED_HOSTS = {"localhost"}


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
            clean = title.strip()
            if clean and clean not in result:
                result.append(clean)
        return result


def ensure_config() -> None:
    player_path = shutil.which("mpv") or shutil.which("vlc") or ""
    player_type = "vlc" if player_path and "vlc" in Path(player_path).name.lower() else "mpv"
    ut.config_data = {
        "general": {"specials": False},
        "provider": {"source": "animeunity"},
        "player": {"type": player_type, "path": player_path},
    }


@lru_cache(maxsize=4)
def get_provider(name: str) -> providers.Provider:
    return providers.create_provider(name)


def default_provider_name() -> str:
    if _state.CURRENT_PROVIDER:
        return _state.CURRENT_PROVIDER
    return str(ut.config_data.get("provider", {}).get("source", "animeunity"))


def set_current_provider(name: str) -> None:
    """Persist the active provider for the current session."""
    if name in providers.PROVIDERS_AVAILABLE:
        _state.CURRENT_PROVIDER = name


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
    query ($year: Int, $season: MediaSeason) {
      Page(page: 1, perPage: 50) {
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
        }
      }
    }
    """
    response = httpx.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": {"year": year, "season": season}},
        timeout=12,
    )
    response.raise_for_status()
    media = response.json().get("data", {}).get("Page", {}).get("media") or []
    return tuple(_seasonal_from_media(item) for item in media)


def _seasonal_from_media(data: dict[str, object]) -> SeasonalAnime:
    title_data = data.get("title") if isinstance(data.get("title"), dict) else {}
    cover_data = data.get("coverImage") if isinstance(data.get("coverImage"), dict) else {}
    title_romaji = str(title_data.get("romaji") or "") if isinstance(title_data, dict) else ""
    title_english = str(title_data.get("english") or "") if isinstance(title_data, dict) else ""
    title_native = str(title_data.get("native") or "") if isinstance(title_data, dict) else ""
    synonyms_data = data.get("synonyms")
    genres_data = data.get("genres")
    return SeasonalAnime(
        anilist_id=int(data.get("id") or 0),
        title=title_english or title_romaji or title_native,
        title_romaji=title_romaji,
        title_english=title_english,
        title_native=title_native,
        synonyms=tuple(str(item) for item in synonyms_data if item) if isinstance(synonyms_data, list) else (),
        cover_url=str(cover_data.get("extraLarge") or cover_data.get("large") or "") if isinstance(cover_data, dict) else "",
        banner_url=str(data.get("bannerImage") or ""),
        status=str(data.get("status") or ""),
        episodes=int(data.get("episodes") or 0),
        genres=tuple(str(item) for item in genres_data[:3]) if isinstance(genres_data, list) else (),
        average_score=int(data.get("averageScore") or 0),
    )


def seasonal_by_id(year: int, season: str, anilist_id: int) -> SeasonalAnime | None:
    for anime in seasonal_anime(year, season):
        if anime.anilist_id == anilist_id:
            return anime
    return None


def seasonal_open_url(provider_name: str, anime: Anime) -> str:
    return (
        f"/anime?provider={quote(provider_name, safe='')}&name={quote(anime.name, safe='')}"
        f"&ref={quote(anime.ref, safe='')}&curr_ep={quote(anime.curr_ep, safe='')}"
        f"&last_ep={quote(anime.last_ep, safe='')}&anilist_id={quote(str(anime.anilist_id), safe='')}"
    )


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


def stream_token(provider_name: str, anime: Anime, episode_num: str) -> str:
    prune_streams()
    token = uuid4().hex
    STREAMS[token] = {
        "provider": provider_name,
        "anime": anime_to_json(anime),
        "episode": episode_num,
        "url": "",
        "created_at": time.time(),
    }
    return token


def prune_streams(now: float | None = None) -> None:
    now = now or time.time()
    expired = [
        token
        for token, data in STREAMS.items()
        if now - float(data.get("created_at") or 0) > STREAM_TTL_SECONDS
    ]
    for token in expired:
        STREAMS.pop(token, None)

    if len(STREAMS) <= MAX_STREAMS:
        return

    oldest = sorted(
        STREAMS,
        key=lambda token: float(STREAMS[token].get("created_at") or 0),
    )
    for token in oldest[: len(STREAMS) - MAX_STREAMS]:
        STREAMS.pop(token, None)


def stream_context(token: str) -> tuple[str, Anime, Anime.Episode]:
    prune_streams()
    data = STREAMS.get(token)
    if not data:
        raise RuntimeError("Sessione video scaduta. Riapri l'episodio dalla pagina anime.")
    provider_name = data["provider"]
    anime = anime_from_json(data["anime"])
    episode_num = data["episode"]
    if not anime.has_episode(episode_num):
        provider = get_provider(provider_name)
        provider.episodes(anime)
        data["anime"] = anime_to_json(anime)
    return provider_name, anime, anime.episode(episode_num)


def resolve_episode_url(token: str) -> tuple[str, dict[str, str]]:
    data = STREAMS.get(token)
    if data and data.get("url"):
        provider_name = data["provider"]
        return validate_media_url(str(data["url"])), dict(get_provider(provider_name).Client.headers)

    provider_name, anime, episode = stream_context(token)
    provider = get_provider(provider_name)
    url = validate_media_url(provider.episode_link(anime, episode))
    if data is not None:
        data["url"] = url
    return url, dict(provider.Client.headers)


def validate_media_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("URL video non valido.")
    if parsed.username or parsed.password:
        raise RuntimeError("URL video non valido.")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTS or hostname.endswith(".localhost"):
        raise RuntimeError("URL video non consentito.")

    try:
        address = ip_address(hostname)
    except ValueError:
        return url

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise RuntimeError("URL video non consentito.")
    return url


def open_external_player(url: str, title: str) -> None:
    url = validate_media_url(url)
    player = ut.config_data.get("player", {})
    player_type = str(player.get("type") or "mpv")
    player_path = str(player.get("path") or shutil.which(player_type) or "")
    if not player_path:
        raise RuntimeError("Nessun player trovato. Installa mpv/vlc o usa il player browser.")

    if player_type == "vlc" or "vlc" in Path(player_path).name.lower():
        command = [player_path, url, "--meta-title", title, "--fullscreen"]
    else:
        command = [player_path, url, f"--force-media-title={title}", "--fullscreen", "--keep-open"]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise RuntimeError(f"Impossibile avviare il player esterno: {exc}") from exc


def anime_detail_url(provider_name: str, anime_ref: str) -> str:
    return f"/anime?saved=1&provider={quote(provider_name, safe='')}&ref={quote(anime_ref, safe='')}"


def save_watch_progress(provider_name: str, anime: Anime, episode: Anime.Episode) -> None:
    cover = get_cover(anime.anilist_id, anime.name)
    DB.upsert_history_item(
        provider=provider_name,
        anime_data=anime.to_dict(),
        cover_url=cover["cover_url"],
        banner_url=cover["banner_url"],
        current_episode=episode.num,
    )
    if DB.find_watch_item(provider_name, anime.ref):
        DB.upsert_watch_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=cover["cover_url"],
            banner_url=cover["banner_url"],
            current_episode=episode.num,
        )
    if DB.find_favorite_item(provider_name, anime.ref):
        DB.upsert_favorite_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=cover["cover_url"],
            banner_url=cover["banner_url"],
            current_episode=episode.num,
        )
