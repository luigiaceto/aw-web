# IMPORTANT

If during your operations you open the local server, close it when you finish your tasks.

## Working on aw-web

- Before saying a change is done, run: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest` (CI runs the same on every push).
- To see the app, use the `aw-web` preview in `.claude/launch.json`: it keeps its database in `.dev-home/` and does not open the user's browser. Never run the app against the real `~/.aw-web/`, which holds the user's watchlist.
- Tests never touch the network or the real database: `tests/conftest.py` points `HOME` to a temporary folder, and `tests/helpers.py` builds fake data.
- AnimeUnity changes domain often: when the site stops resolving, `BASE_URL` in `src/aw_web/animeunity.py` is the first thing to check.
- The database schema is validated strictly at startup and there are no migrations: a schema change means the user runs `aw-web --reset-db`.
- Module map and dev commands: see the "Sviluppo" section of `README.md`.
