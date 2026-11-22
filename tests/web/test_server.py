"""Test del server HTTP: sicurezza dei POST, routing e job di riproduzione."""

import json
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock

import httpx
import pytest

from aw_web.anime import Anime
from aw_web.web import server
from aw_web.web.server import WebHandler, favicon_bytes, handle_play, handle_play_start, handle_play_status
from aw_web.web.state import CSRF_TOKEN, DB
from aw_web.web.utils import anime_to_json


@pytest.fixture
def base_url():
    """Il server vero su una porta libera; il database è quello isolato di conftest."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), WebHandler)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _post(base_url: str, path: str, data: dict[str, str], **headers: str) -> httpx.Response:
    return httpx.post(f"{base_url}{path}", data=data, headers=headers, follow_redirects=False)


def test_post_toggles_and_removes_a_watchlist_item(base_url):
    anime = Anime("Example", "4851")
    form = {"csrf_token": CSRF_TOKEN, "anime": anime_to_json(anime)}

    added = _post(base_url, "/watchlist/toggle", form)

    assert added.status_code == 303
    assert added.headers["Location"] == "/anime?name=Example&ref=4851"
    assert DB.find("watchlist", "4851") is not None

    removed = _post(base_url, "/watchlist/remove", {"csrf_token": CSRF_TOKEN, "ref": "4851"})

    assert removed.status_code == 303
    assert DB.find("watchlist", "4851") is None


@pytest.mark.parametrize(
    ("data", "headers"),
    [
        ({}, {}),  # nessun token
        ({"csrf_token": "wrong"}, {}),
        ({"csrf_token": CSRF_TOKEN}, {"Origin": "https://evil.example"}),  # pagina di un altro sito
    ],
)
def test_post_without_valid_token_or_origin_is_rejected(base_url, data, headers):
    anime = Anime("Example", "4851")

    response = _post(base_url, "/watchlist/toggle", {**data, "anime": anime_to_json(anime)}, **headers)

    assert response.status_code == 403
    assert DB.find("watchlist", "4851") is None


def test_post_accepts_the_local_origin(base_url):
    anime = Anime("Example", "4851")
    form = {"csrf_token": CSRF_TOKEN, "anime": anime_to_json(anime)}

    response = _post(base_url, "/favorites/toggle", form, Origin=next(iter(server.ALLOWED_ORIGINS)))

    assert response.status_code == 303


def test_post_with_a_too_large_body_is_rejected(base_url, monkeypatch):
    monkeypatch.setattr(server, "MAX_POST_BYTES", 10)

    response = _post(base_url, "/watchlist/toggle", {"csrf_token": CSRF_TOKEN})

    assert response.status_code == 413


def test_post_failure_shows_an_error_page(base_url):
    response = _post(base_url, "/play", {"csrf_token": CSRF_TOKEN, "anime": "{}"})

    assert response.status_code == 500
    assert "Torna alla home" in response.text


def test_get_json_endpoints(base_url):
    cards = httpx.get(f"{base_url}/watchlist/cards")
    status = httpx.get(f"{base_url}/play/status", params={"id": "missing"})

    assert cards.headers["Content-Type"].startswith("application/json")
    assert cards.json()["refreshing"] in (True, False)
    assert status.json()["status"] == "error"


def test_favicon_is_packaged():
    assert favicon_bytes()


def test_play_status_requests_are_not_logged(monkeypatch):
    handler = object.__new__(WebHandler)
    written = []
    monkeypatch.setattr("aw_web.web.server.sys.stderr.write", lambda text: written.append(text))

    handler.log_message('"%s" %s %s', "GET /play/status?id=job HTTP/1.1", "200", "-")

    assert written == []


def test_handle_play_opens_mpv_and_saves_progress(monkeypatch):
    anime = Anime("Example", "4851", curr_ep="1", last_ep="2")
    anime.update_episodes({"1": "episode-ref", "2": "episode-ref-2"})
    provider = MagicMock()
    provider.episode_link.return_value = "https://cdn.example.com/video.mp4"
    opened = []
    saved = []
    monkeypatch.setattr("aw_web.services.playback.PROVIDER", provider)
    monkeypatch.setattr("aw_web.services.playback.open_external_player", lambda url, title: opened.append((url, title)))
    monkeypatch.setattr(
        "aw_web.services.playback.save_watch_progress",
        lambda saved_anime, episode: saved.append((saved_anime.ref, episode.num)),
    )

    response = handle_play({"anime": [anime_to_json(anime)], "episode": ["2"]})

    assert response.startswith(b"REDIRECT:/anime?")
    assert opened == [("https://cdn.example.com/video.mp4", "Example Ep. 2")]
    assert saved == [("4851", "2")]


def test_handle_play_start_returns_json_and_starts_job(monkeypatch):
    anime = Anime("Example", "4851", curr_ep="1", last_ep="2")
    anime.update_episodes({"2": "episode-ref-2"})
    started = []
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {})
    monkeypatch.setattr(
        server, "start_playback_job", lambda job_id, saved_anime, episode_num: started.append((job_id, saved_anime.ref, episode_num))
    )

    payload = json.loads(handle_play_start({"anime": [anime_to_json(anime)], "episode": ["2"]}))

    assert payload["status_url"] == f"/play/status?id={payload['job_id']}"
    assert payload["redirect"] == "/anime?name=Example&ref=4851"
    assert started == [(payload["job_id"], "4851", "2")]


def test_handle_play_start_prunes_old_jobs(monkeypatch):
    anime = Anime("Example", "4851", curr_ep="1", last_ep="1")
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"old": server.PlaybackJob(redirect="/anime", created_at=0)})
    monkeypatch.setattr(server, "start_playback_job", lambda *args: None)

    handle_play_start({"anime": [anime_to_json(anime)], "episode": ["1"]})

    assert "old" not in server.PLAYBACK_JOBS
    assert len(server.PLAYBACK_JOBS) == 1


@pytest.mark.parametrize(
    ("error", "expected"),
    [(None, {"status": "ready", "error": ""}), (RuntimeError("MPV non trovato"), {"status": "error", "error": "MPV non trovato"})],
)
def test_run_playback_job_reports_the_outcome(monkeypatch, error, expected):
    def fake_play(anime, episode_num):
        if error:
            raise error

    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"job": server.PlaybackJob(redirect="/anime")})
    monkeypatch.setattr(server, "play_episode", fake_play)

    server.run_playback_job("job", Anime("Example", "4851"), "1")

    assert json.loads(handle_play_status({"id": ["job"]})) == {**expected, "redirect": "/anime"}


def test_handle_play_status_marks_old_pending_job_as_error(monkeypatch):
    monkeypatch.setattr(server, "PLAYBACK_JOBS", {"job": server.PlaybackJob(redirect="/anime", created_at=0)})
    monkeypatch.setattr(server.time, "monotonic", lambda: server.PLAYBACK_JOB_TIMEOUT_SECONDS + 1)

    payload = json.loads(handle_play_status({"id": ["job"]}))

    assert payload["status"] == "error"
    assert "Timeout" in payload["error"]


def test_handle_play_status_returns_error_for_missing_job():
    payload = json.loads(handle_play_status({"id": ["missing"]}))

    assert payload["status"] == "error"
    assert "non trovata" in payload["error"]
