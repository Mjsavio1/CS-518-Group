import os
import time

import pytest
import requests

from class_demo.user_app.logic_api import ApiAppLogic

pytestmark = pytest.mark.slow

API_BASE_URL = os.getenv(
    "USER_API_BASE_URL",
    "https://user-api.whitebay-c606c597.eastus.azurecontainerapps.io",
)


def _login_token(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["token"]


def _create_user(payload: dict, token: str | None = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return requests.post(
        f"{API_BASE_URL}/users",
        json=payload,
        headers=headers,
        timeout=30,
    )


def _delete_user(user_id: str, token: str) -> None:
    requests.delete(
        f"{API_BASE_URL}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )


def test_msa_logic_e2e_live_user_api():
    suffix = str(int(time.time()))
    admin_username = f"msa_admin_{suffix}"
    user_username = f"msa_user_{suffix}"

    admin_payload = {
        "username": admin_username,
        "email": f"{admin_username}@example.com",
        "password": "pw",
        "role": "admin",
    }

    create_admin = _create_user(admin_payload)
    assert create_admin.status_code in (200, 409)

    admin_token = _login_token(admin_username, "pw")

    user_payload = {
        "username": user_username,
        "email": f"{user_username}@example.com",
        "password": "pw",
    }
    create_user = _create_user(user_payload, token=admin_token)
    assert create_user.status_code in (200, 409)

    logic = ApiAppLogic(API_BASE_URL)
    admin_user = logic.login(admin_username, "pw")
    normal_user = logic.login(user_username, "pw")

    all_users = logic.list_all_users(admin_user)
    matching = [u for u in all_users if u.username == user_username]
    assert matching
    target_user = matching[0]

    updated = logic.update_profile(
        requester=normal_user,
        user_id=target_user.id,
        email=f"{user_username}_changed@example.com",
        password=None,
    )
    assert updated.email == f"{user_username}_changed@example.com"

    _delete_user(target_user.id, admin_token)
