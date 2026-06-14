from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def default_db_path() -> Path:
    path = Path.home() / ".aw-cli" / "web.sqlite3"
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
                CREATE TABLE IF NOT EXISTS episode_progress (
                    provider TEXT NOT NULL,
                    anime_ref TEXT NOT NULL,
                    episode_num TEXT NOT NULL,
                    progress_seconds INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(provider, anime_ref, episode_num)
                )
                """
            )

    def watchlist(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist ORDER BY updated_at DESC, id DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def find_watch_item(self, provider: str, ref: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM watchlist WHERE provider = ? AND ref = ?",
                (provider, ref),
            ).fetchone()
            return dict(row) if row else None

    def upsert_watch_item(
        self,
        *,
        provider: str,
        anime_data: dict[str, Any],
        cover_url: str = "",
        banner_url: str = "",
        current_episode: str | None = None,
    ) -> None:
        current = current_episode or str(anime_data.get("curr_ep") or "0")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO watchlist (
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

    def get_cover(self, cache_key: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM cover_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            return dict(row) if row else None

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

    def get_episode_progress(
        self, provider: str, anime_ref: str, episode_num: str
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM episode_progress
                WHERE provider = ? AND anime_ref = ? AND episode_num = ?
                """,
                (provider, anime_ref, episode_num),
            ).fetchone()
            return dict(row) if row else None

    def set_episode_progress(
        self,
        provider: str,
        anime_ref: str,
        episode_num: str,
        progress_seconds: int,
        completed: bool = False,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO episode_progress (
                    provider, anime_ref, episode_num, progress_seconds, completed
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(provider, anime_ref, episode_num) DO UPDATE SET
                    progress_seconds = excluded.progress_seconds,
                    completed = excluded.completed,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (provider, anime_ref, episode_num, progress_seconds, int(completed)),
            )
