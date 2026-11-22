from datetime import UTC, datetime, timedelta

from aw_web.anime import Anime
from aw_web.animeunity import Animeunity
from aw_web.db import WebDatabase, db_timestamp, saved_anime
from aw_web.refresh import (
    refresh_watchlist_availability,
    should_refresh_watch_item,
)


def test_should_refresh_watch_item_after_six_hours():
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    item = {"episodes_checked_at": db_timestamp(now - timedelta(hours=6))}

    assert should_refresh_watch_item(item, now)


def test_should_not_refresh_watch_item_before_six_hours():
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    item = {"episodes_checked_at": db_timestamp(now - timedelta(hours=5, minutes=59))}

    assert not should_refresh_watch_item(item, now)


def test_refresh_watchlist_availability_updates_episode_count(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    anime.update_episodes({"8": "episode-8"})
    db.upsert("watchlist", anime.to_dict(), "8")

    class FakeProvider(Animeunity):
        def info_anime(self, anime: Anime) -> None:
            anime.last_ep = "9"

        def episodes(self, anime: Anime) -> None:
            anime.update_episodes({"8": "episode-8", "9": "episode-9"})

    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    refresh_watchlist_availability(
        db,
        db.items("watchlist"),
        FakeProvider(),
        now=now,
    )

    item = db.find("watchlist", "provider-ref")

    assert item is not None
    assert item["current_episode"] == "8"
    assert saved_anime(item).last_ep == "9"
    assert item["episodes_checked_at"] == db_timestamp(now)
    assert saved_anime(item).has_episode("9")


def test_refresh_watchlist_availability_skips_fresh_items(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    db.upsert("watchlist", anime.to_dict(), "8")
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    db.mark_watch_item_episodes_checked(
        "provider-ref",
        db_timestamp(now - timedelta(hours=1)),
    )

    class UnusedProvider(Animeunity):
        def info_anime(self, anime: Anime) -> None:
            raise AssertionError("fresh items should not hit the provider")

    refresh_watchlist_availability(
        db,
        db.items("watchlist"),
        UnusedProvider(),
        now=now,
    )

    item = db.find("watchlist", "provider-ref")
    assert item is not None
    assert saved_anime(item).last_ep == "8"


def test_refresh_watchlist_availability_marks_failed_attempt(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    db.upsert("watchlist", anime.to_dict(), "8")

    class BrokenProvider(Animeunity):
        def info_anime(self, anime: Anime) -> None:
            raise RuntimeError("provider down")

        def episodes(self, anime: Anime) -> None:
            raise AssertionError("episodes should not be called")

    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    refresh_watchlist_availability(
        db,
        db.items("watchlist"),
        BrokenProvider(),
        now=now,
    )

    item = db.find("watchlist", "provider-ref")
    assert item is not None
    assert saved_anime(item).last_ep == "8"
    assert item["episodes_checked_at"] == db_timestamp(now)


def test_refresh_watchlist_availability_follows_a_relinked_ref(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "old-ref", curr_ep="1", last_ep="1")
    db.upsert("watchlist", anime.to_dict(), "1")

    class FakeProvider(Animeunity):
        def info_anime(self, anime: Anime) -> None:
            anime.ref = "new-ref"

        def episodes(self, anime: Anime) -> None:
            anime.update_episodes({"1": "episode-1"})

    refresh_watchlist_availability(
        db,
        db.items("watchlist"),
        FakeProvider(),
    )

    assert db.find("watchlist", "old-ref") is None
    item = db.find("watchlist", "new-ref")
    assert item is not None
    assert item["current_episode"] == "1"
