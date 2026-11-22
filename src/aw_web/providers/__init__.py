from .animeunity import Animeunity
from .provider import ProviderError

PROVIDER = Animeunity()

__all__ = [
    "Animeunity",
    "PROVIDER",
    "ProviderError",
]
