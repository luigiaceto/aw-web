"""Reusable HTML components for the local web interface."""

from __future__ import annotations

import json
from typing import Any

from aw_web.anime import Anime
from aw_web.services.anilist import get_cover
from aw_web.web.state import CSRF_TOKEN
from aw_web.web.styles import CSS
from aw_web.web.utils import anime_to_json, available_last_episode, esc, has_new_episode, next_playable_episode, q


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
      <style>{CSS}</style>
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
      <script>
        (() => {{
          function setPlayLoading(form) {{
            const button = form.querySelector('button[type="submit"], button:not([type])');
            if (!button || button.dataset.playLoading === "1") return null;
            const state = {{
              button,
              disabled: button.disabled,
              html: button.innerHTML,
            }};
            button.dataset.playLoading = "1";
            button.style.setProperty("--loading-button-width", `${{button.offsetWidth}}px`);
            button.disabled = true;
            button.classList.add("is-loading");
            button.setAttribute("aria-busy", "true");
            button.innerHTML = '<span class="play-spinner" aria-hidden="true"></span><span class="sr-only">Apertura MPV...</span>';
            return state;
          }}

          function restorePlayLoading(state) {{
            if (!state) return;
            state.button.disabled = state.disabled;
            state.button.classList.remove("is-loading");
            state.button.removeAttribute("aria-busy");
            state.button.removeAttribute("data-play-loading");
            state.button.style.removeProperty("--loading-button-width");
            state.button.innerHTML = state.html;
          }}

          function delay(ms) {{
            return new Promise((resolve) => window.setTimeout(resolve, ms));
          }}

          function showPlaybackError(message) {{
            window.alert(message || "Impossibile aprire MPV.");
          }}

          async function waitForPlayback(payload) {{
            if (!payload.status_url) return payload.redirect;
            const startedAt = Date.now();
            while (Date.now() - startedAt < 60000) {{
              await delay(400);
              const response = await fetch(payload.status_url, {{
                credentials: "same-origin",
                headers: {{ "Accept": "application/json" }},
              }});
              if (!response.ok) throw new Error("Impossibile controllare lo stato di MPV.");
              const status = await response.json();
              if (status.status === "ready") return status.redirect || payload.redirect;
              if (status.status === "error") throw new Error(status.error || "Impossibile aprire MPV.");
            }}
            throw new Error("Timeout durante l'apertura di MPV.");
          }}

          async function submitPlayForm(form) {{
            const state = setPlayLoading(form);
            const body = new URLSearchParams(new FormData(form));
            try {{
              const response = await fetch("/play/start", {{
                method: "POST",
                body,
                credentials: "same-origin",
                headers: {{
                  "Accept": "application/json",
                }},
              }});
              if (!response.ok) {{
                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
                return;
              }}
              const payload = await response.json();
              const redirect = await waitForPlayback(payload);
              if (redirect) {{
                window.location.assign(redirect);
                return;
              }}
            }} catch (error) {{
              console.error("Errore apertura MPV", error);
              showPlaybackError(error instanceof Error ? error.message : "");
            }}
            restorePlayLoading(state);
          }}

          document.addEventListener("submit", (event) => {{
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) return;
            if (form.getAttribute("action") !== "/play") return;
            event.preventDefault();
            submitPlayForm(form);
          }}, true);
        }})();
      </script>
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


def _link_action(href: str, label: str, icon: str = "") -> str:
    return f'<a class="button secondary card-action" href="{esc(href)}">{icon}<span>{esc(label)}</span></a>'


def _remove_form(action: str, item_id: object, label: str) -> str:
    return f"""
    <form action="{esc(action)}" method="post">
      {csrf_input()}
      <input type="hidden" name="id" value="{esc(item_id)}">
      <button class="secondary danger card-icon-action" type="submit" aria-label="{esc(label)}" title="{esc(label)}">
        {_trash_icon()}
      </button>
    </form>
    """


def _play_form_action(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/play" method="post">
      {csrf_input()}
      <input type="hidden" name="provider" value="{esc(provider_name)}">
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
    badges: list[str],
    meta: str,
    description: str = "",
    actions: str = "",
    class_name: str = "",
) -> str:
    badge_html = "".join(_pill(badge) for badge in badges if badge)
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
        <div class="badge-row">{badge_html}</div>
        <h3>{esc(title)}</h3>
      </div>
      <div class="card-hover">
        <div class="hover-copy">
          <div class="badge-row">{badge_html}</div>
          <h3>{esc(title)}</h3>
          <p class="hover-meta">{esc(meta) if meta else 'Scheda anime'}</p>
          {description_html}
        </div>
        {f'<div class="hover-actions">{actions}</div>' if actions else ''}
      </div>
    </article>
    """


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
    actions = ""
    if badge == "Nuovo" and anime.curr_ep and anime.curr_ep != "0":
        actions = _play_form_action(provider_name, anime, anime.curr_ep, f"Guarda episodio {anime.curr_ep}")
    return _catalog_card(
        title=anime.name,
        href=href,
        image=image,
        badges=[badge] if badge else [],
        meta=_meta_text(info),
        description=_anime_description(anime),
        actions=actions,
    )


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
    return _catalog_card(
        title=item.title,
        href=href,
        image=image_html(item.cover_url, item.title),
        badges=["Stagionale"],
        meta=_meta_text(meta),
        class_name="seasonal-card",
    )


def anilist_card(item: Any, source: str, badge: str) -> str:
    genres = ", ".join(item.genres)
    meta = []
    if genres:
        meta.append(esc(genres))
    if item.episodes:
        meta.append(f"{esc(item.episodes)} ep.")
    if item.average_score:
        meta.append(f"Voto AniList {esc(item.average_score)}%")
    href = f"/anilist/apri?source={q(source)}&anilist_id={q(item.anilist_id)}"
    return _catalog_card(
        title=item.title,
        href=href,
        image=image_html(item.cover_url, item.title),
        badges=[badge],
        meta=_meta_text(meta),
        class_name="seasonal-card anilist-card",
    )


def provider_match_card(anime: Anime, provider_name: str) -> str:
    cover = get_cover(anime.anilist_id, anime.name, allow_title_lookup=False)
    href = (
        f"/anime?provider={q(provider_name)}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )
    return _catalog_card(
        title=anime.name,
        href=href,
        image=image_html(cover["cover_url"], anime.name),
        badges=[provider_name],
        meta=f"Ep. {anime.curr_ep or '0'} / {anime.last_ep or '0'}",
        description=_anime_description(anime),
    )


def play_form(provider_name: str, anime: Anime, episode_num: str, label: str) -> str:
    return f"""
    <form action="/play" method="post">
      {csrf_input()}
      <input type="hidden" name="provider" value="{esc(provider_name)}">
      <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
      <input type="hidden" name="episode" value="{esc(episode_num)}">
      <button>{esc(label)}</button>
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
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    cover_url = str(item.get("cover_url") or "")
    href = (
        f"/anime?provider={q(item['provider'])}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )
    meta = _meta_text([
        str(item.get("status") or ""),
        f"Ep. {item.get('current_episode') or anime.curr_ep or '0'} / {item.get('last_episode') or anime.last_ep or '0'}",
    ])
    actions = _remove_form("/favorites/remove", item["id"], "Rimuovi dai preferiti")
    return _catalog_card(
        title=str(item["name"]),
        href=href,
        image=image_html(cover_url, str(item["name"])),
        badges=["Preferito"],
        meta=meta,
        description=_anime_description(anime),
        actions=actions,
        class_name="saved-card favorite-card",
    )


def watch_card(item: dict[str, Any], latest: list[Anime]) -> str:
    anime_data = json.loads(str(item["anime_json"]))
    anime = Anime.from_dict(anime_data)
    cover_url = str(item.get("cover_url") or "")
    href = f"/anime?saved=1&provider={q(item['provider'])}&name={q(item['name'])}&ref={q(item['ref'])}"
    new_episode_badge = '<span class="badge new-episode">Nuovo episodio</span>' if has_new_episode(item, latest) else ""
    current_episode = str(item["current_episode"])
    last_episode = available_last_episode(item, latest)
    playable_episode = next_playable_episode(item, latest)
    play_label = "Inizia" if current_episode == "0" else "Riprendi"
    meta = _meta_text([
        f"Ep. {current_episode} / {last_episode}",
        str(item.get("status") or ""),
    ])
    actions = (
        _play_form_action(str(item["provider"]), anime, playable_episode, play_label)
        + _remove_form("/watchlist/remove", item["id"], "Rimuovi dalla watchlist")
    )
    return _catalog_card(
        title=str(item["name"]),
        href=href,
        image=image_html(cover_url, str(item["name"])),
        badges=["Watchlist"],
        meta=meta,
        description=_anime_description(anime),
        actions=actions,
        class_name="saved-card watch-card",
    ).replace(
        '<div class="badge-row"><span class="badge">Watchlist</span></div>',
        f'<div class="badge-row"><span class="badge">Watchlist</span>{new_episode_badge}</div>',
    )


def episode_row(provider_name: str, anime: Anime, episode: Anime.Episode, current_episode: str) -> str:
    active = " active" if current_episode != "0" and episode.num == current_episode else ""
    return f"""
    <div class="episode{active}">
      <div>
        <strong>Ep. {esc(episode.num)}</strong>
        {('<span class="badge">ultimo visto</span>' if active else '')}
      </div>
      <div class="row-actions compact">
        <form action="/play" method="post">
          {csrf_input()}
          <input type="hidden" name="provider" value="{esc(provider_name)}">
          <input type="hidden" name="anime" value="{esc(anime_to_json(anime))}">
          <input type="hidden" name="episode" value="{esc(episode.num)}">
          <button>Guarda</button>
        </form>
      </div>
    </div>
    """
