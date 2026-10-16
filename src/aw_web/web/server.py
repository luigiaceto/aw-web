"""HTTP request routing for the local web interface."""

from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
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
from aw_web.web.components import page
from aw_web.web.state import CSRF_TOKEN, HOST, PORT
from aw_web.web.utils import anime_from_json, anime_url, esc, q
from aw_web.web.views import (
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
PLAYBACK_JOB_TIMEOUT_SECONDS = 60.0
PLAYBACK_JOB_RETENTION_SECONDS = 300.0


@dataclass
class PlaybackJob:
    redirect: str
    status: str = "pending"
    error: str = ""
    created_at: float = field(default_factory=time.monotonic)


PLAYBACK_JOBS: dict[str, PlaybackJob] = {}
PLAYBACK_JOBS_LOCK = threading.Lock()


def favicon_bytes() -> bytes:
    return files("aw_web.web").joinpath("static/favicon.ico").read_bytes()


def handle_toggle_watchlist(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    toggle_watchlist(
        provider_name,
        anime,
        fields.get("cover_url", [""])[0],
        fields.get("banner_url", [""])[0],
    )
    return redirect(anime_url(provider_name, anime))


def handle_toggle_favorite(fields: dict[str, list[str]]) -> bytes:
    provider_name = fields.get("provider", [""])[0]
    anime = anime_from_json(fields.get("anime", ["{}"])[0])
    toggle_favorite(
        provider_name,
        anime,
        fields.get("cover_url", [""])[0],
        fields.get("banner_url", [""])[0],
    )
    return redirect(anime_url(provider_name, anime))


def handle_remove_watchlist(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    remove_watch_item(item_id)
    return redirect("/")


def handle_remove_favorite(fields: dict[str, list[str]]) -> bytes:
    item_id = int(fields.get("id", ["0"])[0] or 0)
    remove_favorite_item(item_id)
    return redirect("/")


def handle_play(fields: dict[str, list[str]]) -> bytes:
    return redirect(play_redirect_url(fields))


def play_request(fields: dict[str, list[str]]) -> tuple[str, Anime, str]:
    provider_name = fields.get("provider", [""])[0]
    anime_values = fields.get("anime", ["{}"])
    anime = anime_from_json(anime_values[0])
    episode_num = fields.get("episode", [anime.curr_ep])[0]
    return provider_name, anime, episode_num


def play_redirect_url(fields: dict[str, list[str]]) -> str:
    provider_name, anime, episode_num = play_request(fields)
    play_episode(provider_name, anime, episode_num)
    return anime_url(provider_name, anime)


def handle_play_start(fields: dict[str, list[str]]) -> bytes:
    provider_name, anime, episode_num = play_request(fields)
    job_id = uuid.uuid4().hex
    redirect_url = anime_url(provider_name, anime)
    with PLAYBACK_JOBS_LOCK:
        now = time.monotonic()
        for old_id in [
            key for key, job in PLAYBACK_JOBS.items()
            if now - job.created_at > PLAYBACK_JOB_RETENTION_SECONDS
        ]:
            del PLAYBACK_JOBS[old_id]
        PLAYBACK_JOBS[job_id] = PlaybackJob(redirect=redirect_url)
    start_playback_job(job_id, provider_name, anime, episode_num)
    return json.dumps(
        {
            "job_id": job_id,
            "status_url": f"/play/status?id={q(job_id)}",
            "redirect": redirect_url,
        }
    ).encode("utf-8")


def start_playback_job(job_id: str, provider_name: str, anime: Anime, episode_num: str) -> None:
    thread = threading.Thread(
        target=run_playback_job,
        args=(job_id, provider_name, anime, episode_num),
        daemon=True,
    )
    thread.start()


def run_playback_job(job_id: str, provider_name: str, anime: Anime, episode_num: str) -> None:
    try:
        play_episode(provider_name, anime, episode_num)
    except Exception as exc:
        with PLAYBACK_JOBS_LOCK:
            if job := PLAYBACK_JOBS.get(job_id):
                job.status = "error"
                job.error = str(exc)
        return

    with PLAYBACK_JOBS_LOCK:
        if job := PLAYBACK_JOBS.get(job_id):
            job.status = "ready"


def handle_play_status(params: dict[str, list[str]]) -> bytes:
    job_id = params.get("id", [""])[0]
    with PLAYBACK_JOBS_LOCK:
        job = PLAYBACK_JOBS.get(job_id)
        if not job:
            return json.dumps(
                {"status": "error", "redirect": "", "error": "Richiesta di riproduzione non trovata."}
            ).encode("utf-8")

        if job.status == "pending" and time.monotonic() - job.created_at > PLAYBACK_JOB_TIMEOUT_SECONDS:
            job.status = "error"
            job.error = "Timeout durante l'apertura di MPV."

        return json.dumps(
            {
                "status": job.status,
                "redirect": job.redirect,
                "error": job.error,
            }
        ).encode("utf-8")


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
            self.respond_favicon()
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
                payload = handle_toggle_watchlist(fields)
            elif parsed.path == "/watchlist/remove":
                payload = handle_remove_watchlist(fields)
            elif parsed.path == "/favorites/toggle":
                payload = handle_toggle_favorite(fields)
            elif parsed.path == "/favorites/remove":
                payload = handle_remove_favorite(fields)
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

    def respond_json(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
        if args and isinstance(args[0], str) and args[0].startswith("GET /play/status"):
            return
        sys.stderr.write("aw-web: " + format % args + "\n")
