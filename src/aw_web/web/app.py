"""Entrypoint that starts the local aw-web server."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Sequence

from aw_web.services.providers import ensure_config
from aw_web.web.db import default_db_path, prepare_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Avvia l'interfaccia web locale di aw-web.")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Cancella il database locale di aw-web e termina.",
    )
    return parser


def reset_database(path: Path) -> bool:
    answer = input(f"Cancellare definitivamente il database locale in {path}? [yes/no] ")
    if answer.strip().lower() != "yes":
        print("Operazione annullata.")
        return False

    removed = False
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        try:
            candidate.unlink()
            removed = True
        except FileNotFoundError:
            pass

    if removed:
        print(f"Database locale cancellato: {path}")
    else:
        print(f"Nessun database locale trovato in {path}")
    return removed


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.reset_db:
        reset_database(default_db_path())
        return

    ensure_config()
    db_result = prepare_database(default_db_path())
    print(f"Database locale: {db_result.path}")
    if db_result.created:
        print("Database creato correttamente")
    if db_result.valid:
        print("Database validato con successo")
    else:
        print("Validazione database fallita")
        for error in db_result.errors:
            print(f"- {error}")
        print("Esegui aw-web --reset-db per cancellare e ricreare il database locale")
        sys.exit(1)

    from aw_web.web.server import WebHandler
    from aw_web.web.state import HOST, PORT

    server = ThreadingHTTPServer((HOST, PORT), WebHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"aw-web avviato su {url}")

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
