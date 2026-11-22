"""Test del provider AnimeUnity con risposte finte nel formato del sito (animeunity.cx)."""

import html
import json

import httpx
import pytest

from aw_web.anime import Anime, AnimeStatus
from aw_web.animeunity import Animeunity, ProviderError, split_ref, stream_urls_from_html, update_link

ANIME = {
    "id": 4851,
    "slug": "frieren",
    "title": "Frieren",
    "type": "tv",
    "season": "fall",
    "year": 2023,
    "total_episodes": 28,
    "episode_runtime": 25,
    "default_status": "completed",
    "score": "8.96",
    "views": 100,
    "images": {"banner": "https://img.example/banner.jpg", "poster": "https://img.example/poster.jpg"},
    "variants": [
        {"language": "ita", "status": "ongoing", "episodes_count": 27},
        {"language": "jpn", "status": "completed", "episodes_count": 28},
    ],
}


def _page(props: dict) -> str:
    return f'<div id="app" data-page="{html.escape(json.dumps({"component": "Anime", "props": props}))}"></div>'


def _provider(handler) -> Animeunity:
    return Animeunity(client=httpx.Client(transport=httpx.MockTransport(handler)))


def _video(video_id: int, language: str, hidden: bool = False) -> dict:
    return {"id": video_id, "language": language, "is_hidden": hidden}


def test_split_ref_reads_language_suffix():
    assert split_ref("4851") == ("4851", "jpn")
    assert split_ref("4851-ita") == ("4851", "ita")


def test_search_lists_the_sub_before_the_dub():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search"
        assert request.url.params["q"] == "frieren"
        return httpx.Response(200, json={"data": [ANIME], "count": 1, "hasMore": False})

    sub, dub = _provider(handler).search("frieren")

    assert (sub.name, sub.ref, sub.last_ep, sub.status) == ("Frieren", "4851", "28", AnimeStatus.FINISHED)
    assert (dub.name, dub.ref, dub.last_ep, dub.status) == ("Frieren (ITA)", "4851-ita", "27", AnimeStatus.ONGOING)
    assert sub.cover_url == "https://img.example/poster.jpg"
    assert sub.banner_url == "https://img.example/banner.jpg"


def test_latest_maps_each_video_to_its_language():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/home/latest-episodes"
        video = {**_video(900, "ita"), "episode": {"number": "7", "anime": ANIME}}
        return httpx.Response(200, json={"data": [video]})

    [anime] = _provider(handler).latest()

    assert (anime.name, anime.ref, anime.curr_ep) == ("Frieren (ITA)", "4851-ita", "7")
    assert anime.episode("7").ref == "900"


def test_episodes_reads_every_block_in_the_anime_language():
    starts = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/anime/4851/episodes"
        start = int(request.url.params["start"])
        starts.append(start)
        blocks = {
            1: [
                {"number": "1", "videos": [_video(11, "jpn"), _video(21, "ita")]},
                {"number": "2", "videos": [_video(12, "jpn", hidden=True), _video(22, "ita")]},
            ],
            3: [{"number": "3", "videos": [_video(13, "jpn")]}],
        }
        return httpx.Response(200, json={"episodes": blocks[start], "start": start, "tab_size": 2, "total": 3})

    provider = _provider(handler)
    sub, dub = Anime("Frieren", "4851"), Anime("Frieren (ITA)", "4851-ita")
    provider.episodes(sub)
    provider.episodes(dub)

    assert {num: sub.episode(num).ref for num in sub.episodes()} == {"1": "11", "3": "13"}
    assert {num: dub.episode(num).ref for num in dub.episodes()} == {"1": "21", "2": "22"}
    assert starts == [1, 3, 1, 3]


def test_episode_link_follows_the_embed_with_referer():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "animeunity.cx":
            assert request.url.path == "/anime/4851-anime/21"
            return httpx.Response(200, text=_page({"embedUrl": "https://vixcloud.example/embed/1?token=t"}))
        assert request.headers["Referer"] == "https://animeunity.cx/"
        return httpx.Response(200, text="window.downloadUrl = 'https:\\/\\/cdn.example\\/video.mp4';")

    anime = Anime("Frieren (ITA)", "4851-ita")
    anime.update_episodes({"1": "21"})

    url = _provider(handler).episode_link(anime, anime.episode("1"))

    assert url == "https://cdn.example/video.mp4"


def test_info_anime_reads_the_anime_page():
    details = {
        **ANIME,
        "anilist_id": 154587,
        "plot": "Trama",
        "studios": [{"name": "MADHOUSE"}],
        "genres": [{"name": "Adventure"}, {"name": "Fantasy"}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/anime/4851-anime"
        return httpx.Response(200, text=_page({"anime": details}))

    anime = Anime("Frieren", "4851")
    _provider(handler).info_anime(anime)

    assert anime.anilist_id == 154587
    assert anime.last_ep == "28"
    assert anime.status == AnimeStatus.FINISHED
    assert anime.info["Stagione"] == "Autunno 2023"
    assert anime.info["Studio"] == "MADHOUSE"
    assert anime.info["Genere"] == "Adventure, Fantasy"
    assert anime.info["Trama"] == "Trama"


def test_extracts_multiple_stream_urls():
    page = """
    <script>
      window.downloadUrl = 'https:\\/\\/cdn.example.com\\/server1.mp4';
      const players = [
        { label: 'server2', file: "https://cdn.example.com/server2.mp4" },
        { label: 'hls', src: "https://cdn.example.com/playlist.m3u8" }
      ];
    </script>
    """

    assert stream_urls_from_html(page) == [
        "https://cdn.example.com/server1.mp4",
        "https://cdn.example.com/server2.mp4",
        "https://cdn.example.com/playlist.m3u8",
    ]


def test_episode_link_reloads_episodes_when_the_video_id_changed():
    # AnimeUnity ha ricaricato l'episodio: il vecchio video 21 non esiste più, ora è il 31
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/anime/4851-anime/21":
            return httpx.Response(404)
        if path == "/api/anime/4851/episodes":
            episodes = [{"number": "1", "videos": [_video(31, "ita")]}]
            return httpx.Response(200, json={"episodes": episodes, "start": 1, "tab_size": 120, "total": 1})
        if path == "/anime/4851-anime/31":
            return httpx.Response(200, text=_page({"embedUrl": "https://vixcloud.example/embed/1"}))
        return httpx.Response(200, text="window.downloadUrl = 'https://cdn.example/new.mp4';")

    anime = Anime("Frieren (ITA)", "4851-ita")
    anime.update_episodes({"1": "21"})

    url = _provider(handler).episode_link(anime, anime.episode("1"))

    assert url == "https://cdn.example/new.mp4"
    assert anime.episode("1").ref == "31"


def test_unexpected_responses_become_provider_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "formato cambiato"})

    with pytest.raises(ProviderError, match="KeyError durante search"):
        _provider(handler).search("frieren")


def test_update_link_uses_only_a_same_name_match():
    anime = Anime("Example", "old-ref")

    class FakeProvider:
        def search(self, name):
            return [Anime("Other Anime", "other-ref"), Anime("Example", "new-ref")]

    result = update_link(FakeProvider(), lambda provider, target: target.ref, anime)

    assert result == "new-ref"
    assert anime.ref == "new-ref"


def test_update_link_raises_when_no_result_has_the_same_name():
    anime = Anime("Example", "old-ref")

    class FakeProvider:
        def search(self, name):
            return [Anime("Other Anime", "other-ref")]

    with pytest.raises(ProviderError, match="nessun risultato"):
        update_link(FakeProvider(), lambda provider, target: None, anime)

    assert anime.ref == "old-ref"
