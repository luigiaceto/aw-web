"""Media URL validation and external player helpers."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from aw_web import utilities as ut
from aw_web.anime import Anime
from aw_web.services.progress import save_watch_progress
from aw_web.services.providers import get_provider


_BLOCKED_HOSTS = {"localhost"}
_HOMEBREW_MPV_PATHS = ("/opt/homebrew/bin/mpv", "/usr/local/bin/mpv")
_MPV_READY_TIMEOUT_SECONDS = 60.0
_MPV_PROPERTY_REQUEST_IDS = {
    "vo-configured": 1001,
    "time-pos": 1002,
    "playback-time": 1003,
    "loadfile": 1004,
}
_MPV_OBSERVED_PROPERTIES = ("vo-configured", "time-pos", "playback-time")
_MPV_READY_EVENTS = {"file-loaded", "playback-restart"}


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


def _mpv_ipc_path() -> str:
    return str(Path("/tmp") / f"aw-web-mpv-{os.getpid()}-{uuid.uuid4().hex}.sock")


def _numeric(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _mpv_ready_from_message(message: dict[str, object]) -> bool:
    if message.get("event") in _MPV_READY_EVENTS:
        return True
    if message.get("event") == "property-change":
        name = message.get("name")
        data = message.get("data")
        return (name == "vo-configured" and data is True) or (name in {"time-pos", "playback-time"} and _numeric(data))

    request_id = message.get("request_id")
    if message.get("error") != "success":
        return False
    if request_id == _MPV_PROPERTY_REQUEST_IDS["vo-configured"]:
        return message.get("data") is True
    if request_id in {
        _MPV_PROPERTY_REQUEST_IDS["time-pos"],
        _MPV_PROPERTY_REQUEST_IDS["playback-time"],
    }:
        return _numeric(message.get("data"))
    return False


def _send_mpv_command(client: socket.socket, command: list[object], request_id: int | None = None) -> None:
    payload: dict[str, object] = {"command": command}
    if request_id is not None:
        payload["request_id"] = request_id
    client.sendall(json.dumps(payload).encode("utf-8") + b"\n")


def _read_until_mpv_ready(client: socket.socket, process: subprocess.Popen[bytes], url: str, deadline: float) -> bool:
    buffer = b""
    next_probe = 0.0
    for observer_id, name in enumerate(_MPV_OBSERVED_PROPERTIES, start=1):
        _send_mpv_command(client, ["observe_property", observer_id, name])
    _send_mpv_command(client, ["loadfile", url, "replace"], _MPV_PROPERTY_REQUEST_IDS["loadfile"])

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("MPV si è chiuso prima di avviare la riproduzione.")

        now = time.monotonic()
        if now >= next_probe:
            for name in _MPV_OBSERVED_PROPERTIES:
                _send_mpv_command(client, ["get_property", name], _MPV_PROPERTY_REQUEST_IDS[name])
            next_probe = now + 0.25

        client.settimeout(max(0.05, min(0.25, deadline - now)))
        try:
            chunk = client.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            return False

        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                message = json.loads(line.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and _mpv_ready_from_message(message):
                return True
    return False


def _wait_for_mpv_ready(
    ipc_path: str,
    process: subprocess.Popen[bytes],
    url: str,
    timeout: float = _MPV_READY_TIMEOUT_SECONDS,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("MPV si è chiuso prima di avviare la riproduzione.")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(ipc_path)
                return _read_until_mpv_ready(client, process, url, deadline)
        except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.05)

    if process.poll() is not None:
        raise RuntimeError("MPV si è chiuso prima di avviare la riproduzione.")
    return False


def open_external_player(url: str, title: str) -> None:
    """Open a media URL in MPV and wait briefly for a playback-ready signal."""
    url = validate_media_url(url)
    player_path = find_mpv_path()
    if not player_path:
        raise RuntimeError(
            "MPV non trovato. Installa mpv oppure imposta AW_WEB_MPV_PATH con il percorso dell'eseguibile."
        )

    ipc_path = _mpv_ipc_path() if hasattr(socket, "AF_UNIX") else ""
    command = [player_path, f"--force-media-title={title}", "--fullscreen", "--keep-open"]
    if ipc_path:
        command.extend([f"--input-ipc-server={ipc_path}", "--idle=yes"])
    else:
        command.append(url)
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise RuntimeError(f"Impossibile avviare MPV: {exc}") from exc
    try:
        if ipc_path:
            _wait_for_mpv_ready(ipc_path, process, url)
    finally:
        if ipc_path:
            try:
                os.unlink(ipc_path)
            except FileNotFoundError:
                pass


def play_episode(provider_name: str, anime: Anime, episode_num: str) -> None:
    provider = get_provider(provider_name)
    if not anime.has_episode(episode_num):
        provider.episodes(anime)

    episode = anime.episode(episode_num)
    url = provider.episode_link(anime, episode)
    open_external_player(url, str(episode))
    save_watch_progress(provider_name, anime, episode)
