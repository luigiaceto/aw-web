from aw_web.anime import Anime
from aw_web.services.anilist import SeasonalAnime
from aw_web.web import views


def _ranked_item() -> SeasonalAnime:
    return SeasonalAnime(
        anilist_id=456,
        title="Ranked Example",
        title_romaji="Ranked Example",
        title_english="",
        title_native="",
        synonyms=(),
        cover_url="",
        banner_url="",
        status="FINISHED",
        episodes=12,
        genres=("Action",),
        average_score=88,
    )


def test_render_top_100_page_uses_score_ranking(monkeypatch):
    monkeypatch.setattr(views, "ranked_anime", lambda source: [_ranked_item()])

    html = views.render_anilist_ranking("top-100").decode()

    assert "<h1>Top 100</h1>" in html
    assert "I cento anime con il punteggio piu alto su AniList." in html
    assert "/anilist/apri?source=top-100&amp;anilist_id=456" in html
    assert "Voto AniList 88%" in html


def test_render_popular_page_uses_trending_copy(monkeypatch):
    monkeypatch.setattr(views, "ranked_anime", lambda source: [_ranked_item()])

    html = views.render_anilist_ranking("popolari").decode()

    assert "<h1>Popolari</h1>" in html
    assert "Gli anime che stanno andando forte ora secondo AniList." in html
    assert "/anilist/apri?source=popolari&amp;anilist_id=456" in html


def test_anilist_open_redirects_to_provider_match(monkeypatch):
    matched = Anime("Provider Example", "provider-ref", curr_ep="0", last_ep="12")
    matched.anilist_id = 456
    monkeypatch.setattr(views, "ranked_by_id", lambda source, anilist_id: _ranked_item())
    monkeypatch.setattr(views, "best_seasonal_match", lambda provider_name, item: (matched, [matched]))

    payload = views.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]})

    assert payload.decode().startswith("REDIRECT:/anime?provider=animeunity")
    assert "anilist_id=456" in payload.decode()


def test_anilist_open_shows_candidates_when_the_match_is_not_sure(monkeypatch):
    candidate = Anime("Maybe This One", "candidate-ref", curr_ep="0", last_ep="12")
    monkeypatch.setattr(views, "ranked_by_id", lambda source, anilist_id: _ranked_item())
    monkeypatch.setattr(views, "best_seasonal_match", lambda provider_name, item: (None, [candidate]))
    monkeypatch.setattr(
        "aw_web.web.components.get_cover",
        lambda anilist_id, title, allow_title_lookup=False: {"cover_url": "", "banner_url": "", "color": ""},
    )

    html = views.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]}).decode()

    assert "Risultati possibili" in html
    assert "Torna a Popolari" in html
    assert "/anime?provider=animeunity" in html
    assert "Maybe This One" in html
