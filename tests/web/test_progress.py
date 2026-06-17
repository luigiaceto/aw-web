from aw_web.anime import Anime
from aw_web.web.server import handle_watch_start
from aw_web.web.utils import anime_to_json


def test_browser_watch_start_saves_progress(monkeypatch):
    anime = Anime("Test Anime", "test-ref", curr_ep="10", last_ep="11")
    anime.update_episodes({"10": "ep-10", "11": "ep-11"})
    saved = []

    def fake_save_watch_progress(provider_name, saved_anime, episode):
        saved.append((provider_name, saved_anime.ref, episode.num))

    monkeypatch.setattr("aw_web.web.server.save_watch_progress", fake_save_watch_progress)

    response = handle_watch_start(
        {
            "provider": ["animeworld"],
            "anime": [anime_to_json(anime)],
            "episode": ["11"],
        }
    )

    assert response.startswith(b"REDIRECT:/watch?token=")
    assert saved == [("animeworld", "test-ref", "11")]
