import pytest
from aw_web.anime import Anime
from aw_web.providers.provider import ProviderError, update_link


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

