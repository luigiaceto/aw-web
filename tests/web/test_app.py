import sqlite3

from aw_web.web.app import main, reset_database
from aw_web.web.db import WebDatabase


def test_reset_database_removes_sqlite_files(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    db_path.write_text("db")
    tmp_path.joinpath("web.sqlite3-wal").write_text("wal")
    tmp_path.joinpath("web.sqlite3-shm").write_text("shm")
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    removed = reset_database(db_path)

    assert removed
    assert not db_path.exists()
    assert not tmp_path.joinpath("web.sqlite3-wal").exists()
    assert not tmp_path.joinpath("web.sqlite3-shm").exists()
    assert tmp_path.joinpath("web.sqlite3.bak").read_text() == "db"


def test_reset_database_can_be_cancelled(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    db_path.write_text("db")
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    removed = reset_database(db_path)

    assert not removed
    assert db_path.exists()


def test_main_reset_db_uses_home_database_path(tmp_path, monkeypatch):
    db_dir = tmp_path / ".aw-web"
    db_dir.mkdir()
    db_path = db_dir / "web.sqlite3"
    db_path.write_text("db")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    main(["--reset-db"])

    assert not db_path.exists()


def test_main_validates_database_before_starting_server(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("webbrowser.open", lambda url: True)

    class FakeServer:
        def __init__(self, address, handler):
            self.address = address
            self.handler = handler

        def serve_forever(self):
            return None

    monkeypatch.setattr("aw_web.web.app.ThreadingHTTPServer", FakeServer)

    main([])

    output = capsys.readouterr().out
    assert "Database creato correttamente" in output
    assert "Database validato con successo" in output
    assert output.index("Database validato con successo") < output.index("aw-web avviato")


def test_main_exits_when_database_validation_fails(tmp_path, monkeypatch, capsys):
    db_dir = tmp_path / ".aw-web"
    db_dir.mkdir()
    db_path = db_dir / "web.sqlite3"
    WebDatabase(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE watch_history")
    monkeypatch.setenv("HOME", str(tmp_path))

    try:
        main([])
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("main should exit when database validation fails")

    output = capsys.readouterr().out
    assert "Validazione database fallita" in output
    assert "Tabella mancante: watch_history" in output
    assert "aw-web --reset-db" in output
