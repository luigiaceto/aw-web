from aw_web.anime import Anime
from aw_web.web.db import WebDatabase


def test_episode_progress_table_is_removed(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")

    with db.connect() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'episode_progress'"
        ).fetchone()

    assert row is None


def test_new_watch_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_watch_item(provider="animeunity", anime_data=anime.to_dict())

    item = db.find_watch_item("animeunity", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert item["last_episode"] == "12"


def test_history_does_not_create_watch_item(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_history_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="3",
    )

    assert db.find_history_item("animeunity", "test-ref")["current_episode"] == "3"
    assert db.find_watch_item("animeunity", "test-ref") is None


def test_favorite_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_favorite_item(provider="animeunity", anime_data=anime.to_dict())

    item = db.find_favorite_item("animeunity", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert item["last_episode"] == "12"


def test_recent_cover_cache_entry_is_returned(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")

    db.set_cover(
        cache_key="anilist:1",
        anilist_id=1,
        title="Fresh",
        cover_url="cover",
        banner_url="banner",
        color="#fff",
    )

    item = db.get_cover("anilist:1")

    assert item is not None
    assert item["cover_url"] == "cover"


def test_expired_cover_cache_entry_is_removed(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    db.set_cover(
        cache_key="anilist:2",
        anilist_id=2,
        title="Old",
        cover_url="cover",
        banner_url="banner",
        color="#fff",
    )
    with db.connect() as conn:
        conn.execute(
            "UPDATE cover_cache SET updated_at = datetime('now', '-31 days') WHERE cache_key = ?",
            ("anilist:2",),
        )

    assert db.get_cover("anilist:2") is None
    assert db.get_cover("anilist:2") is None
