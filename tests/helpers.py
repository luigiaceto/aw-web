"""Costruttori di dati finti condivisi dai test."""

from typing import Any

from aw_web.anilist import SeasonalAnime
from aw_web.anime import Anime, anime_to_json


def seasonal(**overrides: Any) -> SeasonalAnime:
    """Un anime AniList: si passano solo i campi che contano per il test."""
    values: dict[str, Any] = {
        "anilist_id": 123,
        "title": "Example Anime",
        "title_romaji": "",
        "title_english": "",
        "title_native": "",
        "synonyms": (),
        "cover_url": "",
        "episodes": 12,
        "genres": (),
        "average_score": 0,
    }
    return SeasonalAnime(**{**values, **overrides})


def anilist_media(anilist_id: int, title: str, **overrides: Any) -> dict[str, Any]:
    """Un media come lo restituisce l'API GraphQL di AniList."""
    return {
        "id": anilist_id,
        "title": {"english": title, "romaji": "", "native": ""},
        "synonyms": [],
        "coverImage": {},
        "episodes": 12,
        "genres": [],
        "averageScore": 0,
        "isAdult": False,
        **overrides,
    }


def saved_row(anime: Anime, current_episode: str = "0") -> dict[str, Any]:
    """Una riga di watchlist/preferiti come la restituisce il database."""
    return {"ref": anime.ref, "current_episode": current_episode, "anime_json": anime_to_json(anime)}
