from datetime import date

from aw_web.anime import Anime
from aw_web.web.services import (
    SeasonalAnime,
    adjacent_season,
    best_seasonal_match,
    current_season,
    seasonal_label,
)


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
        "aw_web.web.services.find_seasonal_matches",
        lambda provider_name, seasonal: [anime],
    )

    match, candidates = best_seasonal_match("animeunity", seasonal)

    assert match == anime
    assert candidates == [anime]
