# aw-web

Interfaccia web locale per navigare e guardare anime senza pubblicità o pop-up.

<img width="1470" height="877" alt="Screenshot 2026-06-16 alle 22 44 26" src="https://github.com/user-attachments/assets/8b0e6ec5-3dc2-42ab-8b3d-f1cef255a7c9" />

<img width="1470" height="877" alt="Screenshot 2026-06-16 alle 22 43 53" src="https://github.com/user-attachments/assets/254eb4e0-bc87-42bb-b0ad-25f833ad1f04" />

`aw-web` avvia un sito web locale su `http://127.0.0.1:8765` con ricerca anime, ultimi episodi, watchlist, preferiti, anime stagionali, copertine e player integrato nel browser o con MPV/VLC.

## Indice

- [Installazione](#installazione-su-macos-unico-os-supportato-e-testato-attualmente)
- [Avvio](#avvio)
- [Utilizzo](#utilizzo)
- [Anime Stagionali](#anime-stagionali)
- [Watchlist, Preferiti e Database](#watchlist-preferiti-e-database)
- [Player Browser e MPV/VLC](#player-browser-e-mpvvlc)
- [Domande Frequenti](#domande-frequenti)
- [Problemi Noti](#problemi-noti)

## Installazione su MacOS (unico OS supportato e testato attualmente)

Sono richiesti:

- [uv](https://github.com/astral-sh/uv)
- Python 3.10+
- MPV o VLC, come video player fallback esterno

Su macOS puoi installare `uv` e `mpv` tramite `brew` con:

```bash
brew install uv mpv
```

Oppure, se preferisci VLC:

```bash
brew install uv vlc
```

### Installazione (Globale) Da GitHub

Puoi installare `aw-web` direttamente da questa repository GitHub tramite `uv`:

```bash
uv tool install --force git+https://github.com/luigiaceto/aw-web.git
```

Per aggiornare `aw-web` all'ultima versione della repository, ripetere il comando.

## Avvio

Avvia da terminale il server locale con:

```bash
aw-web
```

L'app verrà aperta nel browser su:

```text
http://127.0.0.1:8765
```

Per fermarla, torna nel terminale e premi `Ctrl+C`.

## Utilizzo

Dalla home dell'app puoi:

- vedere gli ultimi episodi usciti;
- aprire la pagina degli anime stagionali;
- cercare anime;
- aprire la pagina dettaglio di un anime;
- vedere la tua watchlist;
- vedere i tuoi preferiti;
- vedere a che episodio eri arrivato;
- vedere il badge `Nuovo episodio` quando esiste un episodio successivo all'ultimo visto.

Nella pagina anime puoi:

- leggere info e trama;
- vedere la copertina recuperata da AniList;
- aggiungere o rimuovere l'anime dalla watchlist con il pulsante segnalibro;
- aggiungere o rimuovere l'anime dai preferiti con il pulsante cuore;
- scegliere un episodio;
- guardarlo nel browser o aprirlo in MPV/VLC.

## Anime Stagionali

Dal pulsante `Stagionali` nella barra in alto puoi accedere alla pagina dedicata agli anime stagionali per rimanere aggiornati.

In questa pagina puoi:

- scegliere anno e stagione;
- usare le frecce per andare alla stagione precedente o successiva;
- vedere copertina, generi, numero di episodi e `Voto AniList`;
- cliccare un anime per cercarlo nel provider attivo e aprirlo nella normale pagina dettaglio di `aw-web`.

Il provider usato è quello selezionato nella barra in alto, accanto alla ricerca.

## Watchlist, Preferiti e Database

Watchlist, preferiti e progresso vengono salvati in un database SQLite locale dentro:

```text
~/.aw-web/web.sqlite3
```

Nel database vengono salvati:

- anime aggiunti esplicitamente alla watchlist;
- anime aggiunti ai preferiti;
- provider usato;
- ultimo episodio visto;
- copertine cacheate;
- metadati necessari per riaprire gli anime.

ATTENZIONE: in caso di cancellazione del database locale perderete i vostri progressi fatti su questa WebApp.

## Player Browser e MPV/VLC

`aw-web` supporta due modalità di riproduzione.

### Browser

Il player browser prova prima la modalità diretta:

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
