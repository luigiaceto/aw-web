import pytest


@pytest.fixture(autouse=True)
def isolate_default_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    from aw_web.web import state

    state.reset_lazy_database()

