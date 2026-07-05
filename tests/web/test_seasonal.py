from datetime import date

from aw_web.anime import Anime
from aw_web.services.anilist import (
    SeasonalAnime,
    adjacent_season,
    current_season,
    get_cover,
    ranked_anime,
    seasonal_anime,
    seasonal_label,
)
from aw_web.services.matching import best_seasonal_match
from aw_web.web.db import WebDatabase


def test_current_season_from_date():
    assert current_season(date(2026, 1, 1)) == (2026, "WINTER")
    assert current_season(date(2026, 4, 1)) == (2026, "SPRING")
    assert current_season(date(2026, 7, 1)) == (2026, "SUMMER")
    assert current_season(date(2026, 10, 1)) == (2026, "FALL")


def test_adjacent_season_crosses_year_boundaries():
    assert adjacent_season(2026, "WINTER", -1) == (2025, "FALL")
    assert adjacent_season(2026, "FALL", 1) == (2027, "WINTER")


def test_seasonal_label_is_italian():
    assert seasonal_label("SPRING") == "Primavera"


def test_seasonal_anime_fetches_all_anilist_pages(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def media_item(anilist_id, title, *, is_adult=False, genres=None):
        return {
            "id": anilist_id,
            "title": {"english": title, "romaji": "", "native": ""},
            "synonyms": [],
            "coverImage": {},
            "bannerImage": "",
            "status": "RELEASING",
            "episodes": 12,
            "genres": genres or [],
            "averageScore": 0,
            "isAdult": is_adult,
        }

    def fake_post(url, *, json, timeout):
        page = json["variables"]["page"]
        calls.append(page)
        return FakeResponse(
            {
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": page == 1},
                        "media": [
                            media_item(page, f"Anime {page}"),
                            media_item(page + 10, f"Adult {page}", is_adult=True),
                            media_item(page + 20, f"Hentai {page}", genres=["Hentai"]),
                        ],
                    }
                }
            }
        )

    seasonal_anime.cache_clear()
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    items = seasonal_anime(2026, "SPRING")

    assert calls == [1, 2]
    assert [item.anilist_id for item in items] == [1, 2]
    seasonal_anime.cache_clear()


def test_ranked_anime_uses_expected_anilist_sort(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": False},
                        "media": [
                            {
                                "id": 123,
                                "title": {"english": "Ranked Anime", "romaji": "", "native": ""},
                                "synonyms": [],
                                "coverImage": {},
                                "bannerImage": "",
                                "status": "FINISHED",
                                "episodes": 12,
                                "genres": ["Action"],
                                "averageScore": 90,
                                "isAdult": False,
                            }
                        ],
                    }
                }
            }

    def fake_post(url, *, json, timeout):
        calls.append(json["variables"])
        return FakeResponse()

    ranked_anime.cache_clear()
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    popular = ranked_anime("popolari")
    ranked_anime.cache_clear()
    top = ranked_anime("top-100")

    assert calls[0]["sort"] == ["TRENDING_DESC"]
    assert calls[1]["sort"] == ["SCORE_DESC"]
    assert popular[0].title == "Ranked Anime"
    assert top[0].average_score == 90
    ranked_anime.cache_clear()


def test_get_cover_does_not_cache_http_errors(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")

    class FakeResponse:
        def raise_for_status(self):
            raise RuntimeError("403 Forbidden")

    def fake_post(url, *, json, timeout):
        return FakeResponse()

    monkeypatch.setattr("aw_web.services.anilist.DB", db)
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    cover = get_cover(123, "Blocked Anime")

    assert cover == {"cover_url": "", "banner_url": "", "color": ""}
    assert db.get_cover("anilist:123") is None


def test_get_cover_does_not_cache_missing_cover_image(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "Media": {
                        "id": 123,
                        "title": {"english": "No Cover", "romaji": "", "native": ""},
                        "coverImage": {},
                        "bannerImage": "https://img.example/banner.jpg",
                    }
                }
            }

    def fake_post(url, *, json, timeout):
        return FakeResponse()

    monkeypatch.setattr("aw_web.services.anilist.DB", db)
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    cover = get_cover(123, "No Cover")

    assert cover == {
        "cover_url": "",
        "banner_url": "https://img.example/banner.jpg",
        "color": "",
    }
    assert db.get_cover("anilist:123") is None


def test_get_cover_caches_valid_anilist_response(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "Media": {
                        "id": 123,
                        "title": {"english": "Covered", "romaji": "", "native": ""},
                        "coverImage": {
                            "large": "https://img.example/large.jpg",
                            "extraLarge": "https://img.example/extra.jpg",
                            "color": "#abcdef",
                        },
                        "bannerImage": "https://img.example/banner.jpg",
                    }
                }
            }

    def fake_post(url, *, json, timeout):
        return FakeResponse()

    monkeypatch.setattr("aw_web.services.anilist.DB", db)
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    cover = get_cover(123, "Covered")
    cached = db.get_cover("anilist:123")

    assert cover == {
        "cover_url": "https://img.example/extra.jpg",
        "banner_url": "https://img.example/banner.jpg",
        "color": "#abcdef",
    }
    assert cached is not None
    assert cached["cover_url"] == "https://img.example/extra.jpg"


def test_get_cover_uses_valid_cache_without_http(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    db.set_cover(
        cache_key="anilist:123",
        anilist_id=123,
        title="Cached",
        cover_url="https://img.example/cached.jpg",
        banner_url="https://img.example/cached-banner.jpg",
        color="#123456",
    )

    def fake_post(url, *, json, timeout):
        raise AssertionError("AniList should not be called for cached covers")

    monkeypatch.setattr("aw_web.services.anilist.DB", db)
    monkeypatch.setattr("aw_web.services.anilist.httpx.post", fake_post)

    cover = get_cover(123, "Cached")

    assert cover == {
        "cover_url": "https://img.example/cached.jpg",
        "banner_url": "https://img.example/cached-banner.jpg",
        "color": "#123456",
    }


def test_best_seasonal_match_uses_anilist_id(monkeypatch):
    seasonal = SeasonalAnime(
        anilist_id=123,
        title="Example Anime",
        title_romaji="Example Anime",
        title_english="",
        title_native="",
        synonyms=(),
        cover_url="",
        banner_url="",
        status="RELEASING",
        episodes=12,
        genres=(),
        average_score=80,
    )
    anime = Anime("Different Provider Title", "provider-ref")
    anime.anilist_id = 123

    monkeypatch.setattr(
        "aw_web.services.matching.find_seasonal_matches",
        lambda provider_name, seasonal: [anime],
    )

    match, candidates = best_seasonal_match("animeunity", seasonal)

    assert match == anime
    assert candidates == [anime]


def test_seasonal_match_tries_numbered_title_variant(monkeypatch):
    seasonal = SeasonalAnime(
        anilist_id=182300,
        title="Re:ZERO -Starting Life in Another World- Season 4",
        title_romaji="",
        title_english="",
        title_native="",
        synonyms=(),
        cover_url="",
        banner_url="",
        status="RELEASING",
        episodes=0,
        genres=(),
        average_score=0,
    )
    anime = Anime("Re:ZERO -Starting Life in Another World- 4", "provider-ref")
    queries = []

    class FakeProvider:
        def search(self, title):
            queries.append(title)
            if title == "Re:ZERO -Starting Life in Another World- 4":
                return [anime]
            return []

    monkeypatch.setattr("aw_web.services.matching.get_provider", lambda provider_name: FakeProvider())

    match, candidates = best_seasonal_match("animeunity", seasonal)

    assert "Re:ZERO -Starting Life in Another World- 4" in queries
    assert match == anime
    assert candidates == [anime]
