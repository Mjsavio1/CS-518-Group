import sys
# tests live in workspace root; ensure src is on path so we import the
# package as a top-level module and avoid the duplicate-module problem.
sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, ANY

from src.run_api import app
from class_demo.user_service.models import User, UserRole
from class_demo.user_service import service_exceptions as svc_exc


@pytest.fixture
def mock_service():
    """Provide a MagicMock service and install it into FastAPI's overrides.

    FastAPI records the dependency function at route declaration time, so simply
    monkeypatching the name does not affect existing endpoints.  The
    ``dependency_overrides`` map is the supported mechanism for testing.
    """
    from class_demo.user_api import api

    svc = MagicMock()
    api.app.dependency_overrides[api.get_service] = lambda: svc
    # ensure any leftover tokens are cleared between tests
    api._token_store.clear()
    yield svc
    api.app.dependency_overrides.clear()


@pytest.fixture
def client(mock_service):
    """TestClient that uses the overridden service."""
    return TestClient(app)


def test_login_success(client, mock_service):
    user = User(id="u1", username="u1", email="u1@x.com", password="pw", role=UserRole.user)
    mock_service.authenticate.return_value = user
    r = client.post("/login", json={"username": "u1", "password": "pw"})
    assert r.status_code == 200
    assert "token" in r.json()
    # subsequent request using token should succeed (token stored in module)
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    mock_service.list_users.return_value = []
    r2 = client.get("/users", headers=headers)
    assert r2.status_code == 200


def test_login_bad_credentials(client, mock_service):
    mock_service.authenticate.side_effect = svc_exc.FailedAuthenticationError()
    r = client.post("/login", json={"username": "nope", "password": "pw"})
    assert r.status_code == 401


def test_create_user_anonymous(client, mock_service):
    # no auth header should still allow registration
    new = User(id="u2", username="u2", email="u2@x.com", password="hashed", role=UserRole.user)
    mock_service.create_user.return_value = new
    r = client.post("/users", json={"username": "u2", "email": "u2@x.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["username"] == "u2"
    # service called with requester None
    mock_service.create_user.assert_called_with(None, ANY)


def test_create_user_with_auth(client, mock_service):
    admin = User(id="admin", username="admin", email="a@b.com", password="pw", role=UserRole.admin)
    token = "tok"
    # inject directly into token store
    from class_demo.user_api import api
    api._token_store[token] = admin
    new = User(id="u3", username="u3", email="u3@x.com", password="h", role=UserRole.user)
    mock_service.create_user.return_value = new
    r = client.post(
        "/users",
        json={"username": "u3", "email": "u3@x.com", "password": "pw"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    mock_service.create_user.assert_called_with(admin, ANY)


def test_service_exceptions_map(client, mock_service):
    # configure service to raise different exceptions and confirm HTTP codes
    errors = [
        (svc_exc.UnauthorizedRequestError("u","x"), 403),
        (svc_exc.UserNotFoundError(user_id="u"), 404),
        (svc_exc.InvalidUserDataError("foo"), 400),
        (svc_exc.DuplicateUsernameError("u1"), 409),
    ]
    for exc, code in errors:
        mock_service.get_user.side_effect = exc
        token = "tt"
        from class_demo.user_api import api
        api._token_store[token] = User(id="u1", username="u1", email="u1@x.com", password="pw", role=UserRole.user)
        r = client.get("/users/u1", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == code
