"""Test delle card e della scelta dell'episodio da riprendere."""

from urllib.parse import parse_qs, urlparse

import pytest

from aw_web.anime import Anime, episode_overview
from aw_web.web.components import anilist_card, anime_url, card, favorite_card, seasonal_card, watch_card
from tests.helpers import saved_row, seasonal


def _anime(episodes: list[str], last_ep: str, name: str = "Example") -> Anime:
    anime = Anime(name, "anime-ref", last_ep=last_ep)
    anime.update_episodes({num: f"video-{num}" for num in episodes})
    return anime


def _latest(name: str, episode: str) -> Anime:
    anime = Anime(name, "anime-ref", curr_ep=episode)
    anime.update_episodes({episode: f"video-{episode}"})
    return anime


@pytest.mark.parametrize(
    ("episodes", "current", "latest", "expected"),
    [
        pytest.param(["1", "2", "3"], "0", [], ("3", "1"), id="mai-visto-parte-dal-primo"),
        pytest.param(["1", "2", "3"], "1", [], ("3", "2"), id="riprende-dal-successivo"),
        pytest.param(["1", "12"], "12", [], ("12", "12"), id="ultimo-visto-resta-sull-ultimo"),
        pytest.param(["10"], "10", [_latest("Example", "11")], ("11", "11"), id="uscito-un-nuovo-episodio"),
        pytest.param(["10"], "10", [_latest("Other", "11")], ("10", "10"), id="uscite-di-altri-anime-ignorate"),
        pytest.param(["1-12"], "0", [], ("1-12", "1-12"), id="episodi-a-blocchi"),
    ],
)
def test_episode_overview(episodes, current, latest, expected):
    anime = _anime(episodes, last_ep=episodes[-1])

    assert episode_overview(anime, current, latest) == expected


def test_watch_card_shows_the_new_episode_and_resumes_from_it():
    saved = _anime(["10"], last_ep="10")

    html = watch_card(saved_row(saved, "10"), [_latest("Example", "11")])

    assert "Nuovo episodio" in html
    assert "Ep. 10 / 11" in html
    assert 'name="episode" value="11"' in html
    assert "Riprendi" in html


def test_watch_card_keeps_play_and_remove_forms():
    saved = _anime(["1", "2"], last_ep="2")
    saved.cover_url = "https://img.example/cover.jpg"

    html = watch_card(saved_row(saved, "0"), [])

    assert 'href="/anime?saved=1&amp;name=Example&amp;ref=anime-ref"' in html
    assert 'name="episode" value="1"' in html
    assert "Inizia" in html
    assert 'action="/watchlist/remove"' in html
    assert 'name="ref" value="anime-ref"' in html
    assert 'src="https://img.example/cover.jpg"' in html


def test_favorite_card_keeps_remove_form_and_detail_link():
    anime = Anime("Favorite Anime", "favorite-ref", last_ep="12")

    html = favorite_card(saved_row(anime))

    assert 'href="/anime?name=Favorite+Anime&amp;ref=favorite-ref"' in html
    assert 'action="/favorites/remove"' in html
    assert "Ep. 0 / 12" in html


def test_anime_url_round_trips_special_characters():
    anime = Anime("Boku & Friends: Test?", "ref&1")

    params = parse_qs(urlparse(anime_url(anime)).query)

    assert params == {"name": [anime.name], "ref": [anime.ref]}


def test_latest_card_plays_its_episode():
    anime = Anime("Plot Anime", "anime-ref", curr_ep="4", last_ep="12")
    anime.info["Trama"] = "Una descrizione gia disponibile dal provider."
    anime.update_episodes({"4": "episode-4"})

    html = card(anime, "Nuovo")

    assert "Una descrizione gia disponibile dal provider." in html
    assert 'name="episode" value="4"' in html
    assert "Guarda episodio 4" in html


def test_search_card_without_episode_has_no_play_button():
    html = card(Anime("No Plot Anime", "anime-ref"))

    assert "Apri la scheda per maggiori dettagli." in html
    assert 'action="/play"' not in html


def test_card_text_is_escaped_once():
    item = seasonal(title="Tom & Jerry", genres=("Slice & Life",), episodes=0)

    html = anilist_card(item, "popolari", "Popolari")

    assert "Tom &amp; Jerry" in html
    assert "Slice &amp; Life" in html
    assert "&amp;amp;" not in html


@pytest.mark.parametrize(
    ("html", "expected_url", "expected_meta"),
    [
        pytest.param(
            seasonal_card(seasonal(genres=("Action", "Fantasy"), average_score=83), 2026, "SUMMER"),
            "/stagionali/apri?year=2026&amp;season=SUMMER&amp;anilist_id=123",
            "Action, Fantasy | 12 ep. | Voto AniList 83%",
            id="seasonal-card",
        ),
        pytest.param(
            anilist_card(
                seasonal(anilist_id=321, episodes=24, genres=("Drama",), average_score=91), "popolari", "Popolari"
            ),
            "/anilist/apri?source=popolari&amp;anilist_id=321",
            "Drama | 24 ep. | Voto AniList 91%",
            id="anilist-card",
        ),
    ],
)
def test_anilist_cards_point_to_open_url(html, expected_url, expected_meta):
    assert expected_url in html
    assert expected_meta in html
