"""Reusable HTML components for the local web interface."""

from __future__ import annotations

import json
from typing import Any

from aw_web.anime import Anime
from aw_web.web.services import default_provider_name, get_cover
from aw_web.web.state import CSRF_TOKEN
from aw_web.web.styles import CSS
from aw_web.web.utils import anime_to_json, available_last_episode, esc, has_new_episode, q


def csrf_input() -> str:
    return f'<input type="hidden" name="csrf_token" value="{esc(CSRF_TOKEN)}">'


def page(title: str, body: str) -> bytes:
    provider = default_provider_name()
    html_doc = f"""
    <!doctype html>
    <html lang="it">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{esc(title)} - aw-web</title>
      <style>{CSS}</style>
    </head>
    <body>
      <header class="topbar">
        <nav class="main-nav" aria-label="Navigazione principale">
          <a class="brand" href="/">aw-web</a>
          <a class="nav-link" href="/stagionali">Stagionali</a>
        </nav>
        <form class="search" action="/search" method="get">
          <input type="search" name="q" placeholder="Cerca anime..." autocomplete="off" required>
          <select name="provider" id="provider-select" onchange="fetch('/set-provider', {{method: 'POST', headers: {{'Content-Type': 'application/x-www-form-urlencoded'}}, body: new URLSearchParams({{name: this.value, csrf_token: '{esc(CSRF_TOKEN)}'}})}})">
            <option value="animeunity" {'selected' if provider == 'animeunity' else ''}>AnimeUnity</option>
            <option value="animeworld" {'selected' if provider == 'animeworld' else ''}>AnimeWorld</option>
          </select>
          <button>Cerca</button>
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


def card(anime: Anime, provider_name: str, badge: str = "") -> str:
    cover = get_cover(anime.anilist_id, anime.name, allow_title_lookup=False)
    image = image_html(cover["cover_url"], anime.name)
    href = (
        f"/anime?provider={q(provider_name)}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )
    info = []
    if anime.curr_ep and anime.curr_ep != "0":
        info.append(f"Ep. {esc(anime.curr_ep)}")
    if anime.status.value != "Sconosciuto":
        info.append(esc(anime.status.value))
    return f"""
    <a class="card" href="{href}">
      {image}
      <div class="card-body">
        {f'<span class="badge">{esc(badge)}</span>' if badge else ''}
        <h3>{esc(anime.name)}</h3>
        <p>{' &middot; '.join(info) or 'Apri dettagli'}</p>
      </div>
    </a>
    """


def seasonal_card(item: Any, year: int, season: str) -> str:
    genres = ", ".join(item.genres)
    meta = []
    if genres:
        meta.append(esc(genres))
    if item.episodes:
        meta.append(f"{esc(item.episodes)} ep.")
    if item.average_score:
        meta.append(f"Voto AniList {esc(item.average_score)}%")
    href = (
        f"/stagionali/apri?year={q(year)}&season={q(season)}"
        f"&anilist_id={q(item.anilist_id)}"
    )
    return f"""
    <a class="card seasonal-card" href="{href}">
      {image_html(item.cover_url, item.title)}
      <div class="card-body">
        <span class="badge">Stagionale</span>
        <h3>{esc(item.title)}</h3>
        <p>{' &middot; '.join(meta) or 'Apri nel provider'}</p>
      </div>
    </a>
    """


def provider_match_card(anime: Anime, provider_name: str) -> str:
    cover = get_cover(anime.anilist_id, anime.name, allow_title_lookup=False)
    href = (
        f"/anime?provider={q(provider_name)}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )
    return f"""
    <a class="card" href="{href}">
      {image_html(cover["cover_url"], anime.name)}
      <div class="card-body">
        <span class="badge">{esc(provider_name)}</span>
        <h3>{esc(anime.name)}</h3>
        <p>Ep. {esc(anime.curr_ep or '0')} / {esc(anime.last_ep or '0')}</p>
      </div>
    </a>
    """


def quick_play_form(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/play" method="post">
      {csrf_input()}
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button>{esc(label)}</button>
    </form>
    """


def token_play_form(token: str, label: str) -> str:
    return f"""
    <form action="/play-token" method="post">
      {csrf_input()}
      <input type="hidden" name="token" value="{esc(token)}">
      <button>{esc(label)}</button>
    </form>
    """


def browser_play_form(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/watch/start" method="post">
      {csrf_input()}
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button class="secondary">{esc(label)}</button>
    </form>
    """


def collection_toggle(
    *,
    action: str,
    provider_name: str,
    anime: Anime,
    cover_url: str,
    banner_url: str,
    active: bool,
    kind: str,
    label: str,
) -> str:
    icon = _bookmark_icon(active) if kind == "watchlist" else _heart_icon(active)
    return f"""
    <form class="icon-toggle-form" action="{esc(action)}" method="post">
      {csrf_input()}
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="cover_url" value="{esc(cover_url)}">
      <input type="hidden" name="banner_url" value="{esc(banner_url)}">
      <button class="icon-toggle {'active' if active else ''}" type="submit" aria-label="{esc(label)}" title="{esc(label)}">
        {icon}
      </button>
    </form>
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
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    cover_url = str(item.get("cover_url") or "")
    href = (
        f"/anime?provider={q(item['provider'])}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )
    return f"""
    <article class="card saved-card">
      <a href="{href}">{image_html(cover_url, str(item['name']))}</a>
      <div class="card-body">
        <span class="badge">Preferito</span>
        <h3><a href="{href}">{esc(item['name'])}</a></h3>
        <div class="row-actions">
          <form action="/favorites/remove" method="post">
            {csrf_input()}
            <input type="hidden" name="id" value="{esc(item['id'])}">
            <button class="secondary danger">Rimuovi</button>
          </form>
        </div>
      </div>
    </article>
    """


def watch_card(item: dict[str, Any], latest: list[Anime]) -> str:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    cover_url = str(item.get("cover_url") or "")
    href = f"/anime?saved=1&provider={q(item['provider'])}&name={q(item['name'])}&ref={q(item['ref'])}"
    new_episode_badge = '<span class="badge new-episode">Nuovo episodio</span>' if has_new_episode(item, latest) else ""
    current_episode = str(item["current_episode"])
    last_episode = available_last_episode(item, latest)
    playable_episode = current_episode if current_episode != "0" else next(iter(anime.episodes()), current_episode)
    play_label = "Inizia" if current_episode == "0" else "Riprendi"
    return f"""
    <article class="card saved-card">
      <a href="{href}">{image_html(cover_url, str(item['name']))}</a>
      <div class="card-body">
        <span class="badge">Watchlist</span>{new_episode_badge}
        <h3><a href="{href}">{esc(item['name'])}</a></h3>
        <p>Sei arrivato all'episodio <strong>{esc(current_episode)}</strong> / {esc(last_episode)}</p>
        <div class="row-actions">
          <form action="/watch/start" method="post">
            {csrf_input()}
            <input type="hidden" name="provider" value="{esc(str(item['provider']))}">
            <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
            <input type="hidden" name="episode" value="{esc(playable_episode)}">
            <button>{esc(play_label)}</button>
          </form>
          <form action="/watchlist/remove" method="post">
            {csrf_input()}
            <input type="hidden" name="id" value="{esc(item['id'])}">
            <button class="secondary danger">Rimuovi</button>
          </form>
        </div>
      </div>
    </article>
    """


def episode_row(provider_name: str, anime: Anime, episode: Anime.Episode, current_episode: str) -> str:
    active = " active" if current_episode != "0" and episode.num == current_episode else ""
    return f"""
    <div class="episode{active}">
      <div>
        <strong>Ep. {esc(episode.num)}</strong>
        {('<span class="badge">ultimo visto</span>' if active else '')}
      </div>
      <div class="row-actions compact">
        <form action="/watch/start" method="post">
          {csrf_input()}
          <input type="hidden" name="provider" value="{esc(provider_name)}">
          <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
          <input type="hidden" name="episode" value="{esc(episode.num)}">
          <button>Browser</button>
        </form>
        <form action="/play" method="post">
          {csrf_input()}
          <input type="hidden" name="provider" value="{esc(provider_name)}">
          <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
          <input type="hidden" name="episode" value="{esc(episode.num)}">
          <button class="secondary">MPV/VLC</button>
        </form>
      </div>
    </div>
    """
