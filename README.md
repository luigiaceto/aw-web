# aw-web

Interfaccia web locale per navigare e guardare anime senza pubblicità o pop-up. Include funzionalità come: ricerca anime, ultimi episodi, watchlist, preferiti, anime stagionali.

<img width="1393" height="878" alt="Screenshot 2026-07-01 alle 15 35 44" src="https://github.com/user-attachments/assets/ac815b87-c940-401d-b2bb-99fa778181ce" />

<img width="1395" height="877" alt="Screenshot 2026-07-01 alle 15 35 54" src="https://github.com/user-attachments/assets/711fb998-574a-437c-ae14-8bcfd959fc3c" />

## Indice

- [Installazione](#installazione-su-macos-unico-os-supportato-e-testato-attualmente)
- [Avvio](#avvio)
- [Utilizzo](#utilizzo)
- [Anime Stagionali](#anime-stagionali)
- [Watchlist, Preferiti e Database](#watchlist-preferiti-e-database)
- [Player MPV](#player-mpv)

## Installazione su MacOS (unico OS supportato e testato attualmente)

La guida d'installazione richiede [uv](https://github.com/astral-sh/uv) e [MPV](https://mpv.io/installation/).

Su macOS puoi installare `uv` e `mpv` tramite [Homebrew](https://brew.sh/) con:

```bash
brew install uv mpv
```

Dopo l'installazione di `uv` potrebbe essere necessario aggiornare la shell. Dunque fare:

```bash
uv tool update-shell
```

```bash
exec zsh
```

Puoi installare `aw-web` direttamente da questa repository GitHub tramite `uv`:

```bash
uv python install 3.13
```

```bash
uv tool install --managed-python --python 3.13 git+https://github.com/luigiaceto/aw-web.git
```

il primo comando installa python 3.13 dentro `uv` in modo da non interferire con altre installazioni python di sistema, mentre il secondo comando installa la WebApp come tool globale in un ambiente isolato.

## Come Aggiornare l'App

Per aggiornare `aw-web` all'ultima versione della repository, eseguire il comando:

```bash
uv tool install --force --managed-python --python 3.13 git+https://github.com/luigiaceto/aw-web.git
```

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
- aprirlo in MPV.

## Anime Stagionali

Dal pulsante `Stagionali` nella barra in alto puoi accedere alla pagina dedicata agli anime stagionali per rimanere aggiornati.

In questa pagina puoi:

- scegliere anno e stagione;
- usare le frecce per andare alla stagione precedente o successiva;
- vedere copertina, generi, numero di episodi e `Voto AniList`;
- cliccare un anime per cercarlo su AnimeUnity e aprirlo nella normale pagina dettaglio di `aw-web`.

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

## Player MPV

`aw-web` usa il browser come interfaccia e MPV come player video.

Quando clicchi `Guarda`, la WebApp risolve il link dell'episodio e apre MPV direttamente:

```text
aw-web -> MPV -> server video
```

Se MPV non viene trovato automaticamente, puoi indicare il percorso dell'eseguibile con:

```bash
AW_WEB_MPV_PATH=/percorso/a/mpv aw-web
```

Su macOS installato con Homebrew, aw-web controlla anche `/opt/homebrew/bin/mpv` e `/usr/local/bin/mpv`.
