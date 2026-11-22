"""Test dell'abbinamento tra un anime AniList e i risultati di AnimeUnity."""

from aw_web.anime import Anime
from aw_web.matching import best_seasonal_match
from tests.helpers import seasonal


def test_seasonal_match_keeps_the_sub_and_drops_its_dub(monkeypatch):
    sub = Anime("Example Anime", "10")
    dub = Anime("Example Anime (ITA)", "10-ita")

    class FakeProvider:
        def search(self, title):
            return [sub, dub, Anime("Other Anime", "11")]

    monkeypatch.setattr("aw_web.matching.PROVIDER", FakeProvider())

    match, candidates = best_seasonal_match(seasonal(title="Example Anime"))

    assert match is sub
    assert dub not in candidates


def test_seasonal_match_asks_when_two_anime_are_equally_close(monkeypatch):
    second, third = Anime("Example Anime 2", "20"), Anime("Example Anime 3", "30")

    class FakeProvider:
        def search(self, title):
            return [second, third]

    monkeypatch.setattr("aw_web.matching.PROVIDER", FakeProvider())

    match, candidates = best_seasonal_match(seasonal(title="Example Anime"))

    assert match is None
    assert candidates == [second, third]


def test_seasonal_match_tries_numbered_title_variant(monkeypatch):
    anime = Anime("Re:ZERO -Starting Life in Another World- 4", "provider-ref")
    queries = []

    class FakeProvider:
        def search(self, title):
            queries.append(title)
            return [anime] if title == "Re:ZERO -Starting Life in Another World- 4" else []

    monkeypatch.setattr("aw_web.matching.PROVIDER", FakeProvider())

    match, candidates = best_seasonal_match(seasonal(title="Re:ZERO -Starting Life in Another World- Season 4"))

    assert "Re:ZERO -Starting Life in Another World- 4" in queries
    assert match == anime
    assert candidates == [anime]
