"""Page renderers for the local web interface."""

from __future__ import annotations

import json
from urllib.parse import unquote

from aw_web import providers
from aw_web.anime import Anime
from aw_web.services.anilist import (
    RANKED_LISTS,
    adjacent_season,
    current_season,
    get_cover,
    normalize_season,
    ranked_anime,
    ranked_by_id,
    ranked_list_label,
    seasonal_anime,
    seasonal_by_id,
    seasonal_label,
)
from aw_web.services.matching import best_seasonal_match, seasonal_open_url
from aw_web.services.providers import default_provider_name, get_provider, set_current_provider
from aw_web.web.components import (
    anilist_card,
    card,
    collection_toggle,
    episode_row,
    favorite_card,
    image_html,
    page,
    provider_match_card,
    seasonal_card,
    watch_card,
)
from aw_web.web.state import DB
from aw_web.web.utils import esc, parse_int, provider_error, q
from aw_web.web.watchlist_refresh import refresh_watchlist_availability


HERO_SLIDE_SECONDS = 8
HERO_FADE_SECONDS = 0.8


def redirect(location: str) -> bytes:
    return f"REDIRECT:{location}".encode("utf-8")


def _hero_slideshow(items: list[dict[str, object]]) -> str:
    images: list[str] = []
    for item in items:
        image = str(item.get("banner_url") or item.get("cover_url") or "").strip()
        if image:
            images.append(image)

    if not images:
        return ""

    slides = "".join(
        (
            '<div class="hero-slide" '
            f'style="--slide-image: url(&quot;{esc(image)}&quot;); --slide-delay: {index * HERO_SLIDE_SECONDS}s"'
            f' aria-hidden="true"></div>'
        )
        for index, image in enumerate(images)
    )
    if len(images) == 1:
        return f'<div class="hero-slideshow is-static" aria-hidden="true">{slides}</div>'

    duration = len(images) * HERO_SLIDE_SECONDS
    segment = 100 / len(images)
    fade = min((HERO_FADE_SECONDS / duration) * 100, segment / 3)
    hold_until = max(segment - fade, fade)
    rules = f"""
      <style>
        @keyframes heroSlideshow {{
          0%, 100% {{ opacity: 0; }}
          {fade:.4f}% {{ opacity: 1; }}
          {hold_until:.4f}% {{ opacity: 1; }}
          {segment:.4f}% {{ opacity: 0; }}
        }}
      </style>
    """
    return (
        f'{rules}<div class="hero-slideshow" aria-hidden="true" '
        f'style="--slideshow-duration: {duration}s">{slides}</div>'
    )


def render_home() -> bytes:
    provider_name = default_provider_name()
    provider = get_provider(provider_name)
    latest: list[Anime] = []
    try:
        latest = provider.latest("a")[:36]
        latest_html = "".join(card(anime, provider_name, "Nuovo") for anime in latest)
    except Exception as exc:
        latest_html = f'<p class="error">Impossibile caricare gli ultimi episodi: {esc(provider_error(exc))}</p>'

    watch_items = [
        item for item in DB.watchlist()
        if str(item.get("provider") or "") in providers.PROVIDERS_AVAILABLE
    ]
    refresh_watchlist_availability(DB, watch_items, provider_factory=get_provider)
    watch_items = [
        item for item in DB.watchlist()
        if str(item.get("provider") or "") in providers.PROVIDERS_AVAILABLE
    ]
    watch_html = "".join(watch_card(item, latest) for item in watch_items)
    if not watch_html:
        watch_html = '<p class="muted">La watchlist è vuota. Cerca un anime e aggiungilo.</p>'

    favorite_items = [
        item for item in DB.favorites()
        if str(item.get("provider") or "") in providers.PROVIDERS_AVAILABLE
    ]
    favorites_html = "".join(favorite_card(item) for item in favorite_items)
    if not favorites_html:
        favorites_html = '<p class="muted">Nessun preferito salvato.</p>'

    hero_slideshow = _hero_slideshow(watch_items)

    body = f"""
    <section class="hero">
      {hero_slideshow}
      <div class="hero-copy">
        <p class="eyebrow">aw-web streaming locale</p>
        <h1>La tua libreria anime, pronta per MPV.</h1>
        <p>Riprendi la watchlist, esplora gli ultimi episodi e apri gli episodi nel player esterno.</p>
      </div>
    </section>
    <section id="watchlist" class="catalog-section">
      <div class="section-title"><h2>La tua watchlist</h2></div>
      <div class="rail">{watch_html}</div>
    </section>
    <section class="catalog-section">
      <div class="section-title"><h2>Preferiti</h2></div>
      <div class="rail">{favorites_html}</div>
    </section>
    <section class="catalog-section">
      <div class="section-title"><h2>Ultimi episodi</h2></div>
      <div class="rail">{latest_html}</div>
    </section>
    """
    return page("Home", body)


def render_search(params: dict[str, list[str]]) -> bytes:
    term = params.get("q", [""])[0].strip()
    provider_name = params.get("provider", [default_provider_name()])[0]
    if provider_name not in providers.PROVIDERS_AVAILABLE:
        provider_name = default_provider_name()
    set_current_provider(provider_name)
    if not term:
        return redirect("/")

    try:
        results = get_provider(provider_name).search(term)
        results_html = "".join(card(anime, provider_name) for anime in results)
        if not results_html:
            results_html = '<p class="muted">Nessun risultato trovato.</p>'
    except Exception as exc:
        results_html = f'<p class="error">Errore ricerca: {esc(provider_error(exc))}</p>'

    body = f"""
    <section class="catalog-section">
      <div class="section-title"><h2>Risultati per "{esc(term)}"</h2><span>{esc(provider_name)}</span></div>
      <div class="grid">{results_html}</div>
    </section>
    """
    return page("Ricerca", body)


def render_seasonal(params: dict[str, list[str]]) -> bytes:
    default_year, default_season = current_season()
    try:
        year = int(params.get("year", [str(default_year)])[0] or default_year)
    except ValueError:
        year = default_year
    season = normalize_season(params.get("season", [default_season])[0])

    prev_year, prev_season = adjacent_season(year, season, -1)
    next_year, next_season = adjacent_season(year, season, 1)
    options = "".join(
        f'<option value="{esc(value)}" {"selected" if value == season else ""}>{esc(seasonal_label(value))}</option>'
        for value in ("WINTER", "SPRING", "SUMMER", "FALL")
    )
    try:
        items = seasonal_anime(year, season)
        grid = "".join(seasonal_card(item, year, season) for item in items)
        if not grid:
            grid = '<p class="muted">Nessun anime stagionale trovato.</p>'
    except Exception as exc:
        grid = f'<p class="error">Impossibile caricare gli anime stagionali: {esc(provider_error(exc))}</p>'

    body = f"""
    <section class="catalog-section">
      <div class="season-toolbar">
        <div class="season-heading">
          <p class="eyebrow">Anime stagionali</p>
          <h1>{esc(seasonal_label(season))} {esc(year)}</h1>
          <p class="muted">Scegli una stagione e consultane le uscite.</p>
        </div>
        <div class="season-picker">
          <a class="button secondary season-arrow" href="/stagionali?year={q(prev_year)}&season={q(prev_season)}" aria-label="Stagione precedente">&#8592;</a>
          <a class="button secondary season-arrow" href="/stagionali?year={q(next_year)}&season={q(next_season)}" aria-label="Stagione successiva">&#8594;</a>
        </div>
      </div>
      <form class="season-controls" action="/stagionali" method="get">
        <input type="number" name="year" min="1960" max="2100" value="{esc(year)}" aria-label="Anno">
        <select name="season" aria-label="Stagione">{options}</select>
        <button>Vai</button>
      </form>
      <div class="grid">{grid}</div>
    </section>
    """
    return page(f"Stagionali - {seasonal_label(season)} {year}", body)


def render_seasonal_open(params: dict[str, list[str]]) -> bytes:
    default_year, default_season = current_season()
    provider_name = default_provider_name()
    try:
        year = int(params.get("year", [str(default_year)])[0] or default_year)
        anilist_id = parse_int(params.get("anilist_id", ["0"])[0])
    except ValueError:
        return page("Stagionali", '<p class="error">Richiesta stagionale non valida.</p>')
    season = normalize_season(params.get("season", [default_season])[0])
    item = seasonal_by_id(year, season, anilist_id)
    if not item:
        return page("Stagionali", '<p class="error">Anime stagionale non trovato.</p>')

    try:
        match, candidates = best_seasonal_match(provider_name, item)
    except Exception as exc:
        return page("Stagionali", f'<p class="error">Errore ricerca provider: {esc(provider_error(exc))}</p>')

    if match:
        return redirect(seasonal_open_url(provider_name, match))

    back_url = f"/stagionali?year={q(year)}&season={q(season)}"
    candidates_html = "".join(provider_match_card(anime, provider_name) for anime in candidates)
    if not candidates_html:
        candidates_html = f'<p class="muted">Non ho trovato "{esc(item.title)}" su {esc(provider_name)}.</p>'

    body = f"""
    <section>
      <div class="section-title">
        <h2>Risultati possibili</h2>
        <a class="button secondary" href="{back_url}">Torna agli stagionali</a>
      </div>
      <p class="muted">Non c'e un match abbastanza sicuro per {esc(item.title)}. Scegli manualmente un risultato.</p>
      <div class="grid">{candidates_html}</div>
    </section>
    """
    return page(f"Scegli risultato - {item.title}", body)


def render_anilist_ranking(source: str) -> bytes:
    source = source if source in RANKED_LISTS else "popolari"
    config = RANKED_LISTS[source]
    title = str(config["title"])
    try:
        items = ranked_anime(source)
        grid = "".join(anilist_card(item, source, title) for item in items)
        if not grid:
            grid = '<p class="muted">Nessun anime trovato.</p>'
    except Exception as exc:
        grid = f'<p class="error">Impossibile caricare {esc(title)}: {esc(provider_error(exc))}</p>'

    body = f"""
    <section class="catalog-section">
      <div class="season-toolbar">
        <div class="season-heading">
          <p class="eyebrow">{esc(config["eyebrow"])}</p>
          <h1>{esc(title)}</h1>
          <p class="muted">{esc(config["description"])}</p>
        </div>
      </div>
      <div class="grid">{grid}</div>
    </section>
    """
    return page(title, body)


def render_anilist_open(params: dict[str, list[str]]) -> bytes:
    source = params.get("source", ["popolari"])[0]
    if source not in RANKED_LISTS:
        source = "popolari"
    provider_name = default_provider_name()
    try:
        anilist_id = parse_int(params.get("anilist_id", ["0"])[0])
    except ValueError:
        return page(ranked_list_label(source), '<p class="error">Richiesta AniList non valida.</p>')

    item = ranked_by_id(source, anilist_id)
    if not item:
        return page(ranked_list_label(source), '<p class="error">Anime AniList non trovato.</p>')

    try:
        match, candidates = best_seasonal_match(provider_name, item)
    except Exception as exc:
        return page(ranked_list_label(source), f'<p class="error">Errore ricerca provider: {esc(provider_error(exc))}</p>')

    if match:
        return redirect(seasonal_open_url(provider_name, match))

    back_url = f"/{q(source)}"
    candidates_html = "".join(provider_match_card(anime, provider_name) for anime in candidates)
    if not candidates_html:
        candidates_html = f'<p class="muted">Non ho trovato "{esc(item.title)}" su {esc(provider_name)}.</p>'

    body = f"""
    <section>
      <div class="section-title">
        <h2>Risultati possibili</h2>
        <a class="button secondary" href="{back_url}">Torna a {esc(ranked_list_label(source))}</a>
      </div>
      <p class="muted">Non c'e un match abbastanza sicuro per {esc(item.title)}. Scegli manualmente un risultato.</p>
      <div class="grid">{candidates_html}</div>
    </section>
    """
    return page(f"Scegli risultato - {item.title}", body)


def render_anime(params: dict[str, list[str]]) -> bytes:
    provider_name = params.get("provider", [default_provider_name()])[0]
    if provider_name not in providers.PROVIDERS_AVAILABLE:
        provider_name = default_provider_name()

    saved = params.get("saved", [""])[0] == "1"
    if saved:
        ref = unquote(params.get("ref", [""])[0])
        item = DB.find_watch_item(provider_name, ref) or DB.find_favorite_item(provider_name, ref) or DB.find_history_item(provider_name, ref)
        if not item:
            return page("Non trovato", '<p class="error">Anime non trovato.</p>')
        anime = Anime.from_dict(json.loads(str(item["anime_json"])))
    else:
        anime = Anime(
            name=unquote(params.get("name", [""])[0]),
            ref=unquote(params.get("ref", [""])[0]),
            curr_ep=unquote(params.get("curr_ep", ["0"])[0]),
            last_ep=unquote(params.get("last_ep", ["0"])[0]),
        )
        anilist_id = parse_int(params.get("anilist_id", ["0"])[0])
        if anilist_id:
            anime.anilist_id = anilist_id

    provider = get_provider(provider_name)
    info_error = ""
    episodes_error = ""
    try:
        provider.info_anime(anime)
    except Exception as exc:
        info_error = provider_error(exc)
    try:
        if saved or not anime.episodes() or not anime.has_all_episodes():
            provider.episodes(anime)
    except Exception as exc:
        episodes_error = provider_error(exc)

    cover = get_cover(anime.anilist_id, anime.name)
    watch_item = DB.find_watch_item(provider_name, anime.ref)
    favorite_item = DB.find_favorite_item(provider_name, anime.ref)
    history_item = DB.find_history_item(provider_name, anime.ref)
    current_episode = str((history_item or watch_item or {}).get("current_episode") or "0")
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
        <p class="muted">Stato: {esc(anime.status.value)} &middot; Ultimo visto: {esc(current_episode)} &middot; Totale: {esc(anime.last_ep)}</p>
        <div class="row-actions">
          {collection_toggle(action="/watchlist/toggle", provider_name=provider_name, anime=anime, cover_url=cover['cover_url'], banner_url=cover['banner_url'], active=bool(watch_item), kind="watchlist", label="Rimuovi dalla watchlist" if watch_item else "Aggiungi alla watchlist")}
          {collection_toggle(action="/favorites/toggle", provider_name=provider_name, anime=anime, cover_url=cover['cover_url'], banner_url=cover['banner_url'], active=bool(favorite_item), kind="favorite", label="Rimuovi dai preferiti" if favorite_item else "Aggiungi ai preferiti")}
        </div>
        {f'<p class="plot">{esc(plot)}</p>' if plot else ''}
        <dl class="info-list">{info_rows}</dl>
      </div>
    </section>
    <section>
      <div class="section-title"><h2>Episodi</h2></div>
      <div class="episodes">{episodes_html}</div>
    </section>
    """
    return page(anime.name, body)
