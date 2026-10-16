import sqlite3

from aw_web.anime import Anime
from aw_web.web.db import WebDatabase, prepare_database, validate_database_schema


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


def test_validate_database_schema_fails_on_missing_column(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE watchlist (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute(
            """
            CREATE TABLE cover_cache (
                cache_key TEXT PRIMARY KEY,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                title TEXT NOT NULL DEFAULT '',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                name TEXT NOT NULL,
                ref TEXT NOT NULL,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                current_episode TEXT NOT NULL DEFAULT '0',
                last_episode TEXT NOT NULL DEFAULT '0',
                status TEXT NOT NULL DEFAULT 'Sconosciuto',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                anime_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, ref)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE watch_history (
                provider TEXT NOT NULL,
                name TEXT NOT NULL,
                ref TEXT NOT NULL,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                current_episode TEXT NOT NULL DEFAULT '0',
                last_episode TEXT NOT NULL DEFAULT '0',
                status TEXT NOT NULL DEFAULT 'Sconosciuto',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                anime_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(provider, ref)
            )
            """
        )

    errors = validate_database_schema(db_path)

    assert "Colonna mancante in watchlist: provider" in errors


def test_validate_database_schema_fails_on_extra_column(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE watchlist ADD COLUMN unexpected TEXT")

    errors = validate_database_schema(db_path)

    assert "Colonna non prevista in watchlist: unexpected" in errors


def test_validate_database_schema_fails_on_extra_table(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE episode_progress (id INTEGER PRIMARY KEY)")

    errors = validate_database_schema(db_path)

    assert "Tabella non prevista: episode_progress" in errors


def test_validate_database_schema_fails_on_missing_unique_constraint(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE watchlist RENAME TO watchlist_old")
        conn.execute(
            """
            CREATE TABLE watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                name TEXT NOT NULL,
                ref TEXT NOT NULL,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                current_episode TEXT NOT NULL DEFAULT '0',
                last_episode TEXT NOT NULL DEFAULT '0',
                status TEXT NOT NULL DEFAULT 'Sconosciuto',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                anime_json TEXT NOT NULL,
                episodes_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("DROP TABLE watchlist_old")

    errors = validate_database_schema(db_path)

    assert any("Indici non validi in watchlist" in error for error in errors)


def test_validate_database_schema_fails_on_wrong_column_signature(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE watchlist RENAME TO watchlist_old")
        conn.execute(
            """
            CREATE TABLE watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                name TEXT NOT NULL,
                ref TEXT NOT NULL,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                current_episode TEXT NOT NULL DEFAULT '0',
                last_episode TEXT NOT NULL DEFAULT '0',
                status TEXT NOT NULL DEFAULT 'Sconosciuto',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                anime_json TEXT NOT NULL,
                episodes_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, ref)
            )
            """
        )
        conn.execute("DROP TABLE watchlist_old")

    errors = validate_database_schema(db_path)

    assert any("Firma colonna non valida in watchlist.provider" in error for error in errors)


def test_validate_database_schema_accepts_same_columns_in_different_order(tmp_path):
    db_path = tmp_path / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE watchlist RENAME TO watchlist_old")
        conn.execute(
            """
            CREATE TABLE watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                name TEXT NOT NULL,
                ref TEXT NOT NULL,
                anilist_id INTEGER NOT NULL DEFAULT 0,
                current_episode TEXT NOT NULL DEFAULT '0',
                last_episode TEXT NOT NULL DEFAULT '0',
                status TEXT NOT NULL DEFAULT 'Sconosciuto',
                cover_url TEXT NOT NULL DEFAULT '',
                banner_url TEXT NOT NULL DEFAULT '',
                anime_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                episodes_checked_at TEXT NOT NULL DEFAULT '',
                UNIQUE(provider, ref)
            )
            """
        )
        conn.execute("DROP TABLE watchlist_old")

    errors = validate_database_schema(db_path)

    assert errors == []


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
    assert item["episodes_checked_at"] == ""


def test_history_does_not_create_watch_item(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_history_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="3",
    )

    history_item = db.find_history_item("animeunity", "test-ref")

    assert history_item is not None
    assert history_item["current_episode"] == "3"
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
