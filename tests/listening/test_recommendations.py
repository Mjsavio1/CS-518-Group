"""Unit tests for the lesser-known artist recommendation algorithm."""
from urllib.parse import urlparse

import pytest

from class_demo.listening_service.listening_service import (
    ListeningService,
    SpotifyConnectionError,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_TOP_TRACKS_PAYLOAD = {
    "items": [
        {
            "name": "Track A",
            "artists": [{"id": "artist-1", "name": "Big Artist"}],
        },
        {
            "name": "Track B",
            "artists": [{"id": "artist-2", "name": "Medium Artist"}],
        },
    ]
}

_RELATED_ARTISTS_ARTIST_1 = {
    "artists": [
        {"id": "rec-1", "name": "Hidden Gem",    "popularity": 30, "genres": ["indie", "folk"]},
        {"id": "rec-2", "name": "Underground Act","popularity": 45, "genres": ["electronic"]},
        {"id": "rec-3", "name": "Big Artist",     "popularity": 80, "genres": []},  # already known – should be excluded
    ]
}

_RELATED_ARTISTS_ARTIST_2 = {
    "artists": [
        {"id": "rec-4", "name": "Niche Project",  "popularity": 25, "genres": ["ambient"]},
        {"id": "rec-2", "name": "Underground Act", "popularity": 45, "genres": ["electronic"]},  # duplicate
        {"id": "rec-5", "name": "Mainstream Star", "popularity": 75, "genres": ["pop"]},          # too popular
    ]
}


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return dict(self._payload)


@pytest.fixture
def connected_service():
    """Return a ListeningService pre-connected for user-1 via fake HTTP."""

    def fake_post(url, data, timeout=0):
        return _FakeResponse(200, {"access_token": "tok", "expires_in": 3600})

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/me"):
            return _FakeResponse(200, {"display_name": "Tester", "id": "sp_1"})
        if url.endswith("/top/tracks"):
            return _FakeResponse(200, _TOP_TRACKS_PAYLOAD)
        if "artist-1/related-artists" in url:
            return _FakeResponse(200, _RELATED_ARTISTS_ARTIST_1)
        if "artist-2/related-artists" in url:
            return _FakeResponse(200, _RELATED_ARTISTS_ARTIST_2)
        return _FakeResponse(200, {"items": []})

    svc = ListeningService(
        client_id="cid",
        redirect_uri="http://localhost:8080/callback",
        post_request=fake_post,
        get_request=fake_get,
    )
    # simulate an already-completed auth flow by injecting a live session
    import time
    svc._sessions["user-1"] = {
        "access_token": "tok",
        "expires_at": time.time() + 3600,
        "display_name": "Tester",
    }
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_recommendations_exclude_known_artists(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert "Big Artist" not in names
    assert "Medium Artist" not in names


def test_recommendations_filter_by_popularity(connected_service):
    recs = connected_service.get_artist_recommendations("user-1", popularity_max=60)
    for r in recs:
        assert r["popularity"] <= 60, f"{r['name']} has popularity {r['popularity']} > 60"


def test_recommendations_excludes_mainstream(connected_service):
    recs = connected_service.get_artist_recommendations("user-1", popularity_max=60)
    names = [r["name"] for r in recs]
    assert "Mainstream Star" not in names


def test_recommendations_sorted_ascending_by_popularity(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    pops = [r["popularity"] for r in recs]
    assert pops == sorted(pops), "Results should be sorted least popular first"


def test_recommendations_deduplicated(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert len(names) == len(set(names)), "Duplicate artists should be removed"


def test_recommendations_returns_expected_artists(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert "Hidden Gem" in names
    assert "Underground Act" in names
    assert "Niche Project" in names


def test_recommendations_max_results_respected(connected_service):
    recs = connected_service.get_artist_recommendations("user-1", max_results=2)
    assert len(recs) <= 2


def test_recommendations_includes_genres(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    hidden_gem = next(r for r in recs if r["name"] == "Hidden Gem")
    assert "indie" in hidden_gem["genres"]


def test_recommendations_requires_connection():
    svc = ListeningService(
        client_id="cid",
        redirect_uri="http://localhost:8080/callback",
    )
    with pytest.raises(SpotifyConnectionError, match="not connected"):
        svc.get_artist_recommendations("user-nobody")


def test_recommendations_fallback_when_threshold_too_low(connected_service):
    recs = connected_service.get_artist_recommendations("user-1", popularity_max=5)
    assert recs, "Expected fallback recommendations when strict threshold yields none"


def test_recommendations_fallback_to_recommendations_enrichment_when_related_empty():
    def fake_post(url, data, timeout=0):
        return _FakeResponse(200, {"access_token": "tok", "expires_in": 3600})

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/top/tracks"):
            return _FakeResponse(200, _TOP_TRACKS_PAYLOAD)
        if url.endswith("/top/artists"):
            return _FakeResponse(
                200,
                {
                    "items": [
                        {"id": "artist-1", "name": "Big Artist", "popularity": 80, "genres": ["pop"]},
                        {"id": "artist-2", "name": "Medium Artist", "popularity": 70, "genres": ["rock"]},
                    ]
                },
            )
        if "related-artists" in url:
            return _FakeResponse(200, {"artists": []})
        if url.endswith("/recommendations"):
            return _FakeResponse(
                200,
                {
                    "tracks": [
                        {"artists": [{"id": "ra-1", "name": "Hidden Seed"}]},
                        {"artists": [{"id": "artist-1", "name": "Big Artist"}]},
                    ]
                },
            )
        if url.endswith("/artists"):
            return _FakeResponse(
                200,
                {
                    "artists": [
                        {"id": "ra-1", "name": "Hidden Seed", "popularity": 23, "genres": ["indie"]},
                        {"id": "artist-1", "name": "Big Artist", "popularity": 80, "genres": ["pop"]},
                    ]
                },
            )
        return _FakeResponse(200, {"items": []})

    svc = ListeningService(
        client_id="cid",
        redirect_uri="http://localhost:8080/callback",
        post_request=fake_post,
        get_request=fake_get,
    )

    import time
    svc._sessions["user-1"] = {
        "access_token": "tok",
        "expires_at": time.time() + 3600,
        "display_name": "Tester",
    }

    recs = svc.get_artist_recommendations("user-1", max_results=5)
    names = [r["name"] for r in recs]

    assert recs
    assert "Hidden Seed" in names
    assert "Big Artist" not in names
