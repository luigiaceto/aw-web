from __future__ import annotations
from enum import Enum
from functools import total_ordering


class AnimeStatus(Enum):
    """Enum for anime status, maintaining the original order."""
    ONGOING = "In corso"
    FINISHED = "Finito"
    NOT_RELEASED = "Non rilasciato"
    UNKNOWN = "Sconosciuto"

    @classmethod
    def from_string(cls, status_str: str) -> AnimeStatus:
        match status_str:
            case "In corso":
                return cls.ONGOING
            case "Finito":
                return cls.FINISHED
            case "Non rilasciato":
                return cls.NOT_RELEASED
            case _:
                return cls.UNKNOWN

class Anime:
    """
    Classe che rappresenta un anime.

    Attributes:
        name (str): il nome dell'anime.
        ref (str): il riferimento dell'anime.
        anilist_id (int): l'ID dell'anime su Anilist.
        curr_ep (str): l'episodio corrente.
        last_ep (str): l'ultimo episodio disponibile.
        status (AnimeStatus): lo stato dell'anime.
        info (dict[str, str]): dizionario con le informazioni dell'anime.
    """

    def __init__(self, name: str, ref: str, curr_ep: str = "0", last_ep: str = "0", status: AnimeStatus = AnimeStatus.UNKNOWN) -> None:
        self.name: str = name
        self.ref: str = ref
        self.anilist_id: int = 0
        self.curr_ep: str = curr_ep
        self.last_ep: str = last_ep if last_ep != "0" else curr_ep
        self.status: AnimeStatus = status
        self._episodes: list[Anime.Episode] = []
        self._num_to_index: dict[str, int] = {}
        self.info: dict[str, str] = {}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Anime):
            return False

        if self.anilist_id and other.anilist_id:
            return self.anilist_id == other.anilist_id

        return self.name == other.name # idealmente andrebbe tolto

    def __hash__(self) -> int:
        if self.anilist_id:
            return hash(self.anilist_id)

        return hash(self.name)

    def update_episodes(self, episodes: dict[str, str] | None = None, specials: bool = True) -> None:
        """
        Imposta i riferimenti degli episodi dell'anime.
        Args:
            episodes (dict[str, str]): dizionario dei riferimenti degli episodi dell'anime (numero->URL/ID).
        """
        episodes = episodes or {}
        for num, ref in episodes.items():
            if not specials and ("." in num or num == "0"):
                continue
            if self.has_episode(num):
                self.episode(num).ref = ref
                continue
            self._episodes.append(Anime.Episode(self, num, ref))

        self._episodes.sort()
        self._num_to_index = {ep.num: i for i, ep in enumerate(self._episodes)}

        if self.has_episode(self.last_ep) and self._episodes[-1] > self.episode(self.last_ep):
            self.last_ep = self._episodes[-1].num

    def episodes(self) -> list[str]:
        """
        Restituisce una lista dei numeri degli episodi disponibili.

        Returns:
            list[str]: la lista dei numeri degli episodi disponibili.
        """
        return list(self._num_to_index.keys())

    def has_episode(self, ep_num: str) -> bool:
        """
        Controlla se l'anime ha l'episodio specificato.
        Args:
            ep_num (str): Il numero dell'episodio.
        Returns:
            (bool): True se l'anime ha l'episodio, False altrimenti.
        """
        return ep_num in self._num_to_index

    def episode(self, ep_num: str) -> Anime.Episode:
        """
        Restituisce il riferimento dell'episodio corrispondente al numero specificato.
        Args:
            ep_num (str): Il numero dell'episodio.
        Returns:
            Anime.Episode : l'episodio corrispondente al numero
        """

        return self._episodes[self._num_to_index[ep_num]]

    def set_info(self, anilist_id: int | str | None, status: AnimeStatus, info: dict[str, str]) -> None:
        """
        Imposta le informazioni dell'anime.
        Args:
            anilist_id (int): l'ID di Anilist dell'anime.
            status (AnimeStatus): lo stato dell'anime.
            info (dict): dizionario delle informazioni dell'anime.
        """
        try:
            self.anilist_id = int(anilist_id or 0)
        except (TypeError, ValueError):
            self.anilist_id = 0
        self.info = info
        self.status = status

    def effective_episodes_count(self) -> int:
        """
        Calcola il numero totale effettivo di episodi, ignorando gli speciali (.5)
        e scompattando i batch (es. 1-12 conta come 12 episodi).
        """
        total = 0
        for ep in self.episodes():
            if '.' in ep:
                continue
            if '-' in ep:
                parts = ep.split('-')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    total += (int(parts[1]) - int(parts[0]) + 1)
                else:
                    total += 1
            else:
                total += 1
        return total

    def has_all_episodes(self) -> bool:
        """
        Verifica se l'anime ha già in memoria tutti gli episodi noti per essere stati rilasciati.
        """
        try:
            return self.effective_episodes_count() >= int(self.last_ep)
        except ValueError:
            return False

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Anime:
        """
        Crea un oggetto Anime a partire da un dizionario.

        Args:
            data (dict): il dizionario con le informazioni dell'anime.

        Returns:
            Anime: l'oggetto Anime creato.
        """
        anime = Anime(
            name=str(data["name"]),
            ref=str(data["ref"]),
            curr_ep=str(data["curr_ep"]),
            last_ep=str(data["last_ep"])
        )
        id_anilist = data.get("id_anilist")
        status_str = str(data.get("status", "Sconosciuto"))
        info = data.get("info", {})

        anime.set_info(
            anilist_id=int(id_anilist) if isinstance(id_anilist, int) else 0,
            status=AnimeStatus.from_string(status_str),
            info=dict(info) if isinstance(info, dict) else {}
        )

        episodes_data = data["episodes"] if isinstance(data["episodes"], list) else []
        anime._episodes = [Anime.Episode.from_dict(anime, ep) for ep in episodes_data]
        anime.update_episodes()

        return anime

    def to_dict(self) -> dict[str, object]:
        """
        Restituisce un dizionario con le informazioni dell'anime.

        Returns:
            dict: un dizionario con le informazioni dell'anime.
        """
        return {
            "name": self.name,
            "ref": self.ref,
            "curr_ep": self.curr_ep,
            "last_ep": self.last_ep,
            "id_anilist": self.anilist_id,
            "status": self.status.value,
            "info": self.info,
            "episodes": [ep.to_dict() for ep in self._episodes]
        }

    @total_ordering
    class Episode:
        """
        Classe che rappresenta un episodio di un anime.

        Attributes:
            num (str): il numero dell'episodio.
            ref (str): il riferimento dell'episodio.
        """

        def __init__(self, anime: Anime, num: str, ref: str) -> None:
            self._anime = anime
            self.num = num
            self.ref = ref

        def __str__(self) -> str:
            return f"{self._anime.name} Ep. {self.num}"

        def __repr__(self) -> str:
            return f"Episode(num={self.num}, ref={self.ref})"

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Anime.Episode):
                return False
            return self._anime == other._anime and self.num == other.num

        def __hash__(self) -> int:
            return hash((self._anime, self.num))

        def __lt__(self, other: object) -> bool:
            if not isinstance(other, Anime.Episode) or self._anime != other._anime:
                return False
            self_num = self.numeric() if '-' in self.num else float(self.num)
            other_num = other.numeric() if '-' in other.num else float(other.num)
            return self_num < other_num

        def numeric(self) -> int:
            """
            Restituisce il numero dell'episodio come intero.

            - se è x.5 arrotonda a x.
            - se è x-y restituisce y.

            Returns:
                int: il numero dell'episodio.
            """
            if '.' in self.num:
                return int(self.num.split('.')[0])
            if '-' in self.num:
                return int(self.num.split('-')[1])
            return int(self.num)

        @classmethod
        def from_dict(cls, anime: Anime, data: dict[str, object]) -> Anime.Episode:
            """
            Crea un oggetto Episode a partire da un dizionario.

            Args:
                anime (Anime): l'anime a cui appartiene l'episodio.
                data (dict): il dizionario con le informazioni dell'episodio.

            Returns:
                Anime.Episode: l'oggetto Episode creato.
            """
            return cls(
                anime,
                num=str(data["num"]),
                ref=str(data["ref"])
            )

        def to_dict(self) -> dict[str, object]:
            """
            Restituisce un dizionario con le informazioni dell'episodio.

            Returns:
                dict: il dizionario con le informazioni dell'episodio.
            """
            return {
                "num": self.num,
                "ref": self.ref,
        }
