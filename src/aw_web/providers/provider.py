from httpx import HTTPError
from ..anime import Anime

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
                raise ProviderError(
                    f"Errore {e.__class__.__name__} durante {func.__name__}: {e}"
                ) from e

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
