"""HTTP request routing and local video proxy for the web interface."""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler
from secrets import compare_digest
from urllib.parse import parse_qs, urlparse

from aw_web.anime import Anime
from aw_web.web.components import page
from aw_web.web.services import (
    DB,
    STREAMS,
    get_cover,
    get_provider,
    open_external_player,
    resolve_episode_url,
    save_watch_progress,
    set_current_provider,
    stream_context,
    stream_token,
)
from aw_web.web.state import CSRF_TOKEN, HOST, PORT
from aw_web.web.utils import anime_from_json, esc, q
from aw_web.web.views import (
    redirect,
    render_anime,
    render_home,
    render_search,
    render_seasonal,
    render_seasonal_open,
    render_watch,
)


MAX_POST_BYTES = 1024 * 1024
ALLOWED_ORIGINS = {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}


def handle_add_watchlist(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime_values = fields.get("anime", ["{}"])
    anime = anime_from_json(anime_values[0])
    existing = DB.find_watch_item(provider_name, anime.ref)
    DB.upsert_watch_item(
        provider=provider_name,
        anime_data=anime.to_dict(),
        cover_url=fields.get("cover_url", [""])[0],
        banner_url=fields.get("banner_url", [""])[0],
        current_episode=str(existing["current_episode"]) if existing else "0",
    )
    return redirect(f"/anime?saved=1&provider={q(provider_name)}&ref={q(anime.ref)}")


def anime_redirect_url(provider_name: str, anime: Anime) -> str:
    return (
        f"/anime?provider={q(provider_name)}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )


def handle_toggle_watchlist(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    existing = DB.find_watch_item(provider_name, anime.ref)
    if existing:
        DB.remove_watch_item_by_ref(provider_name, anime.ref)
    else:
        history = DB.find_history_item(provider_name, anime.ref)
        DB.upsert_watch_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=fields.get("cover_url", [""])[0],
            banner_url=fields.get("banner_url", [""])[0],
            current_episode=str(history["current_episode"]) if history else "0",
        )
    return redirect(anime_redirect_url(provider_name, anime))


def handle_toggle_favorite(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    existing = DB.find_favorite_item(provider_name, anime.ref)
    if existing:
        DB.remove_favorite_item_by_ref(provider_name, anime.ref)
    else:
        history = DB.find_history_item(provider_name, anime.ref)
        DB.upsert_favorite_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=fields.get("cover_url", [""])[0],
            banner_url=fields.get("banner_url", [""])[0],
            current_episode=str(history["current_episode"]) if history else "0",
        )
    return redirect(anime_redirect_url(provider_name, anime))


def handle_remove_watchlist(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    if item_id:
        DB.remove_watch_item(item_id)
    return redirect("/")


def handle_remove_favorite(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    if item_id:
        DB.remove_favorite_item(item_id)
    return redirect("/")


def handle_play(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime_values = fields.get("anime", ["{}"])
    anime = anime_from_json(anime_values[0])
    episode_num = fields.get("episode", [anime.curr_ep])[0]
    provider = get_provider(provider_name)

    if not anime.has_episode(episode_num):
        provider.episodes(anime)
    episode = anime.episode(episode_num)
    url = provider.episode_link(anime, episode)
    open_external_player(url, str(episode))
    save_watch_progress(provider_name, anime, episode)
    return redirect(anime_redirect_url(provider_name, anime))


def handle_play_token(fields: dict[str, list[str]]) -> bytes:
    token = fields.get("token", [""])[0]
    provider_name, anime, episode = stream_context(token)
    url, _ = resolve_episode_url(token)
    open_external_player(url, str(episode))
    save_watch_progress(provider_name, anime, episode)
    return redirect(f"/watch?token={q(token)}")


def handle_watch_start(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime_values = fields.get("anime", ["{}"])
    anime = anime_from_json(anime_values[0])
    episode_num = fields.get("episode", [anime.curr_ep])[0]
    token = stream_token(provider_name, anime, episode_num)
    return redirect(f"/watch?token={q(token)}")


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/":
            self.respond(render_home())
        elif parsed.path == "/search":
            self.respond(render_search(params))
        elif parsed.path == "/anime":
            self.respond(render_anime(params))
        elif parsed.path == "/stagionali":
            self.respond(render_seasonal(params))
        elif parsed.path == "/stagionali/apri":
            self.respond(render_seasonal_open(params))
        elif parsed.path == "/watch":
            self.respond(render_watch(params))
        elif parsed.path == "/stream":
            self.stream_video(params)
        elif parsed.path == "/set-provider":
            self.send_error(405)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            self.send_error(400)
            return
        if length > MAX_POST_BYTES:
            self.send_error(413)
            return
        raw = self.rfile.read(length).decode("utf-8")
        fields = parse_qs(raw)
        parsed = urlparse(self.path)
        if not self.same_origin() or not self.valid_csrf(fields):
            self.send_error(403)
            return
        try:
            if parsed.path == "/set-provider":
                set_current_provider(fields.get("name", [""])[0])
                self.send_response(204)
                self.end_headers()
                return
            elif parsed.path == "/watchlist/add":
                payload = handle_add_watchlist(fields)
            elif parsed.path == "/watchlist/toggle":
                payload = handle_toggle_watchlist(fields)
            elif parsed.path == "/watchlist/remove":
                payload = handle_remove_watchlist(fields)
            elif parsed.path == "/favorites/toggle":
                payload = handle_toggle_favorite(fields)
            elif parsed.path == "/favorites/remove":
                payload = handle_remove_favorite(fields)
            elif parsed.path == "/play":
                payload = handle_play(fields)
            elif parsed.path == "/play-token":
                payload = handle_play_token(fields)
            elif parsed.path == "/watch/start":
                payload = handle_watch_start(fields)
            else:
                self.send_error(404)
                return
            self.respond(payload)
        except Exception as exc:
            self.respond(page("Errore", f'<p class="error">{esc(exc)}</p><p><a href="/">Torna alla home</a></p>'), status=500)

    def same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        return origin in ALLOWED_ORIGINS

    def valid_csrf(self, fields: dict[str, list[str]]) -> bool:
        token = fields.get("csrf_token", [""])[0]
        return compare_digest(token, CSRF_TOKEN)

    def stream_video(self, params: dict[str, list[str]]) -> None:
        token = params.get("token", [""])[0]
        try:
            data = STREAMS.get(token)
            if not data:
                raise RuntimeError("Sessione video scaduta. Riapri l'episodio dalla pagina anime.")
            provider = get_provider(data["provider"])
            headers = {}
            if range_header := self.headers.get("Range"):
                headers["Range"] = range_header

            for attempt in range(2):
                url, _ = resolve_episode_url(token)
                with provider.Client.stream("GET", url, headers=headers) as response:
                    if attempt == 0 and response.status_code in {403, 404, 410, 416}:
                        data["url"] = ""
                        continue

                    self.send_response(response.status_code)
                    for name in (
                        "content-type",
                        "content-length",
                        "content-range",
                        "accept-ranges",
                        "cache-control",
                        "last-modified",
                        "etag",
                    ):
                        value = response.headers.get(name)
                        if value:
                            self.send_header(name.title(), value)
                    if "accept-ranges" not in response.headers:
                        self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    for chunk in response.iter_bytes(1024 * 1024):
                        if chunk:
                            self.wfile.write(chunk)
                    return
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            body = page("Errore stream", f'<p class="error">{esc(exc)}</p>')
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def respond(self, body: bytes, status: int = 200) -> None:
        if body.startswith(b"REDIRECT:"):
            self.send_response(303)
            self.send_header("Location", body.decode("utf-8").split(":", 1)[1])
            self.end_headers()
            return
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("aw-web: " + format % args + "\n")
