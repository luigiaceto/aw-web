from unittest.mock import MagicMock

import pytest

from aw_web.anime import Anime
from aw_web.services.playback import validate_media_url
from aw_web.services.streams import STREAM_TTL_SECONDS, resolve_episode_url, resolve_episode_urls, stream_context, stream_token
from aw_web.web.components import page
from aw_web.web.server import (
    ALLOWED_ORIGINS,
    WebHandler,
    favicon_bytes,
    should_refresh_stream_url,
)
from aw_web.web.state import CSRF_TOKEN, STREAMS
from aw_web.web.views import render_anime


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


def test_stream_tokens_expire(monkeypatch):
    STREAMS.clear()
    anime = Anime("Example", "provider-ref")
    anime.update_episodes({"1": "episode-ref"})

    monkeypatch.setattr("aw_web.services.streams.time.time", lambda: 1000.0)
    token = stream_token("animeunity", anime, "1")

    monkeypatch.setattr("aw_web.services.streams.time.time", lambda: 1001.0 + STREAM_TTL_SECONDS)
    with pytest.raises(RuntimeError):
        stream_context(token)


def test_stream_resolver_caches_multiple_provider_urls(monkeypatch):
    STREAMS.clear()
    anime = Anime("Example", "provider-ref")
    anime.update_episodes({"1": "episode-ref"})
    token = stream_token("animeunity", anime, "1")
    provider = MagicMock()
    provider.Client.headers = {"User-Agent": "test"}
    provider.episode_links.return_value = [
        "https://cdn.example.com/server1.mp4",
        "https://cdn.example.com/server2.mp4",
    ]

    monkeypatch.setattr("aw_web.services.streams.get_provider", lambda provider_name: provider)

    urls, headers = resolve_episode_urls(token)

    assert urls == [
        "https://cdn.example.com/server1.mp4",
        "https://cdn.example.com/server2.mp4",
    ]
    assert headers == {"User-Agent": "test"}
    assert STREAMS[token]["urls"] == urls
    assert resolve_episode_url(token)[0] == "https://cdn.example.com/server1.mp4"

    STREAMS[token]["url"] = "https://cdn.example.com/server2.mp4"
    reordered_urls, _ = resolve_episode_urls(token)
    assert reordered_urls == [
        "https://cdn.example.com/server2.mp4",
        "https://cdn.example.com/server1.mp4",
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


def test_page_includes_favicon_link():
    assert b'<link rel="icon" href="/favicon.ico?v=1" sizes="any">' in page("Test", "")


def test_favicon_is_packaged():
    assert favicon_bytes()


def test_post_origin_check_allows_only_local_origins():
    handler = object.__new__(WebHandler)

    handler.headers = {}
    assert handler.same_origin()

    handler.headers = {"Origin": next(iter(ALLOWED_ORIGINS))}
    assert handler.same_origin()

    handler.headers = {"Origin": "https://example.com"}
    assert not handler.same_origin()


def test_csrf_check_requires_session_token():
    handler = object.__new__(WebHandler)

    assert handler.valid_csrf({"csrf_token": [CSRF_TOKEN]})
    assert not handler.valid_csrf({"csrf_token": ["wrong"]})
    assert not handler.valid_csrf({})


@pytest.mark.parametrize("status_code", [403, 404, 410, 416, 502, 503, 504])
def test_stream_proxy_refreshes_expired_or_invalid_urls(status_code):
    assert should_refresh_stream_url(status_code, "video/mp4")


@pytest.mark.parametrize(
    "content_type",
    [
        "video/mp4",
        "video/webm; charset=binary",
        "application/octet-stream",
        "application/vnd.apple.mpegurl",
        "",
        None,
    ],
)
def test_stream_proxy_keeps_video_like_responses(content_type):
    assert not should_refresh_stream_url(200, content_type)


@pytest.mark.parametrize(
    "content_type",
    [
        "text/html; charset=utf-8",
        "application/json",
        "text/plain",
    ],
)
def test_stream_proxy_refreshes_non_video_success_responses(content_type):
    assert should_refresh_stream_url(200, content_type)
