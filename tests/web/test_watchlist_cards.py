from aw_web.anime import Anime
from aw_web.web.components import watch_card
from aw_web.web.utils import anime_to_json, available_last_episode, has_new_episode


def test_watch_card_uses_latest_episode_for_display():
    saved_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="10", last_ep="10")
    saved_anime.update_episodes({"10": "old-episode"})
    latest_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="11", last_ep="11")
    latest_anime.update_episodes({"11": "new-episode"})
    item = {
        "id": 1,
        "provider": "animeworld",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "10",
        "last_episode": "10",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [latest_anime])

    assert has_new_episode(item, [latest_anime])
    assert available_last_episode(item, [latest_anime]) == "11"
    assert "Nuovo episodio" in html
    assert "<strong>10</strong> / 11" in html
