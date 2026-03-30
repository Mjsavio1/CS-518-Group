import os
import time
import subprocess
import requests
from pymongo import MongoClient
from src.class_demo.config import Config

# mark slow suite so developers can skip if desired
import pytest
pytestmark = pytest.mark.slow

API_HOST = "http://127.0.0.1:8000"


def start_server():
    # launch uvicorn using the same python interpreter
    return subprocess.Popen(
        [
            os.getenv("PYTHON", "python"),
            "-m",
            "uvicorn",
            "src.run_api:app",
            "--host",
            "127.0.0.1",
            "--port",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="module")
def api_server():
    # use an isolated database
    db_name = Config.MONGODB_DB_NAME + "_e2e"
    os.environ["MONGODB_DB_NAME"] = db_name
    client = MongoClient(Config.MONGODB_URI)
    client.drop_database(db_name)

    proc = start_server()
    # wait a moment for server to start
    time.sleep(1)
    yield
    proc.terminate()
    proc.wait(timeout=5)
    client.drop_database(db_name)


def create_admin():
    r = requests.post(
        f"{API_HOST}/users",
        json={
            "username": "admin",
            "email": "admin@e2e.com",
            "password": "pw",
            "role": "admin",
        },
    )
    r.raise_for_status()
    return r.json()


def login(username, password):
    r = requests.post(f"{API_HOST}/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["token"]


def test_e2e_flow(api_server):
    admin = create_admin()
    token = login("admin", "pw")
    headers = {"Authorization": f"Bearer {token}"}

    # admin creates normal user
    r = requests.post(
        f"{API_HOST}/users",
        json={"username": "bob", "email": "bob@e2e.com", "password": "pw"},
        headers=headers,
    )
    assert r.status_code == 200
    bob = r.json()

    # bob can login and fetch own record
    bob_token = login("bob", "pw")
    h2 = {"Authorization": f"Bearer {bob_token}"}
    r2 = requests.get(f"{API_HOST}/users/{bob['id']}", headers=h2)
    assert r2.status_code == 200
    assert r2.json()["username"] == "bob"

    # bob cannot list users
    r3 = requests.get(f"{API_HOST}/users", headers=h2)
    assert r3.status_code == 403

    # admin lists
    r4 = requests.get(f"{API_HOST}/users", headers=headers)
    assert r4.status_code == 200
    assert any(u['username'] == 'bob' for u in r4.json())

    # admin updates bob
    r5 = requests.put(
        f"{API_HOST}/users/{bob['id']}",
        json={"email": "changed@e2e.com"},
        headers=headers,
    )
    assert r5.status_code == 200
    assert r5.json()["email"] == "changed@e2e.com"

    # delete bob
    r6 = requests.delete(f"{API_HOST}/users/{bob['id']}", headers=headers)
    assert r6.status_code == 204

    # verify missing
    r7 = requests.get(f"{API_HOST}/users/{bob['id']}", headers=headers)
    assert r7.status_code == 404
