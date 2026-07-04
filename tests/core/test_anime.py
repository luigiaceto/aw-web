import pytest
from aw_web.anime import Anime

@pytest.fixture
def anime():
    return Anime("Test Anime", "test_ref", "5", "10")

@pytest.mark.parametrize("ep1_num, ep2_num, expected", [
    ("3", "5", True),
    ("5", "3", False),
    ("5", "5.5", True),
    ("5-10", "11", True),
])
def test_episode_less_than_comparisons(anime: Anime, ep1_num, ep2_num, expected):
    ep1 = Anime.Episode(anime, ep1_num, f"ref{ep1_num}")
    ep2 = Anime.Episode(anime, ep2_num, f"ref{ep2_num}")
    assert (ep1 < ep2) is expected


def test_episode_equality_uses_anime_and_episode_number(anime: Anime):
    assert Anime.Episode(anime, "5", "ref5") == Anime.Episode(anime, "5", "other-ref")
    assert Anime.Episode(anime, "5", "ref5") != Anime.Episode(anime, "6", "ref6")

def test_episodes_sorting(anime: Anime):
    episodes = {
        "12": "ref12",
        "5.5": "ref5.5",
        "3-4": "ref3-4",
        "1": "ref1",
        "10": "ref10",
        "0": "ref0",
        "7.5": "ref7.5",
        "2": "ref2",
        "6-7": "ref5-7"
    }
    anime.update_episodes(episodes)
    anime.update_episodes({"5": "ref5"})
    expected = ["0", "1", "2", "3-4", "5", "5.5", "6-7", "7.5", "10", "12"]
    assert anime.episodes() == expected
