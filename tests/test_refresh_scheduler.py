import os
import time
from types import SimpleNamespace

import pytest

# Keep imports local to avoid test import errors in environments missing deps
from class_demo.user_app.logic import AppLogic


class FakeRepo:
    def __init__(self, users):
        # users: dict id -> SimpleNamespace
        self._users = users

    def list_all(self):
        return list(self._users.values())

    def read(self, user_id):
        if user_id not in self._users:
            raise Exception("not found")
        return self._users[user_id]

    def update(self, user_id, user):
        self._users[user_id] = user
        return user


class FakeService:
    def __init__(self, repo):
        self._repo = repo

    def update_user(self, requester, user_id, updates):
        user = self._repo.read(user_id)
        for k, v in updates.items():
            setattr(user, k, v)
        self._repo.update(user_id, user)
        return user


class DummyResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_refresh_scheduler_rotates_and_persists(monkeypatch):
    # arrange
    os.environ["SPOTIFY_CLIENT_ID"] = "cid"
    os.environ["SPOTIFY_CLIENT_SECRET"] = "csecret"
    # don't set SPOTIFY_TOKEN_SECRET so logic falls back to base64 encoding

    # create fake user with encrypted refresh token via AppLogic.encrypt (base64 path)
    repo_users = {}
    fake_user = SimpleNamespace(
        id="u1",
        email="u1@example.com",
        username="u1",
        password="p",
        role="user",
        spotify_refresh_token=None,
        spotify_token_expires_at=0,
    )
    repo_users["u1"] = fake_user

    repo = FakeRepo(repo_users)
    service = FakeService(repo)
    logic = AppLogic(service)

    # set an initial refresh token (encrypted)
    enc = logic._encrypt_token("old_refresh")
    fake_user.spotify_refresh_token = enc
    fake_user.spotify_token_expires_at = time.time() - 10  # expired

    # mock requests.post to simulate spotify token endpoint returning a new refresh token
    def fake_post(url, data=None, timeout=None):
        assert url.endswith("/api/token")
        return DummyResp(200, {"access_token": "a", "expires_in": 3600, "refresh_token": "new_refresh"})

    monkeypatch.setattr("requests.post", fake_post)

    # act
    refreshed = logic.refresh_all_spotify_tokens(max_per_run=5)

    # assert
    assert refreshed == 1
    updated = repo._users["u1"]
    # decrypt stored token
    dec = logic._decrypt_token(updated.spotify_refresh_token)
    assert dec == "new_refresh"
    assert updated.spotify_token_expires_at > time.time()


if __name__ == "__main__":
    pytest.main([__file__])
