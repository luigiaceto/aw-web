import pytest
from urllib.parse import parse_qs, urlparse

from aw_web.anime import Anime
from aw_web.services.anilist import SeasonalAnime
from aw_web.web.components import anilist_card, card, favorite_card, page, seasonal_card, watch_card
from aw_web.web.utils import anime_to_json, anime_url, episode_overview


def test_watch_card_uses_latest_episode_for_display():
    saved_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="10", last_ep="10")
    saved_anime.update_episodes({"10": "old-episode"})
    latest_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="11", last_ep="11")
    latest_anime.update_episodes({"11": "new-episode"})
    item = {
        "id": 1,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "10",
        "last_episode": "10",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [latest_anime])

    last_episode, playable_episode = episode_overview(item, [latest_anime])
    assert last_episode == "11"
    assert playable_episode == "11"
    assert "Nuovo episodio" in html
    assert "Ep. 10 / 11" in html
    assert "Sei arrivato all" not in html
    assert 'name="episode" value="11"' in html


def test_watch_card_resume_keeps_current_episode_when_no_next_exists():
    saved_anime = Anime("Example", "anime-ref", curr_ep="12", last_ep="12")
    saved_anime.update_episodes({"1": "episode-1", "12": "episode-12"})
    item = {
        "id": 1,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "12",
        "last_episode": "12",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [])

    assert episode_overview(item, [])[1] == "12"
    assert 'name="episode" value="12"' in html


def test_watch_card_keeps_play_and_remove_forms():
    saved_anime = Anime("Example", "anime-ref", curr_ep="1", last_ep="2")
    saved_anime.update_episodes({"1": "episode-1", "2": "episode-2"})
    item = {
        "id": 7,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "1",
        "last_episode": "2",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [])

    assert 'class="card-detail-link" href="/anime?saved=1&amp;provider=animeunity' in html
    assert 'action="/play"' in html
    assert 'name="episode" value="2"' in html
    assert 'action="/watchlist/remove"' in html


def test_anime_url_round_trips_special_characters():
    anime = Anime("Boku & Friends: Test?", "ref&1", curr_ep="2", last_ep="5")

    params = parse_qs(urlparse(anime_url("animeunity", anime)).query)

    assert params["name"] == [anime.name]
    assert params["ref"] == [anime.ref]


def test_watch_card_has_decorative_hover_backdrop():
    saved_anime = Anime("Backdrop Example", "anime-ref", curr_ep="1", last_ep="2")
    item = {
        "id": 7,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "1",
        "last_episode": "2",
        "cover_url": "https://img.example/backdrop.jpg",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [])

    assert '<div class="card-backdrop" aria-hidden="true">' in html
    assert 'src="https://img.example/backdrop.jpg"' in html
    assert 'aria-hidden="true" alt="Copertina Backdrop Example"' in html


def test_catalog_card_uses_existing_description(monkeypatch):
    anime = Anime("Plot Anime", "anime-ref", curr_ep="4", last_ep="12")
    anime.info["Trama"] = "Una descrizione gia disponibile dal provider."
    anime.update_episodes({"4": "episode-4"})
    monkeypatch.setattr(
        "aw_web.web.components.get_cover",
        lambda anilist_id, title, allow_title_lookup=False: {"cover_url": "", "banner_url": "", "color": ""},
    )

    html = card(anime, "animeunity", "Nuovo")

    assert "Una descrizione gia disponibile dal provider." in html
    assert 'action="/play"' in html
    assert 'name="episode" value="4"' in html
    assert "Guarda episodio 4" in html


def test_catalog_card_without_description_uses_neutral_fallback(monkeypatch):
    anime = Anime("No Plot Anime", "anime-ref")
    monkeypatch.setattr(
        "aw_web.web.components.get_cover",
        lambda anilist_id, title, allow_title_lookup=False: {"cover_url": "", "banner_url": "", "color": ""},
    )

    html = card(anime, "animeunity")

    assert "Apri la scheda per maggiori dettagli." in html
    assert 'action="/play"' not in html


def test_favorite_card_keeps_remove_form_and_detail_link():
    anime = Anime("Favorite Anime", "favorite-ref", curr_ep="0", last_ep="12")
    item = {
        "id": 9,
        "provider": "animeunity",
        "name": anime.name,
        "ref": anime.ref,
        "current_episode": "0",
        "last_episode": "12",
        "status": "In corso",
        "cover_url": "",
        "anime_json": anime_to_json(anime),
    }

    html = favorite_card(item)

    assert "/anime?provider=animeunity" in html
    assert 'action="/favorites/remove"' in html


@pytest.mark.parametrize(
    "html, expected_url, expected_meta",
    [
        pytest.param(
            seasonal_card(
                SeasonalAnime(
                    anilist_id=123,
                    title="Seasonal Example",
                    title_romaji="Seasonal Example",
                    title_english="",
                    title_native="",
                    synonyms=(),
                    cover_url="",
                    banner_url="",
                    status="RELEASING",
                    episodes=12,
                    genres=("Action", "Fantasy"),
                    average_score=83,
                ),
                2026,
                "SUMMER",
            ),
            "/stagionali/apri?year=2026&amp;season=SUMMER&amp;anilist_id=123",
            "Action, Fantasy | 12 ep. | Voto AniList 83%",
            id="seasonal-card",
        ),
        pytest.param(
            anilist_card(
                SeasonalAnime(
                    anilist_id=321,
                    title="Trending Example",
                    title_romaji="Trending Example",
                    title_english="",
                    title_native="",
                    synonyms=(),
                    cover_url="",
                    banner_url="",
                    status="RELEASING",
                    episodes=24,
                    genres=("Drama",),
                    average_score=91,
                ),
                "popolari",
                "Popolari",
            ),
            "/anilist/apri?source=popolari&amp;anilist_id=321",
            "Drama | 24 ep. | Voto AniList 91%",
            id="anilist-card",
        ),
    ],
)
def test_anilist_catalog_cards_point_to_open_url(html, expected_url, expected_meta):
    assert expected_url in html
    assert expected_meta in html


def test_anilist_card_includes_badge_label():
    item = SeasonalAnime(
        anilist_id=321,
        title="Trending Example",
        title_romaji="Trending Example",
        title_english="",
        title_native="",
        synonyms=(),
        cover_url="",
        banner_url="",
        status="RELEASING",
        episodes=24,
        genres=("Drama",),
        average_score=91,
    )

    html = anilist_card(item, "popolari", "Popolari")

    assert "Popolari" in html


def test_navbar_includes_requested_catalog_links():
    html = page("Test", "").decode()

    assert '<a class="nav-link" href="/">Home</a>' in html
    assert '<a class="nav-link" href="/stagionali">Stagionali</a>' in html
    assert '<a class="nav-link" href="/popolari">Popolari</a>' in html
    assert '<a class="nav-link" href="/top-100">Top 100</a>' in html
