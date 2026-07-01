"""Media URL validation and external player helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from aw_web import utilities as ut
from aw_web.anime import Anime
from aw_web.services.progress import save_watch_progress
from aw_web.services.providers import get_provider


_BLOCKED_HOSTS = {"localhost"}
_HOMEBREW_MPV_PATHS = ("/opt/homebrew/bin/mpv", "/usr/local/bin/mpv")


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


def _existing_mpv_path(path: str) -> str:
    candidate = Path(path).expanduser()
    if candidate.is_file() and "mpv" in candidate.name.lower():
        return str(candidate)
    return ""


def find_mpv_path() -> str:
    """Find the MPV executable using aw-web's supported lookup order."""
    env_path = os.environ.get("AW_WEB_MPV_PATH", "")
    if env_path and (path := _existing_mpv_path(env_path)):
        return path

    configured_path = str(ut.config_data.get("player", {}).get("path") or "")
    if configured_path and (path := _existing_mpv_path(configured_path)):
        return path

    if path := shutil.which("mpv"):
        return path

    for candidate in _HOMEBREW_MPV_PATHS:
        if path := _existing_mpv_path(candidate):
            return path

    return ""


def open_external_player(url: str, title: str) -> None:
    """Open a media URL in MPV without blocking the local web server."""
    url = validate_media_url(url)
    player_path = find_mpv_path()
    if not player_path:
        raise RuntimeError(
            "MPV non trovato. Installa mpv oppure imposta AW_WEB_MPV_PATH con il percorso dell'eseguibile."
        )

    command = [player_path, url, f"--force-media-title={title}", "--fullscreen", "--keep-open"]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise RuntimeError(f"Impossibile avviare MPV: {exc}") from exc


def play_episode(provider_name: str, anime: Anime, episode_num: str) -> None:
    provider = get_provider(provider_name)
    if not anime.has_episode(episode_num):
        provider.episodes(anime)

    episode = anime.episode(episode_num)
    url = provider.episode_link(anime, episode)
    open_external_player(url, str(episode))
    save_watch_progress(provider_name, anime, episode)
