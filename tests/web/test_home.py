from aw_web.anime import Anime
from aw_web.web import views
from aw_web.web.utils import anime_to_json


class FakeProvider:
    def latest(self, _: str):
        return []


class FakeDB:
    def __init__(self, watch_items, favorite_items=()):
        self._watch_items = list(watch_items)
        self._favorite_items = list(favorite_items)

    def watchlist(self):
        return self._watch_items

    def favorites(self):
        return self._favorite_items


def _watch_item(item_id: int, name: str, *, cover_url: str = "", banner_url: str = ""):
    anime = Anime(name, f"ref-{item_id}", curr_ep="1", last_ep="12")
    return {
        "id": item_id,
        "provider": "animeunity",
        "name": anime.name,
        "ref": anime.ref,
        "current_episode": "1",
        "last_episode": "12",
        "status": "In corso",
        "cover_url": cover_url,
        "banner_url": banner_url,
        "anime_json": anime_to_json(anime),
    }


def test_home_uses_all_watchlist_images_for_hero_slideshow(monkeypatch):
    watch_items = [
        _watch_item(1, "First", banner_url="https://img.example/first.jpg"),
        _watch_item(2, "Second", cover_url="https://img.example/second.jpg"),
        _watch_item(3, "No Image"),
    ]
    favorite_items = [
        _watch_item(4, "Favorite", banner_url="https://img.example/favorite.jpg"),
    ]
    monkeypatch.setattr(views, "DB", FakeDB(watch_items, favorite_items))
    monkeypatch.setattr(views, "get_provider", lambda _: FakeProvider())
    monkeypatch.setattr(views, "refresh_watchlist_availability", lambda *args, **kwargs: None)

    html = views.render_home().decode()

    assert html.count('class="hero-slide"') == 2
    assert "https://img.example/first.jpg" in html
    assert "https://img.example/second.jpg" in html
    assert "https://img.example/favorite.jpg" not in html
    assert "--hero-image" not in html


def test_home_static_hero_slide_when_watchlist_has_one_image(monkeypatch):
    monkeypatch.setattr(
        views,
        "DB",
        FakeDB([_watch_item(1, "Only", banner_url="https://img.example/only.jpg")]),
    )
    monkeypatch.setattr(views, "get_provider", lambda _: FakeProvider())
    monkeypatch.setattr(views, "refresh_watchlist_availability", lambda *args, **kwargs: None)

    html = views.render_home().decode()

    assert 'class="hero-slideshow is-static"' in html
    assert 'class="hero-slide"' in html
    assert "@keyframes heroSlideshow" not in html
