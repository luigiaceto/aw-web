"""Test delle liste AniList."""

from datetime import date

import httpx

from aw_web import anilist
from aw_web.anilist import adjacent_season, current_season, ranked_anime, seasonal_anime
from tests.helpers import anilist_media


def _fake_anilist(monkeypatch, pages: list[list[dict]]) -> list[dict]:
    """AniList finto: risponde con una pagina per chiamata e registra le variabili ricevute."""
    calls: list[dict] = []

    def fake_post(url, *, json, timeout):
        calls.append(json["variables"])
        page = json["variables"]["page"]
        data = {"Page": {"pageInfo": {"hasNextPage": page < len(pages)}, "media": pages[page - 1]}}
        return httpx.Response(200, json={"data": data}, request=httpx.Request("POST", url))

    anilist._seasonal_anime.cache_clear()
    anilist._ranked_anime.cache_clear()
    monkeypatch.setattr("aw_web.anilist.httpx.post", fake_post)
    return calls


def test_current_season_from_date():
    assert current_season(date(2026, 1, 1)) == (2026, "WINTER")
    assert current_season(date(2026, 4, 1)) == (2026, "SPRING")
    assert current_season(date(2026, 7, 1)) == (2026, "SUMMER")
    assert current_season(date(2026, 10, 1)) == (2026, "FALL")


def test_adjacent_season_crosses_year_boundaries():
    assert adjacent_season(2026, "WINTER", -1) == (2025, "FALL")
    assert adjacent_season(2026, "FALL", 1) == (2027, "WINTER")
    assert adjacent_season(2026, "SPRING", -5) == (2025, "WINTER")


def test_seasonal_anime_reads_every_page_and_hides_adult_titles(monkeypatch):
    calls = _fake_anilist(
        monkeypatch,
        [
            [anilist_media(1, "Anime 1"), anilist_media(11, "Adult", isAdult=True)],
            [anilist_media(2, "Anime 2"), anilist_media(21, "Hentai", genres=["Hentai"])],
        ],
    )

    items = seasonal_anime(2026, "SPRING")

    assert [call["page"] for call in calls] == [1, 2]
    assert [item.anilist_id for item in items] == [1, 2]


def test_ranked_anime_uses_expected_anilist_sort(monkeypatch):
    calls = _fake_anilist(monkeypatch, [[anilist_media(123, "Ranked Anime", averageScore=90)]])

    popular = ranked_anime("popolari")
    top = ranked_anime("top-100")

    assert [call["sort"] for call in calls] == [["TRENDING_DESC"], ["SCORE_DESC"]]
    assert popular[0].title == "Ranked Anime"
    assert top[0].average_score == 90


def test_seasonal_title_variants_handle_both_season_forms():
    expected = ["Foo- 2", "Foo 2", "Foo"]
    assert anilist.seasonal_title_variants("Foo Season 2") == ["Foo Season 2", *expected]
    assert anilist.seasonal_title_variants("Foo 2nd Season") == ["Foo 2nd Season", *expected]
    assert anilist.seasonal_title_variants("Season 2") == ["Season 2"]
