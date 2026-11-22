"""Collegamento con AnimeUnity (animeunity.cx), l'unico provider dell'app."""

import json
import re
from html import unescape
from typing import Any

from httpx import Client, HTTPError

from aw_web.anime import Anime, AnimeStatus


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete an operation."""


def error_handler(relink=False):
    """
    Decoratore per gestire gli errori delle funzioni.
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if relink and isinstance(e, HTTPError):
                    return update_link(self, func, *args, **kwargs)
                raise ProviderError(f"Errore {e.__class__.__name__} durante {func.__name__}: {e}") from e

        return wrapper

    return decorator


def update_link(self, callback, anime: Anime, episode: Anime.Episode | None = None):
    """
    Riprova l'operazione quando il riferimento dell'anime o dell'episodio non è più valido.
    """
    if episode:
        self.episodes(anime)
        return callback(self, anime, anime.episode(episode.num))

    res: list[Anime] | None = self.search(anime.name)
    match = next(
        (found for found in res or [] if found.name.lower() == anime.name.lower()),
        None,
    )
    if match is None:
        raise ProviderError(
            f"Errore o nessun risultato durante la ricerca di {anime.name} su {self.__class__.__name__}"
        )
    anime.ref = match.ref
    return callback(self, anime)


STREAM_URL_PATTERNS = (
    re.compile(r"""window\.downloadUrl\s*=\s*["'](?P<url>https?:\\?/\\?/[^"']+)["']""", re.IGNORECASE),
    re.compile(
        r"""(?:downloadUrl|file|source|src|url)\s*[:=]\s*["'](?P<url>https?:\\?/\\?/[^"']+)["']""", re.IGNORECASE
    ),
    re.compile(r"""data-(?:url|src|link)=["'](?P<url>https?:\\?/\\?/[^"']+)["']""", re.IGNORECASE),
    re.compile(r"""["'](?P<url>https?:\\?/\\?/[^"']+\.(?:mp4|m3u8)(?:\?[^"']*)?)["']""", re.IGNORECASE),
)


def clean_stream_url(url: str) -> str:
    return unescape(url).replace("\\/", "/").strip()


def stream_urls_from_html(html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for pattern in STREAM_URL_PATTERNS:
        for match in pattern.finditer(html):
            url = clean_stream_url(match.group("url"))
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


ORIGINAL_LANGUAGE = "jpn"  # audio originale (sub ita): ref senza suffisso
STATUS = {
    "ongoing": AnimeStatus.ONGOING,
    "completed": AnimeStatus.FINISHED,
    "upcoming": AnimeStatus.NOT_RELEASED,
}
SEASONS = {"winter": "Inverno", "spring": "Primavera", "summer": "Estate", "fall": "Autunno"}
PAGE_PROPS = re.compile(r'data-page="([^"]*)"')


def split_ref(ref: str) -> tuple[str, str]:
    """Ref -> (id AnimeUnity, lingua): "4851" è il sub ita, "4851-ita" il doppiaggio."""
    anime_id, _, language = ref.partition("-")
    return anime_id, language or ORIGINAL_LANGUAGE


def _ref(anime_id: object, language: str) -> str:
    return str(anime_id) if language == ORIGINAL_LANGUAGE else f"{anime_id}-{language}"


def _languages(data: dict[str, Any]) -> list[str]:
    """Lingue disponibili, l'originale per prima: così il sub precede il doppiaggio."""
    languages = [variant["language"] for variant in data.get("variants") or []] or [ORIGINAL_LANGUAGE]
    return sorted(dict.fromkeys(languages), key=lambda language: language != ORIGINAL_LANGUAGE)


def _info(data: dict[str, Any]) -> dict[str, str]:
    return {
        "Categoria": str(data.get("type") or "").upper(),
        "Stagione": f"{SEASONS.get(str(data.get('season')), '')} {data.get('year') or ''}".strip(),
        "Studio": ", ".join(studio["name"] for studio in data.get("studios") or []),
        "Genere": ", ".join(genre["name"] for genre in data.get("genres") or []),
        "Voto": str(data.get("score") or ""),
        "Durata": f"{data['episode_runtime']} min" if data.get("episode_runtime") else "",
        "Episodi": str(data.get("total_episodes") or "??"),
        "Visualizzazioni": str(data.get("views") or ""),
        "Trama": str(data.get("plot") or ""),
    }


def _fill(anime: Anime, data: dict[str, Any], language: str) -> None:
    """Copia nell'anime i dati di AnimeUnity per la lingua scelta."""
    variant = next((v for v in data.get("variants") or [] if v["language"] == language), {})
    anime.last_ep = str(variant.get("episodes_count") or data.get("total_episodes") or anime.last_ep)
    anime.set_info(
        data.get("anilist_id"),
        STATUS.get(str(variant.get("status") or data.get("default_status")), AnimeStatus.UNKNOWN),
        _info(data),
    )
    images = data.get("images") or {}
    anime.cover_url = str(images.get("poster") or images.get("cover") or "")
    anime.banner_url = str(images.get("banner") or "")


def _anime(data: dict[str, Any], language: str, curr_ep: str = "0") -> Anime:
    title = str(data["title"])
    name = title if language == ORIGINAL_LANGUAGE else f"{title} ({language.upper()})"
    anime = Anime(name, _ref(data["id"], language), curr_ep=curr_ep)
    _fill(anime, data, language)
    return anime


class Animeunity:
    """
    Collegamento con AnimeUnity, l'unico provider dell'app.

    I metodi pubblici gestiscono errori e relink (vedi `error_handler`);
    quelli con `_` fanno solo le richieste HTTP.
    """

    def __init__(self, client: Client | None = None):
        self.BASE_URL = "https://animeunity.cx"
        self.Client = client or Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                "Accept": "application/json",
            },
            follow_redirects=True,
            timeout=10,
        )

    @error_handler(relink=False)
    def search(self, input: str) -> list[Anime]:
        return self._search(input)

    @error_handler(relink=False)
    def latest(self) -> list[Anime]:
        """Ultime uscite: tutte le entry di uno stesso anime ricevono gli stessi episodi."""
        animes = self._latest()

        grouped_animes: dict[str, list[Anime]] = {}
        for anime in animes:
            grouped_animes.setdefault(anime.name, []).append(anime)

        for group in grouped_animes.values():
            if len(group) > 1:
                all_episodes = {}
                for anime in group:
                    for ep in anime._episodes:
                        all_episodes[ep.num] = ep.ref

                for anime in group:
                    anime.update_episodes(all_episodes)

        return animes

    @error_handler(relink=True)
    def episodes(self, anime: Anime) -> None:
        """Carica dentro `anime` i riferimenti agli episodi disponibili."""
        anime.update_episodes(self._episodes(anime))

    @error_handler(relink=True)
    def episode_link(self, anime: Anime, episode: Anime.Episode) -> str:
        return self._episode_link(anime, episode)

    @error_handler(relink=True)
    def info_anime(self, anime: Anime) -> None:
        """Carica dentro `anime` le informazioni della scheda."""
        self._info_anime(anime)

    def _get(self, path: str, **params: str | int) -> Any:
        response = self.Client.get(f"{self.BASE_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()

    def _page_props(self, path: str) -> dict[str, Any]:
        """Le pagine del sito sono Inertia: i dati stanno nell'attributo data-page."""
        response = self.Client.get(f"{self.BASE_URL}{path}", headers={"Accept": "text/html"})
        response.raise_for_status()
        match = PAGE_PROPS.search(response.text)
        if not match:
            raise ValueError("Dati della pagina AnimeUnity non trovati")
        return json.loads(unescape(match.group(1)))["props"]

    def _search(self, input: str) -> list[Anime]:
        results = self._get("/api/search", q=input)["data"]
        return [_anime(data, language) for data in results for language in _languages(data)]

    def _latest(self) -> list[Anime]:
        animes = list[Anime]()
        for video in self._get("/api/home/latest-episodes")["data"]:
            number = str(video["episode"]["number"])
            anime = _anime(video["episode"]["anime"], video["language"], curr_ep=number)
            anime.update_episodes({number: str(video["id"])})
            animes.append(anime)
        return animes

    def _episodes(self, anime: Anime) -> dict[str, str]:
        """Numero episodio -> id del video nella lingua dell'anime (a blocchi di 120)."""
        anime_id, language = split_ref(anime.ref)
        episodes: dict[str, str] = {}
        start = 1
        while True:
            page = self._get(f"/api/anime/{anime_id}/episodes", start=start)
            for episode in page["episodes"]:
                for video in episode["videos"]:
                    if video["language"] == language and not video["is_hidden"]:
                        episodes[str(episode["number"])] = str(video["id"])
            start += len(page["episodes"])
            if not page["episodes"] or start > page["total"]:
                return episodes

    def _episode_link(self, anime: Anime, episode: Anime.Episode) -> str:
        anime_id, _ = split_ref(anime.ref)
        # lo slug nell'URL è libero: il sito reindirizza a quello giusto
        embed_url = self._page_props(f"/anime/{anime_id}-anime/{episode.ref}")["embedUrl"]
        embed = self.Client.get(embed_url, headers={"Referer": f"{self.BASE_URL}/"})  # vixcloud risponde 403 senza
        embed.raise_for_status()
        urls = stream_urls_from_html(embed.text)
        if not urls:
            raise ValueError("Link video non trovato nella pagina")
        return urls[0]

    def _info_anime(self, anime: Anime) -> None:
        anime_id, language = split_ref(anime.ref)
        if not anime_id.isdigit():
            raise HTTPError("Errore 404: pagina non trovata")
        _fill(anime, self._page_props(f"/anime/{anime_id}-anime")["anime"], language)


PROVIDER = Animeunity()
