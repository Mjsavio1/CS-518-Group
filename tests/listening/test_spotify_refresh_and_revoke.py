import pytest
from class_demo.listening_service.listening_service import ListeningService, SpotifyConnectionError

class _FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
    def json(self):
        return self._payload

@pytest.fixture
def service_with_refresh_mocks():
    def fake_post(url, data, timeout=0):
        # handle refresh token exchange
        if data.get('grant_type') == 'refresh_token':
            return _FakeResp(200, {"access_token": "new-access", "expires_in": 3600, "refresh_token": "rotated-rt"})
        return _FakeResp(200, {"access_token": "access", "expires_in": 3600})

    def fake_get(url, headers=None, params=None, timeout=0):
        if url.endswith('/me'):
            return _FakeResp(200, {"display_name": "UserX", "id": "sp_user_1"})
        return _FakeResp(200, {"items": []})

    return ListeningService(client_id='cid', redirect_uri='http://localhost:8080/callback', post_request=fake_post, get_request=fake_get, client_secret='test-secret')


def test_refresh_session_with_refresh_token(service_with_refresh_mocks):
    ok = service_with_refresh_mocks.refresh_session_with_refresh_token('u1', 'stored-rt')
    assert ok is True
    assert service_with_refresh_mocks.is_connected('u1')


def test_refresh_requires_client_secret(monkeypatch):
    svc = ListeningService(client_id='cid', redirect_uri='http://localhost:8080/callback')
    monkeypatch.delenv('SPOTIFY_CLIENT_SECRET', raising=False)
    with pytest.raises(SpotifyConnectionError):
        svc.refresh_session_with_refresh_token('u1', 'rt')

