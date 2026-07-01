from http.client import HTTPMessage
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from aw_web import utilities as ut
from aw_web.anime import Anime
from aw_web.services.playback import find_mpv_path, open_external_player, validate_media_url
from aw_web.web.components import page, watch_card
from aw_web.web.server import (
    ALLOWED_ORIGINS,
    WebHandler,
    favicon_bytes,
    handle_play,
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
    monkeypatch.setattr(ut, "config_data", {"player": {"path": ""}})
    monkeypatch.setattr("aw_web.services.playback.shutil.which", lambda name: "/usr/bin/mpv")

    assert find_mpv_path() == "/usr/bin/mpv"


def test_find_mpv_path_returns_empty_when_mpv_is_missing(monkeypatch):
    monkeypatch.delenv("AW_WEB_MPV_PATH", raising=False)
    monkeypatch.setattr(ut, "config_data", {"player": {"path": ""}})
    monkeypatch.setattr("aw_web.services.playback.shutil.which", lambda name: "")
    monkeypatch.setattr("aw_web.services.playback._HOMEBREW_MPV_PATHS", ())

    assert find_mpv_path() == ""


def test_open_external_player_launches_mpv_without_blocking(monkeypatch):
    launched = []

    def fake_popen(command, stdout=None, stderr=None):
        launched.append((command, stdout, stderr))

    monkeypatch.setattr("aw_web.services.playback.find_mpv_path", lambda: "/usr/bin/mpv")
    monkeypatch.setattr("aw_web.services.playback.subprocess.Popen", fake_popen)

    open_external_player("https://cdn.example.com/video.mp4", "Episode 1")

    assert launched[0][0] == [
        "/usr/bin/mpv",
        "https://cdn.example.com/video.mp4",
        "--force-media-title=Episode 1",
        "--fullscreen",
        "--keep-open",
    ]


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


def test_page_includes_favicon_link():
    assert b'<link rel="icon" href="/favicon.ico?v=1" sizes="any">' in page("Test", "")


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


def test_csrf_check_requires_session_token():
    handler = object.__new__(WebHandler)

    assert handler.valid_csrf({"csrf_token": [CSRF_TOKEN]})
    assert not handler.valid_csrf({"csrf_token": ["wrong"]})
    assert not handler.valid_csrf({})
