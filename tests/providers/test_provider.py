import pytest
from unittest.mock import MagicMock
from aw_web.anime import Anime
from aw_web.providers import create_provider, PROVIDERS_AVAILABLE
from aw_web.providers.provider import ProviderError, update_link


class TestProviderFactory:
    """Test unitari per la classe base Provider e la Factory."""

    @pytest.mark.parametrize("provider_name", list(PROVIDERS_AVAILABLE.keys()))
    def test_create_provider_dynamic(self, provider_name):
        """Verifica la creazione dinamica di tutti i provider disponibili."""
        provider = create_provider(provider_name)
        assert provider.__class__.__name__.lower() == provider_name.replace("-", "")

    def test_create_provider_invalid(self):
        """Verifica che venga sollevato un errore per provider non validi."""
        with pytest.raises(ValueError, match="Provider 'invalid' non disponibile"):
            create_provider("invalid")

    @pytest.mark.parametrize("provider_name", list(PROVIDERS_AVAILABLE.keys()))
    def test_client_injection_dynamic(self, provider_name):
        """Verifica che il client venga iniettato correttamente in tutti i provider."""
        mock_client = MagicMock()
        import importlib

        mod_name, cls_name = PROVIDERS_AVAILABLE[provider_name]
        cls = getattr(importlib.import_module(mod_name), cls_name)

        provider = cls(client=mock_client)
        assert provider.Client is mock_client

    @pytest.mark.parametrize("provider_name", list(PROVIDERS_AVAILABLE.keys()))
    def test_client_default_dynamic(self, provider_name):
        """Verifica che venga creato un client di default per tutti i provider."""
        import importlib

        mod_name, cls_name = PROVIDERS_AVAILABLE[provider_name]
        cls = getattr(importlib.import_module(mod_name), cls_name)

        provider = cls()
        assert provider.Client is not None
        assert provider.Client.headers["User-Agent"] is not None


class TestUpdateLink:
    """Test unitari per il relink quando un riferimento non è più valido."""

    def test_update_link_uses_only_a_same_name_match(self):
        anime = Anime("Example", "old-ref")

        class FakeProvider:
            def search(self, name):
                return [Anime("Other Anime", "other-ref"), Anime("Example", "new-ref")]

        result = update_link(FakeProvider(), lambda provider, target: target.ref, anime)

        assert result == "new-ref"
        assert anime.ref == "new-ref"

    def test_update_link_raises_when_no_result_has_the_same_name(self):
        anime = Anime("Example", "old-ref")

        class FakeProvider:
            def search(self, name):
                return [Anime("Other Anime", "other-ref")]

        with pytest.raises(ProviderError, match="nessun risultato"):
            update_link(FakeProvider(), lambda provider, target: None, anime)

        assert anime.ref == "old-ref"
