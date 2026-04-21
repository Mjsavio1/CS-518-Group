"""Unit tests for the lesser-known artist recommendation algorithm."""
import time

import pytest

from class_demo.listening_service.listening_service import (
    ListeningService,
    SpotifyConnectionError,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

# Tracks include primary artists (top artists) and a feature artist (lesser-known)
_TOP_TRACKS_PAYLOAD = {
    "items": [
        {
            "name": "Track A",
            "artists": [
                {"id": "artist-1", "name": "Big Artist"},
                {"id": "feature-1", "name": "Hidden Gem"},
            ],
        },
        {
            "name": "Track B",
            "artists": [
                {"id": "artist-2", "name": "Medium Artist"},
                {"id": "feature-2", "name": "Niche Project"},
            ],
        },
        {
            "name": "Track C",
            "artists": [
                {"id": "artist-1", "name": "Big Artist"},
                {"id": "feature-3", "name": "Underground Act"},
            ],
        },
    ]
}

# Top artists – the "well-known" ones to exclude from recommendations
_TOP_ARTISTS_PAYLOAD = {
    "items": [
        {"id": "artist-1", "name": "Big Artist",    "popularity": 85, "genres": ["pop"]},
        {"id": "artist-2", "name": "Medium Artist", "popularity": 70, "genres": ["rock"]},
    ]
}

# Enrichment data returned by /v1/artists?ids=...
_ARTISTS_ENRICHMENT = {
    "artists": [
        {"id": "artist-1",  "name": "Big Artist",      "popularity": 85, "genres": ["pop"]},
        {"id": "feature-1", "name": "Hidden Gem",       "popularity": 30, "genres": ["indie", "folk"]},
        {"id": "artist-2",  "name": "Medium Artist",    "popularity": 70, "genres": ["rock"]},
        {"id": "feature-2", "name": "Niche Project",    "popularity": 25, "genres": ["ambient"]},
        {"id": "feature-3", "name": "Underground Act",  "popularity": 45, "genres": ["electronic"]},
    ]
}


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return dict(self._payload)


def _make_fake_get(tracks=None, top_artists=None, enrichment=None):
    """Build a fake GET function for the given payloads."""
    tracks = tracks or _TOP_TRACKS_PAYLOAD
    top_artists_payload = top_artists or _TOP_ARTISTS_PAYLOAD
    enrich = enrichment or _ARTISTS_ENRICHMENT

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/me"):
            return _FakeResponse(200, {"display_name": "Tester", "id": "sp_1"})
        if url.endswith("/top/tracks"):
            return _FakeResponse(200, tracks)
        if url.endswith("/top/artists"):
            return _FakeResponse(200, top_artists_payload)
        if url.endswith("/artists"):
            return _FakeResponse(200, enrich)
        return _FakeResponse(200, {"items": []})

    return fake_get


@pytest.fixture
def connected_service():
    """Return a ListeningService pre-connected for user-1 via fake HTTP."""

    def fake_post(url, data, timeout=0):
        return _FakeResponse(200, {"access_token": "tok", "expires_in": 3600})

    svc = ListeningService(
        client_id="cid",
        redirect_uri="http://localhost:8080/callback",
        post_request=fake_post,
        get_request=_make_fake_get(),
    )
    svc._sessions["user-1"] = {
        "access_token": "tok",
        "expires_at": time.time() + 3600,
        "display_name": "Tester",
    }
    return svc


def _connected_service_with(get_fn):
    def fake_post(url, data, timeout=0):
        return _FakeResponse(200, {"access_token": "tok", "expires_in": 3600})

    svc = ListeningService(
        client_id="cid",
        redirect_uri="http://localhost:8080/callback",
        post_request=fake_post,
        get_request=get_fn,
    )
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
        pop = r["popularity"]
        if pop is not None:
            assert pop <= 60, f"{r['name']} has popularity {pop} > 60"


def test_recommendations_sorted_ascending_by_popularity(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    pops = [r["popularity"] for r in recs if r["popularity"] is not None]
    assert pops == sorted(pops), "Results should be sorted least popular first"


def test_recommendations_deduplicated(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert len(names) == len(set(names)), "Duplicate artists should be removed"


def test_recommendations_returns_expected_artists(connected_service):
    recs = connected_service.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert "Hidden Gem" in names
    assert "Niche Project" in names
    assert "Underground Act" in names


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


def test_recommendations_works_across_multiple_time_ranges():
    """Artists only appearing in long_term tracks should still be found."""
    long_term_tracks = {
        "items": [
            {
                "name": "Old Fav",
                "artists": [
                    {"id": "old-artist-1", "name": "Forgotten Band"},
                ],
            }
        ]
    }

    call_count = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/top/tracks"):
            call_count["n"] += 1
            time_range = (params or {}).get("time_range", "")
            if time_range == "long_term":
                return _FakeResponse(200, long_term_tracks)
            return _FakeResponse(200, {"items": []})
        if url.endswith("/top/artists"):
            return _FakeResponse(200, {"items": []})
        if url.endswith("/artists"):
            return _FakeResponse(
                200,
                {
                    "artists": [
                        {"id": "old-artist-1", "name": "Forgotten Band", "popularity": 22, "genres": ["folk"]},
                    ]
                },
            )
        return _FakeResponse(200, {"items": []})

    svc = _connected_service_with(fake_get)
    recs = svc.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    assert "Forgotten Band" in names
    # Confirm all three time ranges were queried
    assert call_count["n"] == 3


def test_recommendations_handles_enrichment_failure_gracefully():
    """When /artists endpoint fails, results still use whatever data was collected."""

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/top/tracks"):
            return _FakeResponse(200, _TOP_TRACKS_PAYLOAD)
        if url.endswith("/top/artists"):
            return _FakeResponse(200, _TOP_ARTISTS_PAYLOAD)
        if url.endswith("/artists"):
            return _FakeResponse(500, {"error": {"status": 500}})
        return _FakeResponse(200, {"items": []})

    svc = _connected_service_with(fake_get)
    # Should not raise; returns empty list gracefully when enrichment fails
    recs = svc.get_artist_recommendations("user-1")
    assert isinstance(recs, list)


def test_recommendations_excludes_top_artists_from_all_time_ranges():
    """Top artists from long_term should also be excluded."""
    long_term_top_artists = {
        "items": [
            {"id": "feature-1", "name": "Hidden Gem", "popularity": 30, "genres": ["indie"]},
        ]
    }

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/top/tracks"):
            return _FakeResponse(200, _TOP_TRACKS_PAYLOAD)
        if url.endswith("/top/artists"):
            time_range = (params or {}).get("time_range", "")
            if time_range == "long_term":
                return _FakeResponse(200, long_term_top_artists)
            return _FakeResponse(200, _TOP_ARTISTS_PAYLOAD)
        if url.endswith("/artists"):
            return _FakeResponse(200, _ARTISTS_ENRICHMENT)
        return _FakeResponse(200, {"items": []})

    svc = _connected_service_with(fake_get)
    recs = svc.get_artist_recommendations("user-1")
    names = [r["name"] for r in recs]
    # Hidden Gem is now a top artist in long_term, so should be excluded
    assert "Hidden Gem" not in names

