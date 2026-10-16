"""Test delle scritture dati utente: watchlist, preferiti e progressi."""

from aw_web.anime import Anime
from aw_web.services import collections, progress
from aw_web.web.db import WebDatabase


def _anime() -> Anime:
    anime = Anime("Example", "anime-ref", curr_ep="1", last_ep="12")
    anime.update_episodes({"1": "episode-1", "2": "episode-2"})
    return anime


def test_toggle_watchlist_adds_then_removes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(collections, "DB", db)
    anime = _anime()

    collections.toggle_watchlist("animeunity", anime, "https://img.example/cover.jpg", "")
    item = db.find_watch_item("animeunity", anime.ref)
    assert item is not None
    assert item["cover_url"] == "https://img.example/cover.jpg"

    collections.toggle_watchlist("animeunity", anime, "", "")
    assert db.find_watch_item("animeunity", anime.ref) is None


def test_toggle_watchlist_keeps_history_progress(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(collections, "DB", db)
    anime = _anime()
    db.upsert_history_item(
        provider="animeunity", anime_data=anime.to_dict(), current_episode="2"
    )

    collections.toggle_watchlist("animeunity", anime, "", "")

    item = db.find_watch_item("animeunity", anime.ref)
    assert item is not None
    assert item["current_episode"] == "2"


def test_toggle_favorite_adds_then_removes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(collections, "DB", db)
    anime = _anime()

    collections.toggle_favorite("animeunity", anime, "", "")
    assert db.find_favorite_item("animeunity", anime.ref) is not None

    collections.toggle_favorite("animeunity", anime, "", "")
    assert db.find_favorite_item("animeunity", anime.ref) is None


def test_save_watch_progress_updates_history_watchlist_and_favorites(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(progress, "DB", db)
    monkeypatch.setattr(
        progress,
        "get_cover",
        lambda anilist_id, title: {
            "cover_url": "https://img.example/cover.jpg",
            "banner_url": "",
        },
    )
    anime = _anime()
    db.upsert_watch_item(provider="animeunity", anime_data=anime.to_dict(), current_episode="1")
    db.upsert_favorite_item(provider="animeunity", anime_data=anime.to_dict(), current_episode="1")

    progress.save_watch_progress("animeunity", anime, anime.episode("2"))

    history = db.find_history_item("animeunity", anime.ref)
    watch_item = db.find_watch_item("animeunity", anime.ref)
    favorite_item = db.find_favorite_item("animeunity", anime.ref)
    assert history is not None
    assert watch_item is not None
    assert favorite_item is not None
    assert history["current_episode"] == "2"
    assert watch_item["current_episode"] == "2"
    assert favorite_item["current_episode"] == "2"
    assert watch_item["cover_url"] == "https://img.example/cover.jpg"


def test_save_watch_progress_does_not_create_a_watchlist_entry(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(progress, "DB", db)
    monkeypatch.setattr(
        progress, "get_cover", lambda anilist_id, title: {"cover_url": "", "banner_url": ""}
    )
    anime = _anime()

    progress.save_watch_progress("animeunity", anime, anime.episode("1"))

    assert db.find_history_item("animeunity", anime.ref) is not None
    assert db.find_watch_item("animeunity", anime.ref) is None
