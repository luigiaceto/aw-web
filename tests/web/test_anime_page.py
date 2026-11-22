"""Test della pagina dettaglio di un anime."""

from unittest.mock import MagicMock

from aw_web.anime import Anime
from aw_web.web.db import WebDatabase
from aw_web.web.views import render_anime


def _provider(monkeypatch, episodes: dict[str, str]) -> MagicMock:
    provider = MagicMock()
    provider.info_anime.return_value = None
    provider.episodes.side_effect = lambda anime: anime.update_episodes(episodes)
    monkeypatch.setattr("aw_web.web.views.PROVIDER", provider)
    return provider


def test_anime_page_embeds_the_anime_once_for_all_episodes(monkeypatch):
    _provider(monkeypatch, {str(number): f"ref-{number}" for number in range(1, 301)})

    body = render_anime({"name": ["Example"], "ref": ["123"]})

    # un form "Guarda" condiviso + i due toggle watchlist/preferiti, qualunque sia il numero di episodi
    assert body.count(b'name="anime"') == 3
    assert body.count(b'action="/play"') == 1
    assert body.count(b'form="play-form" name="episode"') == 300
    assert len(body) < 500_000


def test_anime_page_saved_does_not_refetch_episodes(monkeypatch, tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Saved Anime", "123", curr_ep="1", last_ep="12")
    anime.update_episodes({"1": "episode-ref"})
    db.upsert("watchlist", anime.to_dict(), "1")
    provider = _provider(monkeypatch, {})
    monkeypatch.setattr("aw_web.web.views.DB", db)

    body = render_anime({"saved": ["1"], "ref": ["123"]})

    provider.episodes.assert_not_called()
    assert b"Ultimo visto: 1" in body
