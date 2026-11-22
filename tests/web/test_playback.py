"""Test dell'apertura dei video in MPV."""

import json
import socket
from typing import cast
from unittest.mock import MagicMock

import pytest

from aw_web.services import playback
from aw_web.services.playback import find_mpv_path, open_external_player, validate_media_url

READY_ID = playback._MPV_PROPERTY_REQUEST_IDS


def test_validate_media_url_allows_public_http_urls():
    url = "https://cdn.example.com/video.mp4"

    assert validate_media_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/video.mp4",
        "http://localhost/video.mp4",
        "http://app.localhost/video.mp4",
        "http://127.0.0.1/video.mp4",
        "http://[::1]/video.mp4",
        "http://0.0.0.0/video.mp4",
        "http://10.0.0.5/video.mp4",
        "http://192.168.1.10/video.mp4",
        "http://172.16.0.10/video.mp4",
        "http://user:pass@cdn.example.com/video.mp4",
    ],
)
def test_validate_media_url_rejects_local_targets(url):
    with pytest.raises(RuntimeError):
        validate_media_url(url)


def test_find_mpv_path_uses_environment_path(monkeypatch, tmp_path):
    mpv_path = tmp_path / "mpv"
    mpv_path.write_text("")
    monkeypatch.setenv("AW_WEB_MPV_PATH", str(mpv_path))
    monkeypatch.setattr("aw_web.services.playback.shutil.which", lambda name: "")

    assert find_mpv_path() == str(mpv_path)


def test_find_mpv_path_falls_back_to_path(monkeypatch):
    monkeypatch.delenv("AW_WEB_MPV_PATH", raising=False)
    monkeypatch.setattr("aw_web.services.playback.shutil.which", lambda name: "/usr/bin/mpv")

    assert find_mpv_path() == "/usr/bin/mpv"


def test_find_mpv_path_returns_empty_when_mpv_is_missing(monkeypatch):
    monkeypatch.delenv("AW_WEB_MPV_PATH", raising=False)
    monkeypatch.setattr("aw_web.services.playback.shutil.which", lambda name: "")
    monkeypatch.setattr("aw_web.services.playback._HOMEBREW_MPV_PATHS", ())

    assert find_mpv_path() == ""


@pytest.fixture
def fake_mpv(monkeypatch):
    """MPV finto: registra il comando lanciato e il socket rimosso a fine apertura."""
    process = MagicMock()
    process.poll.return_value = None
    calls = {"launched": [], "unlinked": []}
    monkeypatch.setattr("aw_web.services.playback.find_mpv_path", lambda: "/usr/bin/mpv")
    monkeypatch.setattr("aw_web.services.playback._mpv_ipc_path", lambda: "/tmp/aw-web-test.sock")
    monkeypatch.setattr(
        "aw_web.services.playback.subprocess.Popen",
        lambda command, **kwargs: calls["launched"].append(command) or process,
    )
    monkeypatch.setattr(
        "aw_web.services.playback.Path.unlink", lambda path, missing_ok: calls["unlinked"].append(str(path))
    )
    return process, calls


def test_open_external_player_loads_the_video_through_the_ipc_socket(monkeypatch, fake_mpv):
    process, calls = fake_mpv
    waited = []
    monkeypatch.setattr(
        "aw_web.services.playback._wait_for_mpv_ready",
        lambda ipc_path, mpv_process, url: waited.append((ipc_path, mpv_process, url)) or True,
    )

    open_external_player("https://cdn.example.com/video.mp4", "Episode 1")

    assert calls["launched"] == [[
        "/usr/bin/mpv",
        "--force-media-title=Episode 1",
        "--fullscreen",
        "--keep-open",
        "--input-ipc-server=/tmp/aw-web-test.sock",
        "--idle=yes",
    ]]
    assert waited == [("/tmp/aw-web-test.sock", process, "https://cdn.example.com/video.mp4")]
    assert calls["unlinked"] == ["/tmp/aw-web-test.sock"]


def test_open_external_player_raises_when_mpv_is_not_ready(monkeypatch, fake_mpv):
    _, calls = fake_mpv
    monkeypatch.setattr("aw_web.services.playback._wait_for_mpv_ready", lambda *args: False)

    with pytest.raises(RuntimeError, match="non è partito"):
        open_external_player("https://cdn.example.com/video.mp4", "Episode 1")

    assert calls["unlinked"] == ["/tmp/aw-web-test.sock"]


def test_mpv_ipc_path_fits_the_unix_socket_limit():
    path = playback._mpv_ipc_path()

    assert path.startswith("/tmp/aw-web-mpv-")
    assert len(path) < 100  # macOS accetta al massimo 104 caratteri per un socket Unix


@pytest.mark.parametrize(
    "message",
    [
        {"event": "file-loaded"},
        {"event": "playback-restart"},
        {"event": "property-change", "name": "vo-configured", "data": True},
        {"request_id": READY_ID["vo-configured"], "error": "success", "data": True},
        {"event": "property-change", "name": "time-pos", "data": 0.0},
        {"request_id": READY_ID["playback-time"], "error": "success", "data": 1.5},
    ],
)
def test_mpv_ready_message_accepts_ready_signals(message):
    assert playback._mpv_ready_from_message(message)


@pytest.mark.parametrize(
    "message",
    [
        {"event": "start-file"},
        {"event": "property-change", "name": "vo-configured", "data": False},
        {"event": "property-change", "name": "time-pos", "data": None},
        {"request_id": READY_ID["time-pos"], "error": "property unavailable"},
        {"request_id": READY_ID["loadfile"], "error": "success", "data": None},
        {"request_id": READY_ID["playback-time"], "error": "success", "data": True},
    ],
)
def test_mpv_ready_message_ignores_signals_before_the_video_starts(message):
    # un falso "pronto" salverebbe come visto un episodio mai partito
    assert not playback._mpv_ready_from_message(message)


def test_wait_for_mpv_ready_raises_when_mpv_closes():
    process = MagicMock()
    process.poll.return_value = 1

    with pytest.raises(RuntimeError, match="MPV si è chiuso"):
        playback._wait_for_mpv_ready("/tmp/missing.sock", process, "https://cdn.example.com/video.mp4", timeout=0.1)


def test_wait_for_mpv_ready_returns_false_on_timeout_if_mpv_is_alive():
    process = MagicMock()
    process.poll.return_value = None

    assert not playback._wait_for_mpv_ready("/tmp/missing.sock", process, "https://cdn.example.com/video.mp4", timeout=0.0)


def test_read_until_mpv_ready_sends_loadfile_after_observing_properties():
    sent = []
    process = MagicMock()
    process.poll.return_value = None

    class FakeSocket:
        def sendall(self, payload):
            sent.append(json.loads(payload.decode("utf-8")))

        def settimeout(self, timeout):
            pass

        def recv(self, size):
            return b'{"event":"file-loaded"}\n'

    assert playback._read_until_mpv_ready(
        cast(socket.socket, FakeSocket()),
        process,
        "https://cdn.example.com/video.mp4",
        9999999999.0,
    )
    assert sent[:3] == [
        {"command": ["observe_property", 1, "vo-configured"]},
        {"command": ["observe_property", 2, "time-pos"]},
        {"command": ["observe_property", 3, "playback-time"]},
    ]
    assert sent[3] == {
        "command": ["loadfile", "https://cdn.example.com/video.mp4", "replace"],
        "request_id": READY_ID["loadfile"],
    }
