# aw-web

Interfaccia web locale per navigare e guardare anime usando i provider gia supportati dal progetto: [AnimeWorld](https://www.animeworld.ac/) e [AnimeUnity](https://www.animeunity.so/).

`aw-web` avvia un sito locale su `http://127.0.0.1:8765` con ricerca anime, ultimi episodi, watchlist SQLite, copertine AniList e player integrato nel browser con fallback a proxy locale. Puoi anche aprire gli episodi con MPV/VLC.

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

### Installazione Globale Da GitHub

Puoi installare `aw-web` direttamente da questa repository GitHub:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-cli.git
```

Dopo l'installazione puoi avviare l'app da qualunque cartella con:

```bash
aw-web
```

Per aggiornare `aw-web` all'ultima versione della repository, riesegui:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-cli.git
```

Se vuoi installare da un branch specifico, per esempio `main`:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-cli.git@main
```

### Installazione Globale Da Questa Cartella

Se hai gia clonato la repository e vuoi installare la copia locale:

```bash
git clone https://github.com/luigiaceto/aw-cli.git
cd aw-cli
uv tool install -e . --force
```

Dopo l'installazione puoi avviare l'app da qualunque cartella con:

```bash
aw-web
```

### Avvio Senza Installazione Globale

Se non vuoi installare il comando globalmente, puoi avviare direttamente dal progetto:

```bash
git clone https://github.com/luigiaceto/aw-cli.git
cd aw-cli
uv run aw-web
```

Se sei gia dentro la cartella del progetto:

```bash
uv run aw-web
```

## Avvio

Avvia il server locale con:

```bash
aw-web
```

L'app verra aperta nel browser su:

```text
http://127.0.0.1:8765
```

Per fermarla, torna nel terminale e premi `Ctrl+C`.

## Utilizzo

Dalla home puoi:

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
- guardarlo nel browser;
- aprirlo in MPV/VLC.

## Watchlist e Database

La watchlist viene salvata in SQLite qui:

```text
~/.aw-cli/web.sqlite3
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

MPV/VLC resta disponibile come fallback esterno. Di solito e piu efficiente e piu robusto del player browser, soprattutto per seek, codec e stream problematici.

## Domande Frequenti

### La guida cambia tanto rispetto ad aw-cli?

Si. `aw-cli` era pensato per essere usato dal terminale con menu testuali. `aw-web` invece avvia una web app locale.

Il flusso ora e:

```text
aw-web -> browser -> ricerca/watchlist/player
```

Invece del vecchio flusso:

```text
aw-cli -> terminale -> fzf -> MPV/VLC
```

### Posso usare `uv tool install aw-web`?

Non da GitHub.

`uv tool install aw-web` funziona solo se esiste un pacchetto pubblicato con nome `aw-web` su PyPI o su un indice Python configurato.

Da GitHub devi usare l'URL della repository:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-cli.git
```

Il comando installato sara comunque:

```bash
aw-web
```

Se in futuro il pacchetto venisse pubblicato su PyPI come `aw-web`, allora avrebbe senso usare:

```bash
uv tool install aw-web
```

### Perche non si usa piu `aw-cli` da questo progetto?

Questo progetto ora espone solo il comando web:

```toml
aw-web = "aw_cli.web.app:main"
```

Se hai gia `aw-cli` installato da un'altra cartella o da PyPI, quello resta separato.

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
