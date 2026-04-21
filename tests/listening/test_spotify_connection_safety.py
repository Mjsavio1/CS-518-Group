from urllib.parse import parse_qs, urlparse

import pytest

from class_demo.listening_service.listening_service import ListeningService, SpotifyConnectionError


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return dict(self._payload)


@pytest.fixture
def service_with_mocks():
    def fake_post(url, data, timeout):
        assert "code_verifier" in data
        assert data["grant_type"] == "authorization_code"
        return _FakeResponse(200, {"access_token": "token-123", "expires_in": 3600})

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/me"):
            return _FakeResponse(200, {"display_name": "Safety User"})
        return _FakeResponse(
            200,
            {
                "items": [
                    {
                        "name": "Track One",
                        "artists": [{"name": "Artist A"}],
                    },
                    {
                        "name": "Track Two",
                        "artists": [{"name": "Artist B"}, {"name": "Artist C"}],
                    },
                ]
            },
        )

    return ListeningService(
        client_id="spotify-client-id",
        redirect_uri="http://localhost:8080/callback",
        scope="user-top-read",
        post_request=fake_post,
        get_request=fake_get,
    )


def test_start_secure_connection_uses_pkce_and_state(service_with_mocks):
    auth_url = service_with_mocks.start_secure_connection("user-1")
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.spotify.com"
    assert params["response_type"][0] == "code"
    assert params["code_challenge_method"][0] == "S256"
    assert params["state"][0]


def test_complete_connection_requires_matching_state(service_with_mocks):
    auth_url = service_with_mocks.start_secure_connection("user-1")
    valid_state = parse_qs(urlparse(auth_url).query)["state"][0]

    with pytest.raises(SpotifyConnectionError):
        service_with_mocks.complete_secure_connection(
            "user-1",
            f"http://localhost:8080/callback?code=abc123&state={valid_state}-tampered",
        )


def test_complete_connection_and_fetch_tracks(service_with_mocks):
    auth_url = service_with_mocks.start_secure_connection("user-1")
    state = parse_qs(urlparse(auth_url).query)["state"][0]

    result = service_with_mocks.complete_secure_connection(
        "user-1",
        f"http://localhost:8080/callback?code=abc123&state={state}",
    )

    assert result["status"] == "connected"
    assert service_with_mocks.is_connected("user-1") is True

    tracks = service_with_mocks.get_top_tracks("user-1")
    assert len(tracks) == 2
    assert tracks[0]["title"] == "Track One"
    assert tracks[1]["artist"] == "Artist B, Artist C"


def test_complete_connection_from_params_success(service_with_mocks):
    auth_url = service_with_mocks.start_secure_connection("user-1")
    state = parse_qs(urlparse(auth_url).query)["state"][0]

    result = service_with_mocks.complete_secure_connection_from_params(
        user_id="user-1",
        code="abc123",
        state=state,
        error=None,
    )

    assert result["status"] == "connected"
    assert result["display_name"] == "Safety User"


def test_complete_connection_succeeds_when_profile_lookup_fails():
    def fake_post(url, data, timeout):
        return _FakeResponse(200, {"access_token": "token-123", "expires_in": 3600})

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith("/me"):
            return _FakeResponse(403, {"error": {"status": 403, "message": "Forbidden"}})
        return _FakeResponse(200, {"items": []})

    service = ListeningService(
        client_id="spotify-client-id",
        redirect_uri="http://localhost:8080/callback",
        scope="user-top-read",
        post_request=fake_post,
        get_request=fake_get,
    )

    auth_url = service.start_secure_connection("user-1")
    state = parse_qs(urlparse(auth_url).query)["state"][0]

    result = service.complete_secure_connection_from_params(
        user_id="user-1",
        code="abc123",
        state=state,
        error=None,
    )

    assert result["status"] == "connected"
    assert result["display_name"] == "Spotify User"


def test_complete_connection_from_params_error_rejected(service_with_mocks):
    service_with_mocks.start_secure_connection("user-1")
    with pytest.raises(SpotifyConnectionError):
        service_with_mocks.complete_secure_connection_from_params(
            user_id="user-1",
            code=None,
            state=None,
            error="access_denied",
        )


def test_missing_client_id_blocks_connect():
    service = ListeningService(client_id="", redirect_uri="http://localhost:8080/callback")
    with pytest.raises(SpotifyConnectionError):
        service.start_secure_connection("user-1")
