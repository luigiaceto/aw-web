"""Test delle pagine Popolari e Top 100."""

import pytest

from aw_web.anime import Anime
from aw_web.web import views
from tests.helpers import seasonal


@pytest.mark.parametrize(
    ("source", "title"),
    [("popolari", "Popolari"), ("top-100", "Top 100")],
)
def test_ranking_page_lists_anime_that_open_on_animeunity(monkeypatch, source, title):
    monkeypatch.setattr(views, "ranked_anime", lambda slug: [seasonal(anilist_id=456, average_score=88)])

    html = views.render_anilist_ranking(source).decode()

    assert f"<h1>{title}</h1>" in html
    assert f"/anilist/apri?source={source}&amp;anilist_id=456" in html
    assert "Voto AniList 88%" in html


def test_anilist_open_redirects_to_provider_match(monkeypatch):
    matched = Anime("Provider Example", "provider-ref")
    monkeypatch.setattr(views, "ranked_by_id", lambda source, anilist_id: seasonal(anilist_id=456))
    monkeypatch.setattr(views, "best_seasonal_match", lambda item: (matched, [matched]))

    payload = views.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]})

    assert payload == b"REDIRECT:/anime?name=Provider+Example&ref=provider-ref"


def test_anilist_open_shows_candidates_when_the_match_is_not_sure(monkeypatch):
    candidate = Anime("Maybe This One", "candidate-ref")
    monkeypatch.setattr(views, "ranked_by_id", lambda source, anilist_id: seasonal(anilist_id=456))
    monkeypatch.setattr(views, "best_seasonal_match", lambda item: (None, [candidate]))

    html = views.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]}).decode()

    assert "Risultati possibili" in html
    assert "Torna a Popolari" in html
    assert "/anime?name=Maybe+This+One" in html
