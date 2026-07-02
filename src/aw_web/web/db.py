from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COVER_CACHE_TTL_DAYS = 30
ALLOWED_INTERNAL_TABLES = {"sqlite_sequence"}


@dataclass(frozen=True)
class ColumnSignature:
    name: str
    type: str
    notnull: int
    default: str | None
    pk: int


@dataclass(frozen=True)
class DatabasePreparation:
    path: Path
    created: bool
    valid: bool
    errors: tuple[str, ...]


EXPECTED_SCHEMA: dict[str, tuple[ColumnSignature, ...]] = {
    "watchlist": (
        ColumnSignature("id", "INTEGER", 0, None, 1),
        ColumnSignature("provider", "TEXT", 1, None, 0),
        ColumnSignature("name", "TEXT", 1, None, 0),
        ColumnSignature("ref", "TEXT", 1, None, 0),
        ColumnSignature("anilist_id", "INTEGER", 1, "0", 0),
        ColumnSignature("current_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("last_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("status", "TEXT", 1, "'Sconosciuto'", 0),
        ColumnSignature("cover_url", "TEXT", 1, "''", 0),
        ColumnSignature("banner_url", "TEXT", 1, "''", 0),
        ColumnSignature("anime_json", "TEXT", 1, None, 0),
        ColumnSignature("episodes_checked_at", "TEXT", 1, "''", 0),
        ColumnSignature("created_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
        ColumnSignature("updated_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
    ),
    "cover_cache": (
        ColumnSignature("cache_key", "TEXT", 0, None, 1),
        ColumnSignature("anilist_id", "INTEGER", 1, "0", 0),
        ColumnSignature("title", "TEXT", 1, "''", 0),
        ColumnSignature("cover_url", "TEXT", 1, "''", 0),
        ColumnSignature("banner_url", "TEXT", 1, "''", 0),
        ColumnSignature("color", "TEXT", 1, "''", 0),
        ColumnSignature("updated_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
    ),
    "favorites": (
        ColumnSignature("id", "INTEGER", 0, None, 1),
        ColumnSignature("provider", "TEXT", 1, None, 0),
        ColumnSignature("name", "TEXT", 1, None, 0),
        ColumnSignature("ref", "TEXT", 1, None, 0),
        ColumnSignature("anilist_id", "INTEGER", 1, "0", 0),
        ColumnSignature("current_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("last_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("status", "TEXT", 1, "'Sconosciuto'", 0),
        ColumnSignature("cover_url", "TEXT", 1, "''", 0),
        ColumnSignature("banner_url", "TEXT", 1, "''", 0),
        ColumnSignature("anime_json", "TEXT", 1, None, 0),
        ColumnSignature("created_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
        ColumnSignature("updated_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
    ),
    "watch_history": (
        ColumnSignature("provider", "TEXT", 1, None, 1),
        ColumnSignature("name", "TEXT", 1, None, 0),
        ColumnSignature("ref", "TEXT", 1, None, 2),
        ColumnSignature("anilist_id", "INTEGER", 1, "0", 0),
        ColumnSignature("current_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("last_episode", "TEXT", 1, "'0'", 0),
        ColumnSignature("status", "TEXT", 1, "'Sconosciuto'", 0),
        ColumnSignature("cover_url", "TEXT", 1, "''", 0),
        ColumnSignature("banner_url", "TEXT", 1, "''", 0),
        ColumnSignature("anime_json", "TEXT", 1, None, 0),
        ColumnSignature("updated_at", "TEXT", 1, "CURRENT_TIMESTAMP", 0),
    ),
}


CREATE_TABLE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS watchlist (
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
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, ref)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cover_cache (
        cache_key TEXT PRIMARY KEY,
        anilist_id INTEGER NOT NULL DEFAULT 0,
        title TEXT NOT NULL DEFAULT '',
        cover_url TEXT NOT NULL DEFAULT '',
        banner_url TEXT NOT NULL DEFAULT '',
        color TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS watch_history (
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
    """,
)


def default_db_path() -> Path:
    path = Path.home() / ".aw-web" / "web.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def create_schema(conn: sqlite3.Connection) -> None:
    for statement in CREATE_TABLE_STATEMENTS:
        conn.execute(statement)


def prepare_database(path: Path | None = None) -> DatabasePreparation:
    db_path = path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    created = not db_path.exists()
    if created:
        with sqlite3.connect(db_path) as conn:
            create_schema(conn)

    errors = validate_database_schema(db_path)
    return DatabasePreparation(
        path=db_path,
        created=created,
        valid=not errors,
        errors=tuple(errors),
    )


def validate_database_schema(path: Path) -> list[str]:
    if not path.exists():
        return [f"Database inesistente: {path}"]

    errors: list[str] = []
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            actual_tables = {str(row["name"]) for row in table_rows}

            expected_tables = set(EXPECTED_SCHEMA)
            missing_tables = sorted(expected_tables - actual_tables)
            extra_tables = sorted(actual_tables - expected_tables - ALLOWED_INTERNAL_TABLES)
            errors.extend(f"Tabella mancante: {table}" for table in missing_tables)
            errors.extend(f"Tabella non prevista: {table}" for table in extra_tables)

            for table in sorted(expected_tables & actual_tables):
                errors.extend(_validate_table_schema(conn, table, EXPECTED_SCHEMA[table]))
    except sqlite3.DatabaseError as exc:
        return [f"Errore apertura database: {exc}"]

    return errors


def _validate_table_schema(
    conn: sqlite3.Connection,
    table: str,
    expected_columns: tuple[ColumnSignature, ...],
) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    actual_columns = tuple(
        ColumnSignature(
            name=str(row["name"]),
            type=str(row["type"]),
            notnull=int(row["notnull"]),
            default=row["dflt_value"] if row["dflt_value"] is None else str(row["dflt_value"]),
            pk=int(row["pk"]),
        )
        for row in rows
    )
    errors: list[str] = []
    expected_names = [column.name for column in expected_columns]
    actual_names = [column.name for column in actual_columns]

    missing_columns = [name for name in expected_names if name not in actual_names]
    extra_columns = [name for name in actual_names if name not in expected_names]
    errors.extend(f"Colonna mancante in {table}: {column}" for column in missing_columns)
    errors.extend(f"Colonna non prevista in {table}: {column}" for column in extra_columns)

    if not missing_columns and not extra_columns and actual_names != expected_names:
        errors.append(f"Ordine colonne non valido in {table}")

    actual_by_name = {column.name: column for column in actual_columns}
    for expected in expected_columns:
        actual = actual_by_name.get(expected.name)
        if actual is None:
            continue
        if actual != expected:
            errors.append(
                "Firma colonna non valida in "
                f"{table}.{expected.name}: attesa {expected}, trovata {actual}"
            )

    return errors


class WebDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_db_path()
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            create_schema(conn)
            conn.execute(
                "DELETE FROM cover_cache WHERE updated_at < ?",
                (self._cover_cache_cutoff(),),
            )

    def _collection(self, table: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY updated_at DESC, id DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def watchlist(self) -> list[dict[str, Any]]:
        return self._collection("watchlist")

    def favorites(self) -> list[dict[str, Any]]:
        return self._collection("favorites")

    def _find_collection_item(self, table: str, provider: str, ref: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE provider = ? AND ref = ?",
                (provider, ref),
            ).fetchone()
            return dict(row) if row else None

    def find_watch_item(self, provider: str, ref: str) -> dict[str, Any] | None:
        return self._find_collection_item("watchlist", provider, ref)

    def find_favorite_item(self, provider: str, ref: str) -> dict[str, Any] | None:
        return self._find_collection_item("favorites", provider, ref)

    def find_history_item(self, provider: str, ref: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM watch_history WHERE provider = ? AND ref = ?",
                (provider, ref),
            ).fetchone()
            return dict(row) if row else None

    def _upsert_collection_item(
        self,
        table: str,
        *,
        provider: str,
        anime_data: dict[str, Any],
        cover_url: str = "",
        banner_url: str = "",
        current_episode: str | None = None,
    ) -> None:
        current = current_episode if current_episode is not None else "0"
        with self.connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {table} (
                    provider, name, ref, anilist_id, current_episode, last_episode,
                    status, cover_url, banner_url, anime_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, ref) DO UPDATE SET
                    name = excluded.name,
                    anilist_id = excluded.anilist_id,
                    current_episode = excluded.current_episode,
                    last_episode = excluded.last_episode,
                    status = excluded.status,
                    cover_url = excluded.cover_url,
                    banner_url = excluded.banner_url,
                    anime_json = excluded.anime_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    provider,
                    str(anime_data.get("name") or ""),
                    str(anime_data.get("ref") or ""),
                    int(anime_data.get("id_anilist") or 0),
                    current,
                    str(anime_data.get("last_ep") or "0"),
                    str(anime_data.get("status") or "Sconosciuto"),
                    cover_url,
                    banner_url,
                    json.dumps(anime_data, ensure_ascii=False),
                ),
            )

    def upsert_watch_item(
        self,
        *,
        provider: str,
        anime_data: dict[str, Any],
        cover_url: str = "",
        banner_url: str = "",
        current_episode: str | None = None,
    ) -> None:
        self._upsert_collection_item(
            "watchlist",
            provider=provider,
            anime_data=anime_data,
            cover_url=cover_url,
            banner_url=banner_url,
            current_episode=current_episode,
        )

    def upsert_favorite_item(
        self,
        *,
        provider: str,
        anime_data: dict[str, Any],
        cover_url: str = "",
        banner_url: str = "",
        current_episode: str | None = None,
    ) -> None:
        self._upsert_collection_item(
            "favorites",
            provider=provider,
            anime_data=anime_data,
            cover_url=cover_url,
            banner_url=banner_url,
            current_episode=current_episode,
        )

    def upsert_history_item(
        self,
        *,
        provider: str,
        anime_data: dict[str, Any],
        cover_url: str = "",
        banner_url: str = "",
        current_episode: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO watch_history (
                    provider, name, ref, anilist_id, current_episode, last_episode,
                    status, cover_url, banner_url, anime_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, ref) DO UPDATE SET
                    name = excluded.name,
                    anilist_id = excluded.anilist_id,
                    current_episode = excluded.current_episode,
                    last_episode = excluded.last_episode,
                    status = excluded.status,
                    cover_url = excluded.cover_url,
                    banner_url = excluded.banner_url,
                    anime_json = excluded.anime_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    provider,
                    str(anime_data.get("name") or ""),
                    str(anime_data.get("ref") or ""),
                    int(anime_data.get("id_anilist") or 0),
                    current_episode,
                    str(anime_data.get("last_ep") or "0"),
                    str(anime_data.get("status") or "Sconosciuto"),
                    cover_url,
                    banner_url,
                    json.dumps(anime_data, ensure_ascii=False),
                ),
            )

    def update_current_episode(self, provider: str, ref: str, episode: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE watchlist
                SET current_episode = ?, updated_at = CURRENT_TIMESTAMP
                WHERE provider = ? AND ref = ?
                """,
                (episode, provider, ref),
            )

    def update_watch_item_availability(
        self,
        *,
        provider: str,
        ref: str,
        anime_data: dict[str, Any],
        cover_url: str,
        banner_url: str,
        checked_at: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE watchlist
                SET name = ?,
                    anilist_id = ?,
                    last_episode = ?,
                    status = ?,
                    cover_url = ?,
                    banner_url = ?,
                    anime_json = ?,
                    episodes_checked_at = ?
                WHERE provider = ? AND ref = ?
                """,
                (
                    str(anime_data.get("name") or ""),
                    int(anime_data.get("id_anilist") or 0),
                    str(anime_data.get("last_ep") or "0"),
                    str(anime_data.get("status") or "Sconosciuto"),
                    cover_url,
                    banner_url,
                    json.dumps(anime_data, ensure_ascii=False),
                    checked_at,
                    provider,
                    ref,
                ),
            )

    def mark_watch_item_episodes_checked(self, provider: str, ref: str, checked_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE watchlist
                SET episodes_checked_at = ?
                WHERE provider = ? AND ref = ?
                """,
                (checked_at, provider, ref),
            )

    def remove_watch_item(self, item_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))

    def remove_watch_item_by_ref(self, provider: str, ref: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE provider = ? AND ref = ?", (provider, ref))

    def remove_favorite_item(self, item_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM favorites WHERE id = ?", (item_id,))

    def remove_favorite_item_by_ref(self, provider: str, ref: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM favorites WHERE provider = ? AND ref = ?", (provider, ref))

    def get_cover(self, cache_key: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM cover_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            if row and self._is_cover_cache_expired(str(row["updated_at"])):
                conn.execute("DELETE FROM cover_cache WHERE cache_key = ?", (cache_key,))
                return None
            return dict(row) if row else None

    def prune_cover_cache(self) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM cover_cache WHERE updated_at < ?",
                (self._cover_cache_cutoff(),),
            )

    def _cover_cache_cutoff(self) -> str:
        cutoff = datetime.now(timezone.utc) - timedelta(days=COVER_CACHE_TTL_DAYS)
        return cutoff.strftime("%Y-%m-%d %H:%M:%S")

    def _is_cover_cache_expired(self, updated_at: str) -> bool:
        try:
            cached_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - cached_at > timedelta(days=COVER_CACHE_TTL_DAYS)

    def set_cover(
        self,
        *,
        cache_key: str,
        anilist_id: int,
        title: str,
        cover_url: str,
        banner_url: str,
        color: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO cover_cache (
                    cache_key, anilist_id, title, cover_url, banner_url, color
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    anilist_id = excluded.anilist_id,
                    title = excluded.title,
                    cover_url = excluded.cover_url,
                    banner_url = excluded.banner_url,
                    color = excluded.color,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (cache_key, anilist_id, title, cover_url, banner_url, color),
            )
