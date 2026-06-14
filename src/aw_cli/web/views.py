"""Page renderers for the local web interface."""

from __future__ import annotations

import json
from urllib.parse import unquote

from aw_cli import providers
from aw_cli.anime import Anime
from aw_cli.web.components import card, episode_row, image_html, page, token_play_form, watch_card
from aw_cli.web.services import DB, default_provider_name, get_cover, get_provider, resolve_episode_url, stream_context
from aw_cli.web.utils import anime_to_json, esc, provider_error, q


def redirect(location: str) -> bytes:
    return f"REDIRECT:{location}".encode("utf-8")


def render_home() -> bytes:
    provider_name = default_provider_name()
    provider = get_provider(provider_name)
    latest: list[Anime] = []
    try:
        latest = provider.latest("a")[:36]
        latest_html = "".join(card(anime, provider_name, "Nuovo") for anime in latest)
    except (Exception, SystemExit) as exc:
        latest_html = f'<p class="error">Impossibile caricare gli ultimi episodi: {esc(provider_error(exc))}</p>'

    watch_items = DB.watchlist()
    watch_html = "".join(watch_card(item, latest) for item in watch_items)
    if not watch_html:
        watch_html = '<p class="muted">La watchlist e vuota. Cerca un anime e aggiungilo.</p>'

    body = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">Interfaccia locale</p>
        <h1>Guarda anime con la comodita del browser, usando aw-cli sotto il cofano.</h1>
        <p>Apri dettagli, salva la tua watchlist e lancia gli episodi in MPV/VLC.</p>
      </div>
    </section>
    <section>
      <div class="section-title"><h2>La tua watchlist</h2></div>
      <div class="grid">{watch_html}</div>
    </section>
    <section>
      <div class="section-title"><h2>Ultimi episodi</h2><span>{esc(provider_name)}</span></div>
      <div class="grid">{latest_html}</div>
    </section>
    """
    return page("Home", body)


def render_search(params: dict[str, list[str]]) -> bytes:
    term = params.get("q", [""])[0].strip()
    provider_name = params.get("provider", [default_provider_name()])[0]
    if provider_name not in providers.PROVIDERS_AVAILABLE:
        provider_name = default_provider_name()
    if not term:
        return redirect("/")

    try:
        results = get_provider(provider_name).search(term)
        results_html = "".join(card(anime, provider_name) for anime in results)
        if not results_html:
            results_html = '<p class="muted">Nessun risultato trovato.</p>'
    except (Exception, SystemExit) as exc:
        results_html = f'<p class="error">Errore ricerca: {esc(provider_error(exc))}</p>'

    body = f"""
    <section>
      <div class="section-title"><h2>Risultati per "{esc(term)}"</h2><span>{esc(provider_name)}</span></div>
      <div class="grid">{results_html}</div>
    </section>
    """
    return page("Ricerca", body)


def render_anime(params: dict[str, list[str]]) -> bytes:
    provider_name = params.get("provider", [default_provider_name()])[0]
    if provider_name not in providers.PROVIDERS_AVAILABLE:
        provider_name = default_provider_name()

    saved = params.get("saved", [""])[0] == "1"
    if saved:
        item = DB.find_watch_item(provider_name, unquote(params.get("ref", [""])[0]))
        if not item:
            return page("Non trovato", '<p class="error">Anime non trovato in watchlist.</p>')
        anime = Anime.from_dict(json.loads(str(item["anime_json"])))
    else:
        anime = Anime(
            name=unquote(params.get("name", [""])[0]),
            ref=unquote(params.get("ref", [""])[0]),
            curr_ep=unquote(params.get("curr_ep", ["0"])[0]),
            last_ep=unquote(params.get("last_ep", ["0"])[0]),
        )
        anilist_id = int(params.get("anilist_id", ["0"])[0] or 0)
        if anilist_id:
            anime.anilist_id = anilist_id

    provider = get_provider(provider_name)
    info_error = ""
    episodes_error = ""
    try:
        provider.info_anime(anime)
    except (Exception, SystemExit) as exc:
        info_error = provider_error(exc)
    try:
        if not anime.episodes() or not anime.has_all_episodes():
            provider.episodes(anime)
    except (Exception, SystemExit) as exc:
        episodes_error = provider_error(exc)

    cover = get_cover(anime.anilist_id, anime.name)
    item = DB.find_watch_item(provider_name, anime.ref)
    current_episode = str(item["current_episode"]) if item else anime.curr_ep
    info_rows = "".join(
        f"<dt>{esc(key)}</dt><dd>{esc(value)}</dd>"
        for key, value in anime.info.items()
        if value and key != "Trama"
    )
    plot = anime.info.get("Trama", "")
    episodes_html = "".join(episode_row(provider_name, anime, ep, current_episode) for ep in anime._episodes)
    if not episodes_html:
        message = episodes_error or "Nessun episodio disponibile."
        episodes_html = f'<p class="muted">{esc(message)}</p>'
    warnings = "".join(
        f'<p class="error">{esc(message)}</p>'
        for message in (info_error, episodes_error)
        if message
    )

    body = f"""
    <section class="detail">
      <div class="poster-wrap">{image_html(cover['cover_url'], anime.name)}</div>
      <div class="detail-main">
        {warnings}
        <p class="eyebrow">{esc(provider_name)}</p>
        <h1>{esc(anime.name)}</h1>
        <p class="muted">Stato: {esc(anime.status.value)} &middot; Episodio corrente: {esc(current_episode)} &middot; Totale: {esc(anime.last_ep)}</p>
        <div class="row-actions">
          <form action="/watchlist/add" method="post">
            <input type="hidden" name="provider" value="{esc(provider_name)}">
            <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
            <input type="hidden" name="cover_url" value="{esc(cover['cover_url'])}">
            <input type="hidden" name="banner_url" value="{esc(cover['banner_url'])}">
            <button>{'Aggiorna watchlist' if item else 'Aggiungi alla watchlist'}</button>
          </form>
          <a class="button secondary" href="/">Home</a>
        </div>
        {f'<p class="plot">{esc(plot)}</p>' if plot else ''}
        <dl class="info-list">{info_rows}</dl>
      </div>
    </section>
    <section>
      <div class="section-title"><h2>Episodi</h2><span>MPV/VLC esterno</span></div>
      <div class="episodes">{episodes_html}</div>
    </section>
    """
    return page(anime.name, body)


def render_watch(params: dict[str, list[str]]) -> bytes:
    token = params.get("token", [""])[0]
    try:
        provider_name, anime, episode = stream_context(token)
    except Exception as exc:
        return page("Player", f'<p class="error">{esc(exc)}</p><p><a href="/">Torna alla home</a></p>')

    progress = DB.get_episode_progress(provider_name, anime.ref, episode.num) or {}
    resume_at = int(progress.get("progress_seconds") or 0)
    back_url = f"/anime?saved=1&provider={q(provider_name)}&ref={q(anime.ref)}"
    direct_url = ""
    direct_error = ""
    try:
        direct_url, _ = resolve_episode_url(token)
    except Exception as exc:
        direct_error = provider_error(exc)
    body = f"""
    <section class="watch-page">
      <div class="section-title"><h2>{esc(anime.name)} - Ep. {esc(episode.num)}</h2><span>Player browser</span></div>
      {f'<p class="error">{esc(direct_error)}</p>' if direct_error else ''}
      <div class="video-shell">
        <div id="playback-mode" class="mode-pill mode-direct"><span></span>Diretto</div>
        <video id="player" class="video-player" controls autoplay playsinline preload="metadata"></video>
      </div>
      <div class="row-actions">
        {token_play_form(token, 'Apri in MPV/VLC')}
        <a class="button secondary" href="{back_url}">Torna agli episodi</a>
      </div>
      <p id="player-status" class="muted">Avvio in modalita browser diretta. Se non funziona, passo automaticamente al proxy locale.</p>
    </section>
    <script>
      const video = document.getElementById('player');
      const status = document.getElementById('player-status');
      const mode = document.getElementById('playback-mode');
      const resumeAt = {resume_at};
      const directUrl = {json.dumps(direct_url)};
      const proxyUrl = '/stream?token={esc(token)}';
      let restored = false;
      let lastSavedAt = -1;
      let usingProxy = false;
      let pendingResumeAt = 0;
      function setMode(kind, label) {{
        if (!mode) return;
        mode.className = 'mode-pill mode-' + kind;
        mode.innerHTML = '<span></span>' + label;
      }}
      function saveProgress(completed = false) {{
        if (!video || Number.isNaN(video.currentTime)) return;
        const currentSecond = Math.floor(video.currentTime || 0);
        if (!completed && currentSecond === lastSavedAt) return;
        lastSavedAt = currentSecond;
        const body = new URLSearchParams({{
          token: {json.dumps(token)},
          seconds: String(currentSecond),
          completed: completed ? '1' : '0'
        }});
        fetch('/progress', {{ method: 'POST', body, keepalive: true }}).catch(() => {{}});
      }}
      function useProxy() {{
        if (usingProxy) return;
        usingProxy = true;
        restored = false;
        pendingResumeAt = Math.max(video.currentTime || 0, resumeAt || 0);
        setMode('proxy', 'Proxy fallback');
        if (status) status.textContent = 'Link diretto non riproducibile dal browser: uso il proxy locale aw-web.';
        video.src = proxyUrl;
        video.load();
        video.play().catch(() => {{}});
      }}
      video.addEventListener('loadedmetadata', () => {{
        const target = pendingResumeAt || resumeAt;
        if (!restored && target > 5 && target < video.duration - 10) {{
          video.currentTime = target;
        }}
        restored = true;
      }});
      video.addEventListener('playing', () => {{
        setMode(usingProxy ? 'proxy' : 'direct', usingProxy ? 'Proxy fallback' : 'Diretto');
      }});
      video.addEventListener('waiting', () => {{
        setMode('buffering', usingProxy ? 'Buffering proxy' : 'Buffering');
      }});
      video.addEventListener('timeupdate', () => {{
        if (Math.floor(video.currentTime) % 30 === 0) saveProgress(false);
      }});
      video.addEventListener('error', () => {{
        if (usingProxy) {{
          setMode('error', 'Errore video');
          if (status) status.textContent = 'Errore durante la riproduzione anche con proxy locale. Prova MPV/VLC.';
          return;
        }}
        useProxy();
      }});
      video.addEventListener('stalled', () => {{
        setMode('buffering', usingProxy ? 'Buffering proxy' : 'Buffering');
      }});
      video.addEventListener('pause', () => saveProgress(false));
      video.addEventListener('ended', () => saveProgress(true));
      window.addEventListener('beforeunload', () => saveProgress(false));
      if (directUrl) {{
        setMode('direct', 'Diretto');
        video.src = directUrl;
      }} else {{
        useProxy();
      }}
    </script>
    """
    return page(f"Player - {anime.name}", body)
