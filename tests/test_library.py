"""Test delle scritture dati utente: watchlist, preferiti e progressi."""

from aw_web import library
from aw_web.anime import Anime
from aw_web.db import WebDatabase, saved_anime


def _anime() -> Anime:
    anime = Anime("Example", "anime-ref", curr_ep="1", last_ep="12")
    anime.update_episodes({"1": "episode-1", "2": "episode-2"})
    anime.cover_url = "https://img.example/cover.jpg"
    return anime


def test_toggle_watchlist_adds_then_removes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(library, "DB", db)
    anime = _anime()

    library.toggle("watchlist", anime)
    item = db.find("watchlist", anime.ref)
    assert item is not None
    assert saved_anime(item).cover_url == "https://img.example/cover.jpg"

    library.toggle("watchlist", anime)
    assert db.find("watchlist", anime.ref) is None


def test_toggle_watchlist_keeps_history_progress(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(library, "DB", db)
    anime = _anime()
    db.upsert("watch_history", anime.to_dict(), "2")

    library.toggle("watchlist", anime)

    item = db.find("watchlist", anime.ref)
    assert item is not None
    assert item["current_episode"] == "2"


def test_toggle_favorite_adds_then_removes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(library, "DB", db)
    anime = _anime()

    library.toggle("favorites", anime)
    assert db.find("favorites", anime.ref) is not None

    library.toggle("favorites", anime)
    assert db.find("favorites", anime.ref) is None


def test_save_watch_progress_updates_history_watchlist_and_favorites(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(library, "DB", db)
    anime = _anime()
    db.upsert("watchlist", anime.to_dict(), "1")
    db.upsert("favorites", anime.to_dict(), "1")

    library.save_watch_progress(anime, anime.episode("2"))

    history = db.find("watch_history", anime.ref)
    watch_item = db.find("watchlist", anime.ref)
    favorite_item = db.find("favorites", anime.ref)
    assert history is not None
    assert watch_item is not None
    assert favorite_item is not None
    assert history["current_episode"] == "2"
    assert watch_item["current_episode"] == "2"
    assert favorite_item["current_episode"] == "2"
    assert saved_anime(watch_item).cover_url == "https://img.example/cover.jpg"


def test_save_watch_progress_does_not_create_a_watchlist_entry(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    monkeypatch.setattr(library, "DB", db)
    anime = _anime()

    library.save_watch_progress(anime, anime.episode("1"))

    assert db.find("watch_history", anime.ref) is not None
    assert db.find("watchlist", anime.ref) is None
