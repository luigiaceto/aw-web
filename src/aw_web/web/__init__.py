"""Interfaccia web locale: server HTTP, pagine e componenti HTML."""

from secrets import token_urlsafe

HOST = "127.0.0.1"
PORT = 8765
CSRF_TOKEN = token_urlsafe(32)  # nuovo a ogni avvio: i form valgono solo per questa sessione
