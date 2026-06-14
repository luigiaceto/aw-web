from aw_web.anime import Anime
from aw_web.web.db import WebDatabase


def test_new_watch_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_watch_item(provider="animeunity", anime_data=anime.to_dict())

    item = db.find_watch_item("animeunity", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert item["last_episode"] == "12"
