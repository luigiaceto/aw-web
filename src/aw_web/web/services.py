"""Backend services for providers, cover metadata, playback, and watch progress."""

from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx

from aw_web import providers, utilities as ut
from aw_web.anime import Anime
from aw_web.web.state import DB, STREAMS
from aw_web.web.utils import anime_from_json, anime_to_json


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
    return str(ut.config_data.get("provider", {}).get("source", "animeunity"))


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
    token = uuid4().hex
    STREAMS[token] = {
        "provider": provider_name,
        "anime": anime_to_json(anime),
        "episode": episode_num,
        "url": "",
    }
    return token


def stream_context(token: str) -> tuple[str, Anime, Anime.Episode]:
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
        return data["url"], dict(get_provider(provider_name).Client.headers)

    provider_name, anime, episode = stream_context(token)
    provider = get_provider(provider_name)
    url = provider.episode_link(anime, episode)
    if data is not None:
        data["url"] = url
    return url, dict(provider.Client.headers)


def open_external_player(url: str, title: str) -> None:
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
    if not DB.find_watch_item(provider_name, anime.ref):
        cover = get_cover(anime.anilist_id, anime.name)
        DB.upsert_watch_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=cover["cover_url"],
            banner_url=cover["banner_url"],
            current_episode=episode.num,
        )
    DB.update_current_episode(provider_name, anime.ref, episode.num)
