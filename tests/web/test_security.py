import json
import socket
from http.client import HTTPMessage
from io import BytesIO
from typing import cast
from unittest.mock import MagicMock

import pytest

from aw_web.anime import Anime
from aw_web.services import playback
from aw_web.services.playback import find_mpv_path, open_external_player, validate_media_url
from aw_web.web import server
from aw_web.web.components import page, watch_card
from aw_web.web.db import WebDatabase
from aw_web.web.server import (
    ALLOWED_ORIGINS,
    WebHandler,
    favicon_bytes,
    handle_play,
    handle_play_start,
    handle_play_status,
)
from aw_web.web.state import CSRF_TOKEN
from aw_web.web.utils import anime_to_json
from aw_web.web.views import render_anime


def headers(values: dict[str, str] | None = None) -> HTTPMessage:
    message = HTTPMessage()
    for name, value in (values or {}).items():
        message[name] = value
    return message


def test_validate_media_url_allows_public_http_urls():
    url = "https://cdn.example.com/video.mp4"

    assert validate_media_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/video.mp4",
        "http://localhost/video.mp4",
        "http://127.0.0.1/video.mp4",
        "http://10.0.0.5/video.mp4",
        "http://192.168.1.10/video.mp4",
        "http://172.16.0.10/video.mp4",
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


def test_open_external_player_launches_mpv_without_blocking(monkeypatch):
    launched = []
    waited = []
    unlinked = []
    process = MagicMock()
    process.poll.return_value = None

    def fake_popen(command, stdout=None, stderr=None):
        launched.append((command, stdout, stderr))
        return process

    monkeypatch.setattr("aw_web.services.playback.find_mpv_path", lambda: "/usr/bin/mpv")
    monkeypatch.setattr("aw_web.services.playback._mpv_ipc_path", lambda: "/tmp/aw-web-test.sock")
    monkeypatch.setattr(
        "aw_web.services.playback._wait_for_mpv_ready",
        lambda ipc_path, mpv_process, url: waited.append((ipc_path, mpv_process, url)) or True,
    )
    monkeypatch.setattr("aw_web.services.playback.os.unlink", lambda path: unlinked.append(path))
    monkeypatch.setattr("aw_web.services.playback.subprocess.Popen", fake_popen)

    open_external_player("https://cdn.example.com/video.mp4", "Episode 1")

    assert launched[0][0] == [
        "/usr/bin/mpv",
        "--force-media-title=Episode 1",
        "--fullscreen",
        "--keep-open",
        "--input-ipc-server=/tmp/aw-web-test.sock",
        "--idle=yes",
    ]
    assert "--force-window=immediate" not in launched[0][0]
    assert "https://cdn.example.com/video.mp4" not in launched[0][0]
    assert waited == [("/tmp/aw-web-test.sock", process, "https://cdn.example.com/video.mp4")]
    assert unlinked == ["/tmp/aw-web-test.sock"]


def test_mpv_ipc_path_uses_short_tmp_path():
    path = playback._mpv_ipc_path()

    assert path.startswith("/tmp/aw-web-mpv-")
    assert len(path) < 100


def test_open_external_player_raises_when_mpv_is_not_ready(monkeypatch):
    process = MagicMock()
    process.poll.return_value = None
    unlinked = []

    monkeypatch.setattr("aw_web.services.playback.find_mpv_path", lambda: "/usr/bin/mpv")
    monkeypatch.setattr("aw_web.services.playback._mpv_ipc_path", lambda: "/tmp/aw-web-test.sock")
    monkeypatch.setattr("aw_web.services.playback._wait_for_mpv_ready", lambda *args: False)
    monkeypatch.setattr("aw_web.services.playback.subprocess.Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr("aw_web.services.playback.os.unlink", lambda path: unlinked.append(path))

    with pytest.raises(RuntimeError, match="non è partito"):
        open_external_player("https://cdn.example.com/video.mp4", "Episode 1")

    assert unlinked == ["/tmp/aw-web-test.sock"]


@pytest.mark.parametrize(
    "message",
    [
        {"event": "file-loaded"},
        {"event": "playback-restart"},
        {"event": "property-change", "name": "vo-configured", "data": True},
        {"request_id": playback._MPV_PROPERTY_REQUEST_IDS["vo-configured"], "error": "success", "data": True},
        {"event": "property-change", "name": "time-pos", "data": 0.0},
        {"request_id": playback._MPV_PROPERTY_REQUEST_IDS["playback-time"], "error": "success", "data": 1.5},
    ],
)
def test_mpv_ready_message_accepts_ready_signals(message):
    assert playback._mpv_ready_from_message(message)


def test_wait_for_mpv_ready_raises_when_mpv_closes():
    process = MagicMock()
    process.poll.return_value = 1

    with pytest.raises(RuntimeError, match="MPV si è chiuso"):
        playback._wait_for_mpv_ready("/tmp/missing.sock", process, "https://cdn.example.com/video.mp4", timeout=0.1)


def test_wait_for_mpv_ready_timeout_succeeds_if_process_is_alive():
    process = MagicMock()
    process.poll.return_value = None

    assert not playback._wait_for_mpv_ready("/tmp/missing.sock", process, "https://cdn.example.com/video.mp4", timeout=0.0)


def test_read_until_mpv_ready_sends_loadfile_after_observing_properties(monkeypatch):
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
        "request_id": playback._MPV_PROPERTY_REQUEST_IDS["loadfile"],
    }


def test_anime_page_treats_invalid_anilist_id_as_missing(monkeypatch):
    provider = MagicMock()
    provider.info_anime.return_value = None
    provider.episodes.return_value = None

    monkeypatch.setattr("aw_web.web.views.get_provider", lambda provider_name: provider)
    monkeypatch.setattr(
        "aw_web.web.views.get_cover",
        lambda anilist_id, title: {"cover_url": "", "banner_url": "", "color": ""},
    )

    body = render_anime(
        {
            "provider": ["animeunity"],
            "name": ["Example"],
            "ref": ["123"],
            "anilist_id": ["None"],
        }
    )

    assert b"Example" in body


def test_anime_page_uses_mpv_play_forms(monkeypatch):
    provider = MagicMock()
    provider.info_anime.return_value = None
    provider.episodes.side_effect = lambda anime: anime.update_episodes({"1": "episode-ref"})

    monkeypatch.setattr("aw_web.web.views.get_provider", lambda provider_name: provider)
    monkeypatch.setattr(
        "aw_web.web.views.get_cover",
        lambda anilist_id, title: {"cover_url": "", "banner_url": "", "color": ""},
    )

    body = render_anime(
        {
            "provider": ["animeunity"],
            "name": ["Example"],
            "ref": ["123"],
            "curr_ep": ["1"],
            "last_ep": ["1"],
        }
    )

    assert b'action="/play"' in body
    assert b"/watch/start" not in body
    assert b"<video" not in body


def test_watchlist_card_uses_mpv_play_form():
    anime = Anime("Example", "provider-ref", curr_ep="1", last_ep="2")
    anime.update_episodes({"1": "episode-ref", "2": "episode-ref-2"})
    html = watch_card(
        {
            "id": 1,
            "provider": "animeunity",
            "name": "Example",
            "ref": "provider-ref",
            "anime_json": anime_to_json(anime),
            "current_episode": "1",
            "last_episode": "2",
            "cover_url": "",
        },
        [],
    )

    assert 'action="/play"' in html
    assert "/watch/start" not in html


def test_handle_play_opens_mpv_and_saves_progress(monkeypatch):
    anime = Anime("Example", "provider-ref", curr_ep="1", last_ep="2")
    anime.update_episodes({"1": "episode-ref", "2": "episode-ref-2"})
    provider = MagicMock()
    provider.episode_link.return_value = "https://cdn.example.com/video.mp4"
    opened = []
    saved = []

    monkeypatch.setattr("aw_web.services.playback.get_provider", lambda provider_name: provider)
    monkeypatch.setattr("aw_web.services.playback.open_external_player", lambda url, title: opened.append((url, title)))
    monkeypatch.setattr(
        "aw_web.services.playback.save_watch_progress",
        lambda provider_name, saved_anime, episode: saved.append((provider_name, saved_anime.ref, episode.num)),
    )

    response = handle_play(
        {
            "provider": ["animeunity"],
            "anime": [anime_to_json(anime)],
            "episode": ["2"],
        }
    )

    assert response.startswith(b"REDIRECT:/anime?")
    assert opened == [("https://cdn.example.com/video.mp4", "Example Ep. 2")]
    assert saved == [("animeunity", "provider-ref", "2")]


def test_handle_play_start_returns_json_and_starts_job(monkeypatch):
    anime = Anime("Example", "provider-ref", curr_ep="1", last_ep="2")
    anime.update_episodes({"2": "episode-ref-2"})
    started = []

    monkeypatch.setattr(server, "PLAYBACK_JOBS", {})
    monkeypatch.setattr(
        "aw_web.web.server.start_playback_job",
        lambda job_id, provider_name, saved_anime, episode_num: started.append(
            (job_id, provider_name, saved_anime.ref, episode_num)
        ),
    )

    response = handle_play_start(
        {
            "provider": ["animeunity"],
            "anime": [anime_to_json(anime)],
            "episode": ["2"],
        }
    )

    payload = json.loads(response)
    assert payload["job_id"]
    assert payload["status_url"] == f"/play/status?id={payload['job_id']}"
    assert payload["redirect"].startswith("/anime?")
    assert "provider=animeunity" in payload["redirect"]
    assert started == [(payload["job_id"], "animeunity", "provider-ref", "2")]


def test_handle_play_status_returns_ready_job(monkeypatch):
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"job-id": server.PlaybackJob(redirect="/anime")})
    server.PLAYBACK_JOBS["job-id"].status = "ready"

    response = handle_play_status({"id": ["job-id"]})

    assert json.loads(response) == {"status": "ready", "redirect": "/anime", "error": ""}


def test_handle_play_status_marks_old_pending_job_as_error(monkeypatch):
    job = server.PlaybackJob(redirect="/anime", created_at=0)
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"job-id": job})
    monkeypatch.setattr(server.time, "monotonic", lambda: server.PLAYBACK_JOB_TIMEOUT_SECONDS + 1)

    response = handle_play_status({"id": ["job-id"]})

    payload = json.loads(response)
    assert payload["status"] == "error"
    assert "Timeout" in payload["error"]


def test_handle_play_status_returns_error_for_missing_job():
    response = handle_play_status({"id": ["missing"]})

    payload = json.loads(response)
    assert payload["status"] == "error"
    assert "non trovata" in payload["error"]


def test_post_play_start_uses_json_response(monkeypatch):
    raw = f"csrf_token={CSRF_TOKEN}".encode("utf-8")
    handler = object.__new__(WebHandler)
    handler.headers = headers({"Content-Length": str(len(raw))})
    handler.rfile = BytesIO(raw)
    handler.path = "/play/start"
    captured = {}

    def fake_respond_json(body, status=200):
        captured["body"] = body
        captured["status"] = status

    handler.respond_json = fake_respond_json
    monkeypatch.setattr("aw_web.web.server.handle_play_start", lambda fields: b'{"job_id":"job"}')

    handler.do_POST()

    assert captured == {"body": b'{"job_id":"job"}', "status": 200}


def test_post_play_failure_returns_error_page(monkeypatch):
    raw = f"csrf_token={CSRF_TOKEN}".encode("utf-8")
    handler = object.__new__(WebHandler)
    handler.headers = headers({"Content-Length": str(len(raw))})
    handler.rfile = BytesIO(raw)
    handler.path = "/play"
    captured = {}

    def fake_respond(body, status=200):
        captured["body"] = body
        captured["status"] = status

    handler.respond = fake_respond
    monkeypatch.setattr(
        "aw_web.web.server.handle_play",
        lambda fields: (_ for _ in ()).throw(RuntimeError("MPV non trovato")),
    )

    handler.do_POST()

    assert captured["status"] == 500
    assert b"MPV non trovato" in captured["body"]


def test_get_watchlist_cards_returns_json(monkeypatch):
    handler = object.__new__(WebHandler)
    handler.path = "/watchlist/cards"
    captured = {}

    def fake_respond_json(body, status=200):
        captured["body"] = body
        captured["status"] = status

    handler.respond_json = fake_respond_json
    monkeypatch.setattr(
        "aw_web.web.server.watchlist_cards_payload",
        lambda: b'{"refreshing": false, "html": "<p>cards</p>"}',
    )

    handler.do_GET()

    assert captured == {"body": b'{"refreshing": false, "html": "<p>cards</p>"}', "status": 200}


def test_anime_page_saved_does_not_refetch_episodes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Saved Anime", "123", curr_ep="1", last_ep="12")
    anime.update_episodes({"1": "episode-ref"})
    db.upsert_watch_item(provider="animeunity", anime_data=anime.to_dict(), current_episode="1")

    provider = MagicMock()
    provider.info_anime.return_value = None
    monkeypatch.setattr("aw_web.web.views.DB", db)
    monkeypatch.setattr("aw_web.web.views.get_provider", lambda provider_name: provider)
    monkeypatch.setattr(
        "aw_web.web.views.get_cover",
        lambda anilist_id, title: {"cover_url": "", "banner_url": "", "color": ""},
    )

    body = render_anime({"provider": ["animeunity"], "saved": ["1"], "ref": ["123"]})

    provider.episodes.assert_not_called()
    assert b"Ep. 1" in body


def test_handle_play_start_prunes_old_jobs(monkeypatch):
    anime = Anime("Example", "provider-ref", curr_ep="1", last_ep="1")
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"old": server.PlaybackJob(redirect="/anime", created_at=0)})
    monkeypatch.setattr(server, "start_playback_job", lambda *args: None)

    server.handle_play_start(
        {
            "provider": ["animeunity"],
            "anime": [anime_to_json(anime)],
            "episode": ["1"],
        }
    )

    assert "old" not in server.PLAYBACK_JOBS
    assert len(server.PLAYBACK_JOBS) == 1


def test_page_includes_favicon_link():
    assert b'<link rel="icon" href="/favicon.ico?v=1" sizes="any">' in page("Test", "")


def test_page_includes_play_loading_script():
    body = page("Test", "")

    assert b'form.getAttribute("action") !== "/play"' in body
    assert b"event.preventDefault()" in body
    assert b'fetch("/play/start"' in body
    assert b"waitForPlayback" in body
    assert b"payload.status_url" in body
    assert b"play-spinner" in body
    assert b"is-loading" in body


def test_favicon_is_packaged():
    assert favicon_bytes()


def test_post_origin_check_allows_only_local_origins():
    handler = object.__new__(WebHandler)

    handler.headers = headers()
    assert handler.same_origin()

    handler.headers = headers({"Origin": next(iter(ALLOWED_ORIGINS))})
    assert handler.same_origin()

    handler.headers = headers({"Origin": "https://example.com"})
    assert not handler.same_origin()


def test_play_status_requests_are_not_logged(monkeypatch):
    handler = object.__new__(WebHandler)
    written = []
    monkeypatch.setattr("aw_web.web.server.sys.stderr.write", lambda text: written.append(text))

    handler.log_message('"%s" %s %s', "GET /play/status?id=job HTTP/1.1", "200", "-")

    assert written == []


def test_csrf_check_requires_session_token():
    handler = object.__new__(WebHandler)

    assert handler.valid_csrf({"csrf_token": [CSRF_TOKEN]})
    assert not handler.valid_csrf({"csrf_token": ["wrong"]})
    assert not handler.valid_csrf({})
