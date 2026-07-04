import time
import json
import warnings

import pytest
from pathlib import Path
from aw_web.providers.animeunity import Animeunity

# Le fixtures sono considerate deprecate/scadute dopo 7 giorni
DEPRECATION_PERIOD_SECONDS = 7 * 24 * 60 * 60  # 7 giorni

def update_fixtures():
    """Scarica e aggiorna tutte le fixtures per i test unitari in modo rispettoso (con delay)."""
    au = Animeunity()

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    def respectful_sleep():
        time.sleep(.5)

    print("Scaricando i risultati di ricerca JSON per AnimeUnity...")
    _ = au._session  # Inizializza sessione/cookies
    respectful_sleep()
    response = au.Client.post(f"{au.BASE_URL}/livesearch", data={"title": "naruto"})
    (fixtures_dir / "au_search.json").write_text(json.dumps(response.json(), indent=2), encoding="utf-8")
    respectful_sleep()

    print("Scaricando la landing page (latest) per AnimeUnity...")
    (fixtures_dir / "au_latest.html").write_text(au._session, encoding="utf-8")
    respectful_sleep()

    print("Scaricando i dati info JSON per un anime di AnimeUnity (id 1469 - Naruto)...")
    response_au_info = au.Client.get(f"{au.BASE_URL}/info_api/1469/")
    (fixtures_dir / "au_info.json").write_text(json.dumps(response_au_info.json(), indent=2), encoding="utf-8")

    print("✓ Tutte le fixtures salvate con successo nella cartella:", fixtures_dir.resolve())


def pytest_addoption(parser):
    parser.addoption(
        "--update-fixtures",
        action="store_true",
        default=False,
        help="Forza la rigenerazione di tutte le fixtures per i test",
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures(request):
    force_update = request.config.getoption("--update-fixtures")
    fixtures_dir = Path(__file__).parent / "fixtures"
    required_files = [
        "au_search.json",
        "au_latest.html",
        "au_info.json",
    ]

    missing = False
    deprecated = False
    now = time.time()

    if not fixtures_dir.exists():
        missing = True
    else:
        for filename in required_files:
            file_path = fixtures_dir / filename
            if not file_path.exists():
                missing = True
                break

            # Verifica se la fixture è deprecata (più vecchia di 7 giorni)
            file_mtime = file_path.stat().st_mtime
            if now - file_mtime > DEPRECATION_PERIOD_SECONDS:
                deprecated = True

    if force_update:
        warnings.warn(
            UserWarning("\n[Pytest] Rigenerazione fixtures richiesta tramite --update-fixtures.")
        )
        try:
            update_fixtures()
        except Exception as e:
            warnings.warn(UserWarning(f"Errore durante l'aggiornamento delle fixtures: {e}"))
        return

    if missing:
        pytest.fail(
            "Fixture AnimeUnity mancanti. Esegui pytest con --update-fixtures per rigenerarle.",
            pytrace=False,
        )

    if deprecated:
        warnings.warn(
            UserWarning(
                "\n[Pytest] Le fixtures AnimeUnity sono deprecate (più vecchie di 7 giorni). "
                "Continuo a usare quelle locali; esegui pytest con --update-fixtures per aggiornarle."
            )
        )


@pytest.fixture(autouse=True)
def isolate_default_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    from aw_web.web import state

    state.reset_lazy_database()


if __name__ == "__main__":
    update_fixtures()
