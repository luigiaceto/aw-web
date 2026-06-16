from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COVER_CACHE_TTL_DAYS = 30


def default_db_path() -> Path:
    path = Path.home() / ".aw-web" / "web.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
            conn.execute(
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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider, ref)
                )
                """
            )
            conn.execute(
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
                """
            )
            conn.execute(
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
                """
            )
            conn.execute(
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
                """
            )
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
