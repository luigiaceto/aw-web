from unittest.mock import MagicMock

import pytest
from httpx import HTTPError

from aw_web.anime import Anime
from aw_web.providers.animeworld import Animeworld
from aw_web.web.server import ALLOWED_ORIGINS, WebHandler
from aw_web.web.services import STREAM_TTL_SECONDS, stream_context, stream_token, validate_media_url
from aw_web.web.state import CSRF_TOKEN, STREAMS


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

    monkeypatch.setattr("aw_web.web.services.time.time", lambda: 1000.0)
    token = stream_token("animeunity", anime, "1")

    monkeypatch.setattr("aw_web.web.services.time.time", lambda: 1001.0 + STREAM_TTL_SECONDS)
    with pytest.raises(RuntimeError):
        stream_context(token)


def test_animeworld_rejects_non_animeworld_refs_before_fetch():
    client = MagicMock()
    provider = Animeworld(client=client)

    with pytest.raises(HTTPError):
        provider._get_html("http://127.0.0.1:8765/private")

    client.get.assert_not_called()


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
