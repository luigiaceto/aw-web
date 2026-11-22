"""Test delle pagine: home, scheda anime e classifiche AniList."""

import json
import threading
import time
from unittest.mock import MagicMock

import pytest

from aw_web.anime import Anime, anime_to_json
from aw_web.db import WebDatabase
from aw_web.web import pages
from aw_web.web.pages import render_anime
from tests.helpers import saved_row, seasonal


class FakeProvider:
    def latest(self):
        return []


class FakeDB:
    def __init__(self, watch_items, favorite_items=()):
        self._watch_items = list(watch_items)
        self._favorite_items = list(favorite_items)

    def items(self, table):
        return {"watchlist": self._watch_items, "favorites": self._favorite_items}[table]


def _watch_item(item_id: int, name: str, *, cover_url: str = "", banner_url: str = ""):
    anime = Anime(name, f"ref-{item_id}", curr_ep="1", last_ep="12")
    anime.cover_url, anime.banner_url = cover_url, banner_url
    return saved_row(anime, "1")


def test_home_uses_all_watchlist_images_for_hero_slideshow(monkeypatch):
    watch_items = [
        _watch_item(1, "First", banner_url="https://img.example/first.jpg"),
        _watch_item(2, "Second", cover_url="https://img.example/second.jpg"),
        _watch_item(3, "No Image"),
    ]
    favorite_items = [
        _watch_item(4, "Favorite", banner_url="https://img.example/favorite.jpg"),
    ]
    monkeypatch.setattr(pages, "DB", FakeDB(watch_items, favorite_items))
    monkeypatch.setattr(pages, "PROVIDER", FakeProvider())
    monkeypatch.setattr(pages, "refresh_watchlist_availability", lambda *args, **kwargs: None)

    html = pages.render_home().decode()

    assert html.count('class="hero-slide"') == 2
    assert "https://img.example/first.jpg" in html
    assert "https://img.example/second.jpg" in html
    assert "https://img.example/favorite.jpg" not in html
    assert "--hero-image" not in html


def test_home_static_hero_slide_when_watchlist_has_one_image(monkeypatch):
    monkeypatch.setattr(
        pages,
        "DB",
        FakeDB([_watch_item(1, "Only", banner_url="https://img.example/only.jpg")]),
    )
    monkeypatch.setattr(pages, "PROVIDER", FakeProvider())
    monkeypatch.setattr(pages, "refresh_watchlist_availability", lambda *args, **kwargs: None)

    html = pages.render_home().decode()

    assert 'class="hero-slideshow is-static"' in html
    assert 'class="hero-slide"' in html
    assert "@keyframes heroSlideshow" not in html


def test_start_watchlist_refresh_skips_while_a_refresh_is_running():
    pages._WATCHLIST_REFRESH_RUNNING = False
    started = threading.Event()
    release = threading.Event()
    calls = []

    def task():
        calls.append(1)
        started.set()
        release.wait(5)

    pages.start_watchlist_refresh(task)
    assert started.wait(5)
    pages.start_watchlist_refresh(task)  # già in corso: ignorata
    release.set()

    deadline = time.monotonic() + 5
    while pages._WATCHLIST_REFRESH_RUNNING and time.monotonic() < deadline:
        time.sleep(0.01)

    assert calls == [1]
    assert not pages._WATCHLIST_REFRESH_RUNNING


def test_watchlist_cards_payload_reports_refresh_state(monkeypatch):
    monkeypatch.setattr(pages, "DB", FakeDB([_watch_item(1, "First")]))
    monkeypatch.setattr(pages, "_WATCHLIST_REFRESH_RUNNING", True)

    payload = json.loads(pages.watchlist_cards_payload())

    assert payload["refreshing"] is True
    assert "First" in payload["html"]

    monkeypatch.setattr(pages, "_WATCHLIST_REFRESH_RUNNING", False)
    assert json.loads(pages.watchlist_cards_payload())["refreshing"] is False


def test_watchlist_cards_payload_shows_the_refreshed_episode(monkeypatch):
    anime = Anime("First", "ref-1", curr_ep="12", last_ep="12")
    item = saved_row(anime, "12")
    monkeypatch.setattr(pages, "DB", FakeDB([item]))

    assert "Nuovo episodio" not in json.loads(pages.watchlist_cards_payload())["html"]

    refreshed = Anime("First", "ref-1", curr_ep="12", last_ep="13")
    item["anime_json"] = anime_to_json(refreshed)

    assert "Nuovo episodio" in json.loads(pages.watchlist_cards_payload())["html"]


def _provider(monkeypatch, episodes: dict[str, str]) -> MagicMock:
    provider = MagicMock()
    provider.info_anime.return_value = None
    provider.episodes.side_effect = lambda anime: anime.update_episodes(episodes)
    monkeypatch.setattr("aw_web.web.pages.PROVIDER", provider)
    return provider


def test_anime_page_embeds_the_anime_once_for_all_episodes(monkeypatch):
    _provider(monkeypatch, {str(number): f"ref-{number}" for number in range(1, 301)})

    body = render_anime({"name": ["Example"], "ref": ["123"]})

    # un form "Guarda" condiviso + i due toggle watchlist/preferiti, qualunque sia il numero di episodi
    assert body.count(b'name="anime"') == 3
    assert body.count(b'action="/play"') == 1
    assert body.count(b'form="play-form" name="episode"') == 300
    assert len(body) < 500_000


def test_anime_page_saved_does_not_refetch_episodes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Saved Anime", "123", curr_ep="1", last_ep="12")
    anime.update_episodes({"1": "episode-ref"})
    db.upsert("watchlist", anime.to_dict(), "1")
    provider = _provider(monkeypatch, {})
    monkeypatch.setattr("aw_web.web.pages.DB", db)

    body = render_anime({"saved": ["1"], "ref": ["123"]})

    provider.episodes.assert_not_called()
    assert b"Ultimo visto: 1" in body


@pytest.mark.parametrize(
    ("source", "title"),
    [("popolari", "Popolari"), ("top-100", "Top 100")],
)
def test_ranking_page_lists_anime_that_open_on_animeunity(monkeypatch, source, title):
    monkeypatch.setattr(pages, "ranked_anime", lambda slug: [seasonal(anilist_id=456, average_score=88)])

    html = pages.render_anilist_ranking(source).decode()

    assert f"<h1>{title}</h1>" in html
    assert f"/anilist/apri?source={source}&amp;anilist_id=456" in html
    assert "Voto AniList 88%" in html


def test_anilist_open_redirects_to_provider_match(monkeypatch):
    matched = Anime("Provider Example", "provider-ref")
    monkeypatch.setattr(pages, "ranked_by_id", lambda source, anilist_id: seasonal(anilist_id=456))
    monkeypatch.setattr(pages, "best_seasonal_match", lambda item: (matched, [matched]))

    payload = pages.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]})

    assert payload == b"REDIRECT:/anime?name=Provider+Example&ref=provider-ref"


def test_anilist_open_shows_candidates_when_the_match_is_not_sure(monkeypatch):
    candidate = Anime("Maybe This One", "candidate-ref")
    monkeypatch.setattr(pages, "ranked_by_id", lambda source, anilist_id: seasonal(anilist_id=456))
    monkeypatch.setattr(pages, "best_seasonal_match", lambda item: (None, [candidate]))

    html = pages.render_anilist_open({"source": ["popolari"], "anilist_id": ["456"]}).decode()

    assert "Risultati possibili" in html
    assert "Torna a Popolari" in html
    assert "/anime?name=Maybe+This+One" in html
