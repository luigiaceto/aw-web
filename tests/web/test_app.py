import sqlite3

from aw_web.web.app import main, reset_database
from aw_web.web.db import WebDatabase


def test_reset_database_moves_the_database_to_a_backup(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    db_path.write_text("db")
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    removed = reset_database(db_path)

    assert removed
    assert not db_path.exists()
    backups = list(tmp_path.glob("web.sqlite3.*.bak"))
    assert [backup.read_text() for backup in backups] == ["db"]


def test_second_reset_keeps_the_first_backup(tmp_path, monkeypatch):
    db_path = tmp_path / "web.sqlite3"
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    stamps = iter(["20260101-000000", "20260101-000001"])
    monkeypatch.setattr("aw_web.web.app.time.strftime", lambda fmt: next(stamps))

    db_path.write_text("progress")
    reset_database(db_path)
    db_path.write_text("empty")
    reset_database(db_path)

    backups = sorted(backup.read_text() for backup in tmp_path.glob("web.sqlite3.*.bak"))
    assert backups == ["empty", "progress"]


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
