"""Entrypoint that starts the local aw-web server."""

from __future__ import annotations

import os
import signal
import sys
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

    def _sigterm(signum: int, frame: object) -> None:
        print("\nWebapp chiusa, a presto!")
        os._exit(0)

    signal.signal(signal.SIGTERM, _sigterm)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWebapp chiusa, a presto!")
        sys.exit(0)


if __name__ == "__main__":
    main()
