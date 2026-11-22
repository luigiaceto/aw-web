import sqlite3

import pytest

from aw_web.anime import Anime
from aw_web.db import CREATE_TABLE_STATEMENTS, WebDatabase, prepare_database, saved_anime, validate_database_schema

WATCHLIST_SQL = CREATE_TABLE_STATEMENTS[0]


def _with_watchlist(tmp_path, watchlist_sql):
    """Database valido in cui la tabella watchlist è sostituita da `watchlist_sql`."""
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE watchlist")
        conn.execute(watchlist_sql)
    return db_path


def test_prepare_database_creates_and_validates_new_database(tmp_path):
    db_path = tmp_path / "web.sqlite3"

    result = prepare_database(db_path)

    assert result.created
    assert result.valid
    assert result.errors == ()
    assert db_path.exists()


def test_prepare_database_validates_existing_database(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)

    result = prepare_database(db_path)

    assert not result.created
    assert result.valid
    assert result.errors == ()


def test_validate_database_schema_fails_on_missing_table(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE watch_history")

    errors = validate_database_schema(db_path)

    assert "Tabella mancante: watch_history" in errors


def test_validate_database_schema_fails_on_extra_table(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE unexpected_table (id INTEGER PRIMARY KEY)")

    errors = validate_database_schema(db_path)

    assert "Tabella non prevista: unexpected_table" in errors


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("        episodes_checked_at TEXT NOT NULL DEFAULT '',\n", ""),  # colonna mancante
        ("anime_json TEXT NOT NULL,", "anime_json TEXT NOT NULL, extra TEXT,"),  # colonna in più
        ("ref TEXT NOT NULL PRIMARY KEY", "ref TEXT NOT NULL"),  # chiave mancante
        ("anime_json TEXT NOT NULL", "anime_json TEXT"),  # vincolo diverso
    ],
)
def test_validate_database_schema_fails_on_a_changed_table(tmp_path, old, new):
    assert old in WATCHLIST_SQL
    db_path = _with_watchlist(tmp_path, WATCHLIST_SQL.replace(old, new))

    errors = validate_database_schema(db_path)

    assert errors == ["Tabella diversa dallo schema atteso: watchlist"]


def test_new_watch_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert("watchlist", anime.to_dict())

    item = db.find("watchlist", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert saved_anime(item).last_ep == "12"
    assert item["episodes_checked_at"] == ""


def test_history_does_not_create_watch_item(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert("watch_history", anime.to_dict(), "3")

    history_item = db.find("watch_history", "test-ref")

    assert history_item is not None
    assert history_item["current_episode"] == "3"
    assert db.find("watchlist", "test-ref") is None


def test_favorite_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert("favorites", anime.to_dict())

    item = db.find("favorites", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert saved_anime(item).last_ep == "12"


def test_validate_database_schema_ignores_sqlite_internal_tables(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY AUTOINCREMENT)")  # crea sqlite_sequence
        conn.execute("INSERT INTO counter DEFAULT VALUES")
        conn.execute("DROP TABLE counter")

    assert validate_database_schema(db_path) == []
