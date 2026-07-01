"""HTTP request routing for the local web interface."""

from __future__ import annotations

import sys
from importlib.resources import files
from http.server import BaseHTTPRequestHandler
from secrets import compare_digest
from urllib.parse import parse_qs, urlparse

from aw_web.anime import Anime
from aw_web.services.collections import (
    remove_favorite_item,
    remove_watch_item,
    toggle_favorite,
    toggle_watchlist,
)
from aw_web.services.playback import play_episode
from aw_web.services.providers import set_current_provider
from aw_web.web.components import page
from aw_web.web.state import CSRF_TOKEN, HOST, PORT
from aw_web.web.utils import anime_from_json, esc, q
from aw_web.web.views import (
    redirect,
    render_anime,
    render_home,
    render_search,
    render_seasonal,
    render_seasonal_open,
)


MAX_POST_BYTES = 1024 * 1024
ALLOWED_ORIGINS = {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}


def favicon_bytes() -> bytes:
    return files("aw_web.web").joinpath("static/favicon.ico").read_bytes()


def anime_redirect_url(provider_name: str, anime: Anime) -> str:
    return (
        f"/anime?provider={q(provider_name)}&name={q(anime.name)}&ref={q(anime.ref)}"
        f"&curr_ep={q(anime.curr_ep)}&last_ep={q(anime.last_ep)}&anilist_id={q(anime.anilist_id)}"
    )


def handle_toggle_watchlist(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    toggle_watchlist(
        provider_name,
        anime,
        fields.get("cover_url", [""])[0],
        fields.get("banner_url", [""])[0],
    )
    return redirect(anime_redirect_url(provider_name, anime))


def handle_toggle_favorite(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    toggle_favorite(
        provider_name,
        anime,
        fields.get("cover_url", [""])[0],
        fields.get("banner_url", [""])[0],
    )
    return redirect(anime_redirect_url(provider_name, anime))


def handle_remove_watchlist(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    remove_watch_item(item_id)
    return redirect("/")


def handle_remove_favorite(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    remove_favorite_item(item_id)
    return redirect("/")


def handle_play(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime_values = fields.get("anime", ["{}"])
    anime = anime_from_json(anime_values[0])
    episode_num = fields.get("episode", [anime.curr_ep])[0]
    play_episode(provider_name, anime, episode_num)
    return redirect(anime_redirect_url(provider_name, anime))


class WebHandler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/favicon.ico":
            self.respond_favicon(head_only=True)
        else:
            self.send_error(405)

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
        elif parsed.path == "/favicon.ico":
            self.respond_favicon()
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

    def respond_favicon(self, *, head_only: bool = False) -> None:
        try:
            body = favicon_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/x-icon")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("aw-web: " + format % args + "\n")
