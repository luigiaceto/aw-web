"""Database SQLite locale: watchlist, preferiti e cronologia."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from aw_web.anime import Anime, anime_from_json

# l'anime salvato vive tutto in anime_json: le colonne servono solo a chiave, progresso e ordine
Table = Literal["watchlist", "favorites", "watch_history"]


@dataclass(frozen=True)
class DatabasePreparation:
    path: Path
    created: bool
    valid: bool
    errors: tuple[str, ...]


CREATE_TABLE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS watchlist (
        ref TEXT NOT NULL PRIMARY KEY,
        current_episode TEXT NOT NULL DEFAULT '0',
        anime_json TEXT NOT NULL,
        episodes_checked_at TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        ref TEXT NOT NULL PRIMARY KEY,
        current_episode TEXT NOT NULL DEFAULT '0',
        anime_json TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watch_history (
        ref TEXT NOT NULL PRIMARY KEY,
        current_episode TEXT NOT NULL DEFAULT '0',
        anime_json TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


def db_timestamp(value: datetime) -> str:
    """Stesso formato di CURRENT_TIMESTAMP di SQLite (UTC, senza fuso)."""
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def parse_db_timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=UTC) if value else None
    except ValueError:
        return None


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


def _table_sql(conn: sqlite3.Connection) -> dict[str, str]:
    # le tabelle sqlite_* sono interne a SQLite, non fanno parte dello schema dell'app
    return dict(
        conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    )


def validate_database_schema(path: Path) -> list[str]:
    """Il database è valido se le sue tabelle sono create esattamente da CREATE_TABLE_STATEMENTS."""
    if not path.exists():
        return [f"Database inesistente: {path}"]
    try:
        with sqlite3.connect(path) as conn:
            actual = _table_sql(conn)
    except sqlite3.DatabaseError as exc:
        return [f"Errore apertura database: {exc}"]
    with sqlite3.connect(":memory:") as conn:
        create_schema(conn)
        expected = _table_sql(conn)

    return (
        [f"Tabella mancante: {table}" for table in sorted(expected.keys() - actual.keys())]
        + [f"Tabella non prevista: {table}" for table in sorted(actual.keys() - expected.keys())]
        + [
            f"Tabella diversa dallo schema atteso: {table}"
            for table in sorted(expected.keys() & actual.keys())
            if expected[table] != actual[table]
        ]
    )


class WebDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_db_path()
        with self.connect() as conn:
            create_schema(conn)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def items(self, table: Table) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY updated_at DESC, rowid DESC").fetchall()
            return [dict(row) for row in rows]

    def find(self, table: Table, ref: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE ref = ?", (ref,)).fetchone()
            return dict(row) if row else None

    def upsert(self, table: Table, anime_data: dict[str, Any], current_episode: str = "0") -> None:
        with self.connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {table} (ref, current_episode, anime_json) VALUES (?, ?, ?)
                ON CONFLICT(ref) DO UPDATE SET
                    current_episode = excluded.current_episode,
                    anime_json = excluded.anime_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(anime_data["ref"]), current_episode, json.dumps(anime_data, ensure_ascii=False)),
            )

    def remove(self, table: Table, ref: str) -> None:
        with self.connect() as conn:
            conn.execute(f"DELETE FROM {table} WHERE ref = ?", (ref,))

    def update_watch_item_availability(self, *, ref: str, anime_data: dict[str, Any], checked_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE watchlist SET ref = ?, anime_json = ?, episodes_checked_at = ? WHERE ref = ?",
                (
                    # AnimeUnity può aver cambiato il ref (relink): la riga deve seguirlo
                    str(anime_data["ref"]),
                    json.dumps(anime_data, ensure_ascii=False),
                    checked_at,
                    ref,
                ),
            )

    def mark_watch_item_episodes_checked(self, ref: str, checked_at: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE watchlist SET episodes_checked_at = ? WHERE ref = ?", (checked_at, ref))


class LazyDatabase:
    def __init__(self) -> None:
        self._database: WebDatabase | None = None

    def _get_database(self) -> WebDatabase:
        if self._database is None:
            self._database = WebDatabase()
        return self._database

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_database(), name)


_DB = LazyDatabase()
DB = cast(WebDatabase, _DB)  # creato al primo uso: i test cambiano HOME prima


def reset_lazy_database() -> None:
    _DB._database = None


def saved_anime(item: dict[str, Any]) -> Anime:
    """L'anime di una riga del database."""
    return anime_from_json(str(item["anime_json"]))
