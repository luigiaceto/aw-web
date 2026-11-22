"""HTTP request routing for the local web interface."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from pathlib import Path
from secrets import compare_digest
from typing import Literal
from urllib.parse import parse_qs, urlparse

from aw_web.anime import Anime, anime_from_json
from aw_web.db import DB
from aw_web.library import toggle
from aw_web.playback import job_status, play_episode, start_job
from aw_web.web import CSRF_TOKEN, HOST, PORT
from aw_web.web.components import anime_url, esc, page, q
from aw_web.web.pages import (
    redirect,
    render_anilist_open,
    render_anilist_ranking,
    render_anime,
    render_home,
    render_search,
    render_seasonal,
    render_seasonal_open,
    watchlist_cards_payload,
)

MAX_POST_BYTES = 1024 * 1024
ALLOWED_ORIGINS = {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}


STATIC_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".ico": "image/x-icon",
}


def static_file(name: str) -> tuple[bytes, str] | None:
    """Contenuto e tipo di un file in web/static; None se il nome non è un file servibile."""
    content_type = STATIC_TYPES.get(Path(name).suffix)
    if not content_type or Path(name).name != name:  # niente sottocartelle né "../"
        return None
    resource = files("aw_web.web").joinpath("static", name)
    return (resource.read_bytes(), content_type) if resource.is_file() else None


def handle_toggle(table: Literal["watchlist", "favorites"], fields: dict[str, list[str]]) -> bytes:
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    toggle(table, anime)
    return redirect(anime_url(anime))


def handle_remove(table: Literal["watchlist", "favorites"], fields: dict[str, list[str]]) -> bytes:
    DB.remove(table, fields.get("ref", [""])[0])
    return redirect("/")


def play_request(fields: dict[str, list[str]]) -> tuple[Anime, str]:
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    return anime, fields.get("episode", [anime.curr_ep])[0]


def handle_play(fields: dict[str, list[str]]) -> bytes:
    """Senza JavaScript: apre l'episodio e poi torna alla scheda."""
    anime, episode_num = play_request(fields)
    play_episode(anime, episode_num)
    return redirect(anime_url(anime))


def handle_play_start(fields: dict[str, list[str]]) -> bytes:
    anime, episode_num = play_request(fields)
    job_id = start_job(anime, episode_num)
    payload = {"job_id": job_id, "status_url": f"/play/status?id={q(job_id)}", "redirect": anime_url(anime)}
    return json.dumps(payload).encode("utf-8")


def handle_play_status(params: dict[str, list[str]]) -> bytes:
    job = job_status(params.get("id", [""])[0])
    payload = (
        {"status": job.status, "error": job.error}
        if job
        else {
            "status": "error",
            "error": "Richiesta di riproduzione non trovata.",
        }
    )
    return json.dumps(payload).encode("utf-8")


class WebHandler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path == "/favicon.ico" or path.startswith("/static/"):
            self.respond_static(path.rsplit("/", 1)[-1], head_only=True)
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
        elif parsed.path == "/popolari":
            self.respond(render_anilist_ranking("popolari"))
        elif parsed.path == "/top-100":
            self.respond(render_anilist_ranking("top-100"))
        elif parsed.path == "/anilist/apri":
            self.respond(render_anilist_open(params))
        elif parsed.path == "/play/status":
            self.respond_json(handle_play_status(params))
        elif parsed.path == "/watchlist/cards":
            self.respond_json(watchlist_cards_payload())
        elif parsed.path == "/favicon.ico":
            self.respond_static("favicon.ico")
        elif parsed.path.startswith("/static/"):
            self.respond_static(parsed.path.removeprefix("/static/"))
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
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        fields = parse_qs(raw)
        parsed = urlparse(self.path)
        if not self.same_origin() or not self.valid_csrf(fields):
            self.send_error(403)
            return
        try:
            if parsed.path == "/watchlist/toggle":
                payload = handle_toggle("watchlist", fields)
            elif parsed.path == "/watchlist/remove":
                payload = handle_remove("watchlist", fields)
            elif parsed.path == "/favorites/toggle":
                payload = handle_toggle("favorites", fields)
            elif parsed.path == "/favorites/remove":
                payload = handle_remove("favorites", fields)
            elif parsed.path == "/play":
                payload = handle_play(fields)
            elif parsed.path == "/play/start":
                self.respond_json(handle_play_start(fields))
                return
            else:
                self.send_error(404)
                return
            self.respond(payload)
        except Exception as exc:
            self.respond(
                page("Errore", f'<p class="error">{esc(exc)}</p><p><a href="/">Torna alla home</a></p>'), status=500
            )

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

    def respond_json(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_static(self, name: str, *, head_only: bool = False) -> None:
        found = static_file(name)
        if not found:
            self.send_error(404)
            return
        body, content_type = found
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")  # dopo un aggiornamento dell'app il browser li ricarica
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        if args and isinstance(args[0], str) and args[0].startswith("GET /play/status"):
            return
        sys.stderr.write("aw-web: " + format % args + "\n")
