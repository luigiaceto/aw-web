"""Entrypoint that starts the local aw-web server."""

from __future__ import annotations

import webbrowser
from http.server import ThreadingHTTPServer

from aw_web.web.server import WebHandler
from aw_web.web.services import DB, ensure_config
from aw_web.web.state import HOST, PORT


def main() -> None:
    ensure_config()
    server = ThreadingHTTPServer((HOST, PORT), WebHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"aw-web avviato su {url}")
    print(f"Database watchlist: {DB.path}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server.serve_forever()


if __name__ == "__main__":
    main()
