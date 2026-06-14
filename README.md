# aw-web

Interfaccia web locale per navigare e guardare anime con [AnimeWorld](https://www.animeworld.ac/) e [AnimeUnity](https://www.animeunity.so/).

`aw-web` avvia un sito locale su `http://127.0.0.1:8765` con ricerca anime, ultimi episodi, watchlist, copertine AniList e player integrato nel browser o con MPV/VLC.

## Indice

- [Installazione](#installazione)
- [Avvio](#avvio)
- [Utilizzo](#utilizzo)
- [Watchlist e Database](#watchlist-e-database)
- [Player Browser e MPV/VLC](#player-browser-e-mpvlc)
- [Domande Frequenti](#domande-frequenti)
- [Problemi Noti](#problemi-noti)

## Installazione

Sono richiesti:

- [uv](https://github.com/astral-sh/uv)
- Python 3.10+
- MPV o VLC, consigliato come fallback esterno

Su macOS puoi installare `uv` e `mpv` con:

```bash
brew install uv mpv
```

Oppure, se preferisci VLC:

```bash
brew install uv vlc
```

### Installazione (Globale) Da GitHub

Puoi installare `aw-web` direttamente da questa repository GitHub:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-web.git
```

Per aggiornare `aw-web` all'ultima versione della repository, ripetere il comando.

## Avvio

Avvia ad terminale il server locale con:

```bash
aw-web
```

L'app verra aperta nel browser su:

```text
http://127.0.0.1:8765
```

Per fermarla, torna nel terminale e premi `Ctrl+C`.

## Utilizzo

Dalla home dell'app puoi:

- vedere gli ultimi episodi usciti;
- cercare anime;
- aprire la pagina dettaglio di un anime;
- aggiungere o rimuovere anime dalla watchlist;
- vedere a che episodio eri arrivato;
- vedere il badge `Nuovo episodio` quando esiste un episodio successivo all'ultimo visto.

Nella pagina anime puoi:

- leggere info e trama;
- vedere la copertina recuperata da AniList;
- scegliere un episodio;
- guardarlo nel browser o aprirlo in MPV/VLC.

## Watchlist e Database

La watchlist viene salvata in un database SQLite dentro:

```text
~/.aw-web/web.sqlite3
```

Nel database vengono salvati:

- anime in watchlist;
- provider usato;
- ultimo episodio visto;
- progresso dell'episodio nel player browser;
- copertine AniList cacheate;
- metadati necessari per riaprire gli anime.

## Player Browser e MPV/VLC

`aw-web` supporta due modalita di riproduzione.

### Browser

Il player browser prova prima la modalita diretta:

```text
server video -> browser
```

Se il browser non riesce a riprodurre il video, passa automaticamente al proxy locale:

```text
server video -> aw-web -> browser
```

Nella pagina player viene mostrato un badge in alto a destra:

- verde: `Diretto`
- blu: `Buffering`
- giallo: `Proxy fallback`
- rosso: `Errore video`

### MPV/VLC

MPV/VLC resta disponibile come fallback esterno. Di solito è più efficiente e più robusto del player browser, soprattutto per seek, codec e stream problematici.

## Domande Frequenti

### Come funziona il flusso?

`aw-web` avvia una web app locale e usa il browser come interfaccia principale:

```text
aw-web -> browser -> ricerca/watchlist/player
```

### Posso usare `uv tool install aw-web`?

Se in futuro il pacchetto venisse pubblicato su PyPI come `aw-web`, allora si potrà usare:

```bash
uv tool install aw-web
```

### Quale comando espone il progetto?

Questo progetto espone solo il comando web:

```toml
aw-web = "aw_web.web.app:main"
```

## Problemi Noti

- Se `aw-web` non viene trovato dopo l'installazione, aggiorna il PATH dei tool `uv`:

  ```bash
  uv tool update-shell
  ```

  Poi chiudi e riapri il terminale.

- Se il player browser fallisce, prova il pulsante MPV/VLC.

- Se MPV/VLC non si apre, verifica che sia installato e disponibile nel PATH:

  ```bash
  which mpv
  which vlc
  ```

- Se appare un errore di certificati SSL, potrebbe essere necessario aggiornare i certificati del sistema.
