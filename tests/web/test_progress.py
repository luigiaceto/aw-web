from aw_web.anime import Anime
from aw_web.web.server import handle_play
from aw_web.web.utils import anime_to_json


def test_play_saves_progress(monkeypatch):
    anime = Anime("Test Anime", "test-ref", curr_ep="10", last_ep="11")
    anime.update_episodes({"10": "ep-10", "11": "ep-11"})
    provider = type("Provider", (), {"episode_link": lambda self, anime, episode: "https://cdn.example.com/video.mp4"})()
    saved = []

    def fake_save_watch_progress(provider_name, saved_anime, episode):
        saved.append((provider_name, saved_anime.ref, episode.num))

    monkeypatch.setattr("aw_web.services.playback.get_provider", lambda provider_name: provider)
    monkeypatch.setattr("aw_web.services.playback.open_external_player", lambda url, title: None)
    monkeypatch.setattr("aw_web.services.playback.save_watch_progress", fake_save_watch_progress)

    response = handle_play(
        {
            "provider": ["animeunity"],
            "anime": [anime_to_json(anime)],
            "episode": ["11"],
        }
    )

    assert response.startswith(b"REDIRECT:/anime?")
    assert saved == [("animeunity", "test-ref", "11")]
