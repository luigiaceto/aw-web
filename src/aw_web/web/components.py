"""Reusable HTML components for the local web interface."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote, urlencode

from aw_web.anilist import SeasonalAnime
from aw_web.anime import Anime, AnimeStatus, anime_to_json, episode_overview, episode_value
from aw_web.db import saved_anime
from aw_web.web import CSRF_TOKEN


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def q(value: object) -> str:
    return quote(str(value), safe="")


def anime_url(anime: Anime, *, saved: bool = False) -> str:
    """Link alla pagina dettaglio: il resto lo carica la pagina da AnimeUnity."""
    query = urlencode({"name": anime.name, "ref": anime.ref})
    return f"/anime?saved=1&{query}" if saved else f"/anime?{query}"


def csrf_input() -> str:
    return f'<input type="hidden" name="csrf_token" value="{esc(CSRF_TOKEN)}">'


def page(title: str, body: str) -> bytes:
    html_doc = f"""
    <!doctype html>
    <html lang="it">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="icon" href="/favicon.ico?v=1" sizes="any">
      <title>{esc(title)} - aw-web</title>
      <link rel="stylesheet" href="/static/style.css">
      <script src="/static/app.js" defer></script>
    </head>
    <body>
      <header class="topbar">
        <nav class="main-nav" aria-label="Navigazione principale">
          <a class="brand" href="/"><span class="brand-mark">aw</span><span>web</span></a>
          <a class="nav-link" href="/">Home</a>
          <a class="nav-link" href="/stagionali">Stagionali</a>
          <a class="nav-link" href="/popolari">Popolari</a>
          <a class="nav-link" href="/top-100">Top 100</a>
        </nav>
        <form class="search" action="/search" method="get">
          <input type="search" name="q" placeholder="Cerca anime..." autocomplete="off" required>
          <button aria-label="Cerca">{_search_icon()}<span class="button-text">Cerca</span></button>
        </form>
      </header>
      <main>{body}</main>
    </body>
    </html>
    """
    return html_doc.encode("utf-8")


def image_html(url: str, alt: str) -> str:
    if url:
        return f'<img class="cover" src="{esc(url)}" alt="Copertina {esc(alt)}" loading="lazy">'
    initials = "".join(part[:1] for part in alt.split()[:2]).upper() or "AW"
    return f'<div class="cover placeholder"><span>{esc(initials)}</span></div>'


def _decorative_card_image(image: str) -> str:
    if image.startswith('<img class="cover" '):
        return image.replace('alt="', 'aria-hidden="true" alt="', 1)
    return image


def _short_text(value: str, *, limit: int = 190) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rsplit(" ", 1)[0] + "..."


def _anime_description(anime: Anime) -> str:
    return _short_text(str(anime.info.get("Trama", "")))


def _meta_text(parts: list[str]) -> str:
    return " | ".join(part for part in parts if part)


def _pill(label: str, class_name: str = "") -> str:
    classes = f"badge {class_name}".strip()
    return f'<span class="{classes}">{esc(label)}</span>'


def _remove_form(action: str, ref: str, label: str) -> str:
    return f"""
    <form action="{esc(action)}" method="post">
      {csrf_input()}
      <input type="hidden" name="ref" value="{esc(ref)}">
      <button class="secondary danger card-icon-action" type="submit" aria-label="{esc(label)}" title="{esc(label)}">
        {_trash_icon()}
      </button>
    </form>
    """


def _play_form_action(anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/play" method="post">
      {csrf_input()}
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button class="card-action play-action" type="submit">{_play_icon()}<span>{esc(label)}</span></button>
    </form>
    """


def _catalog_card(
    *,
    title: str,
    href: str,
    image: str,
    badges: str,
    meta: str,
    description: str = "",
    actions: str = "",
    class_name: str = "",
) -> str:
    description_html = (
        f'<p class="hover-description">{esc(description)}</p>'
        if description
        else '<p class="hover-description muted">Apri la scheda per maggiori dettagli.</p>'
    )
    return f"""
    <article class="catalog-card {esc(class_name)}">
      <a class="card-detail-link" href="{esc(href)}" aria-label="{esc(title)}"></a>
      <div class="card-backdrop" aria-hidden="true">{_decorative_card_image(image)}</div>
      <div class="poster-frame">{image}</div>
      <div class="card-info">
        <div class="badge-row">{badges}</div>
        <h3>{esc(title)}</h3>
      </div>
      <div class="card-hover">
        <div class="hover-copy">
          <div class="badge-row">{badges}</div>
          <h3>{esc(title)}</h3>
          <p class="hover-meta">{esc(meta) if meta else "Scheda anime"}</p>
          {description_html}
        </div>
        {f'<div class="hover-actions">{actions}</div>' if actions else ""}
      </div>
    </article>
    """


def card(anime: Anime, badge: str = "") -> str:
    image = image_html(anime.cover_url, anime.name)
    href = anime_url(anime)
    info = []
    if anime.curr_ep and anime.curr_ep != "0":
        info.append(f"Ep. {anime.curr_ep}")
    if anime.status != AnimeStatus.UNKNOWN:
        info.append(anime.status.value)
    actions = ""
    if badge == "Nuovo" and anime.curr_ep and anime.curr_ep != "0":
        actions = _play_form_action(anime, anime.curr_ep, f"Guarda episodio {anime.curr_ep}")
    return _catalog_card(
        title=anime.name,
        href=href,
        image=image,
        badges=_pill(badge) if badge else "",
        meta=_meta_text(info),
        description=_anime_description(anime),
        actions=actions,
    )


def _anilist_meta(item: SeasonalAnime) -> str:
    return _meta_text(
        [
            ", ".join(item.genres),
            f"{item.episodes} ep." if item.episodes else "",
            f"Voto AniList {item.average_score}%" if item.average_score else "",
        ]
    )


def seasonal_card(item: SeasonalAnime, year: int, season: str) -> str:
    href = f"/stagionali/apri?year={q(year)}&season={q(season)}&anilist_id={q(item.anilist_id)}"
    return _catalog_card(
        title=item.title,
        href=href,
        image=image_html(item.cover_url, item.title),
        badges=_pill("Stagionale"),
        meta=_anilist_meta(item),
        class_name="seasonal-card",
    )


def anilist_card(item: SeasonalAnime, source: str, badge: str) -> str:
    href = f"/anilist/apri?source={q(source)}&anilist_id={q(item.anilist_id)}"
    return _catalog_card(
        title=item.title,
        href=href,
        image=image_html(item.cover_url, item.title),
        badges=_pill(badge),
        meta=_anilist_meta(item),
        class_name="seasonal-card anilist-card",
    )


def provider_match_card(anime: Anime) -> str:
    href = anime_url(anime)
    return _catalog_card(
        title=anime.name,
        href=href,
        image=image_html(anime.cover_url, anime.name),
        badges=_pill("AnimeUnity"),
        meta=f"Ep. {anime.curr_ep or '0'} / {anime.last_ep or '0'}",
        description=_anime_description(anime),
    )


def collection_toggle(
    *,
    action: str,
    anime: Anime,
    active: bool,
    kind: str,
    label: str,
) -> str:
    icon = _bookmark_icon(active) if kind == "watchlist" else _heart_icon(active)
    return f"""
    <form class="icon-toggle-form" action="{esc(action)}" method="post">
      {csrf_input()}
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <button class="icon-toggle {"active" if active else ""}" type="submit" aria-label="{esc(label)}" title="{esc(label)}">
        {icon}
      </button>
    </form>
    """


def _play_icon() -> str:
    return """
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 5.5v13l11-6.5-11-6.5Z" fill="currentColor"/>
    </svg>
    """


def _trash_icon() -> str:
    return """
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 3h6l1 2h4v2H4V5h4l1-2Z" fill="currentColor"/>
      <path d="M6.5 9h11l-.7 10.2A2 2 0 0 1 14.8 21H9.2a2 2 0 0 1-2-1.8L6.5 9Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
    </svg>
    """


def _search_icon() -> str:
    return """
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/>
      <path d="m16 16 4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
    """


def _bookmark_icon(active: bool) -> str:
    fill = "currentColor" if active else "none"
    return f"""
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4.75A2.75 2.75 0 0 1 8.75 2h6.5A2.75 2.75 0 0 1 18 4.75V21l-6-3.6L6 21V4.75Z" fill="{fill}" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
    </svg>
    """


def _heart_icon(active: bool) -> str:
    fill = "currentColor" if active else "none"
    return f"""
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z" fill="{fill}" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
    </svg>
    """


def favorite_card(item: dict[str, Any]) -> str:
    anime = saved_anime(item)
    return _catalog_card(
        title=anime.name,
        href=anime_url(anime),
        image=image_html(anime.cover_url, anime.name),
        badges=_pill("Preferito"),
        meta=_meta_text([anime.status.value, f"Ep. {item['current_episode']} / {anime.last_ep}"]),
        description=_anime_description(anime),
        actions=_remove_form("/favorites/remove", anime.ref, "Rimuovi dai preferiti"),
        class_name="saved-card favorite-card",
    )


def watch_card(item: dict[str, Any], latest: list[Anime]) -> str:
    anime = saved_anime(item)
    current_episode = str(item["current_episode"])
    last_episode, playable_episode = episode_overview(anime, current_episode, latest)
    badges = _pill("Watchlist")
    if episode_value(last_episode) > episode_value(current_episode):
        badges += _pill("Nuovo episodio", "new-episode")
    actions = _play_form_action(
        anime, playable_episode, "Inizia" if current_episode == "0" else "Riprendi"
    ) + _remove_form("/watchlist/remove", anime.ref, "Rimuovi dalla watchlist")
    return _catalog_card(
        title=anime.name,
        href=anime_url(anime, saved=True),
        image=image_html(anime.cover_url, anime.name),
        badges=badges,
        meta=_meta_text([f"Ep. {current_episode} / {last_episode}", anime.status.value]),
        description=_anime_description(anime),
        actions=actions,
        class_name="saved-card watch-card",
    )


def episode_play_form(anime: Anime) -> str:
    """Un solo form per pagina: i bottoni degli episodi lo usano con l'attributo form."""
    return f"""
    <form id="play-form" action="/play" method="post" hidden>
      {csrf_input()}
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
    </form>
    """


def episode_row(episode: Anime.Episode, current_episode: str) -> str:
    active = " active" if current_episode != "0" and episode.num == current_episode else ""
    return f"""
    <div class="episode{active}">
      <div>
        <strong>Ep. {esc(episode.num)}</strong>
        {('<span class="badge">ultimo visto</span>' if active else "")}
      </div>
      <div class="row-actions compact">
        <button form="play-form" name="episode" value="{esc(episode.num)}">Guarda</button>
      </div>
    </div>
    """
