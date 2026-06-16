"""Reusable HTML components for the local web interface."""

from __future__ import annotations

import json
from typing import Any

from aw_web.anime import Anime
from aw_web.web.services import default_provider_name, get_cover
from aw_web.web.styles import CSS
from aw_web.web.utils import anime_to_json, esc, has_new_episode, q


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
        <a class="brand" href="/">aw-web</a>
        <form class="search" action="/search" method="get">
          <input type="search" name="q" placeholder="Cerca anime..." autocomplete="off" required>
          <select name="provider" id="provider-select" onchange="fetch('/set-provider?name='+this.value)">
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


def quick_play_form(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/play" method="post">
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button>{esc(label)}</button>
    </form>
    """


def token_play_form(token: str, label: str) -> str:
    return f"""
    <form action="/play-token" method="post">
      <input type="hidden" name="token" value="{esc(token)}">
      <button>{esc(label)}</button>
    </form>
    """


def browser_play_form(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/watch/start" method="post">
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button class="secondary">{esc(label)}</button>
    </form>
    """


def watch_card(item: dict[str, Any], latest: list[Anime]) -> str:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    cover_url = str(item.get("cover_url") or "")
    href = f"/anime?saved=1&provider={q(item['provider'])}&name={q(item['name'])}&ref={q(item['ref'])}"
    new_episode_badge = '<span class="badge new-episode">Nuovo episodio</span>' if has_new_episode(item, latest) else ""
    current_episode = str(item["current_episode"])
    playable_episode = current_episode if current_episode != "0" else next(iter(anime.episodes()), current_episode)
    play_label = "Inizia" if current_episode == "0" else "Riprendi"
    return f"""
    <article class="card saved-card">
      <a href="{href}">{image_html(cover_url, str(item['name']))}</a>
      <div class="card-body">
        <span class="badge">Watchlist</span>{new_episode_badge}
        <h3><a href="{href}">{esc(item['name'])}</a></h3>
        <p>Sei arrivato all'episodio <strong>{esc(current_episode)}</strong> / {esc(item['last_episode'])}</p>
        <div class="row-actions">
          <form action="/watch/start" method="post">
            <input type="hidden" name="provider" value="{esc(str(item['provider']))}">
            <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
            <input type="hidden" name="episode" value="{esc(playable_episode)}">
            <button>{esc(play_label)}</button>
          </form>
          <form action="/watchlist/remove" method="post">
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
          <input type="hidden" name="provider" value="{esc(provider_name)}">
          <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
          <input type="hidden" name="episode" value="{esc(episode.num)}">
          <button>Browser</button>
        </form>
        <form action="/play" method="post">
          <input type="hidden" name="provider" value="{esc(provider_name)}">
          <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
          <input type="hidden" name="episode" value="{esc(episode.num)}">
          <button class="secondary">MPV/VLC</button>
        </form>
      </div>
    </div>
    """
