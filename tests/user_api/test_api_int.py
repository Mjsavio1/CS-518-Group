import sys
# ensure package import works the same way as production code
sys.path.insert(0, "src")

import os
import unittest
from pymongo import MongoClient
from fastapi.testclient import TestClient

from src.run_api import app
from class_demo.config import Config
from class_demo.user_service.repository import UserRepository
from class_demo.user_service.service import UserService
from class_demo.user_service.models import User, UserRole
from class_demo.user_service.service_exceptions import (
    FailedAuthenticationError,
    UnauthorizedRequestError,
    UserNotFoundError,
)


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS") == "1",
    "Integration tests require RUN_INTEGRATION_TESTS=1",
)
class TestAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(Config.MONGODB_URI)
        cls.db_name = Config.MONGODB_DB_NAME + "_test_api"
        cls.db = cls.client[cls.db_name]
        cls.collection = cls.db["users"]
        # ensure the app uses the same database name for requests
        os.environ["MONGODB_DB_NAME"] = cls.db_name

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db_name)
        cls.client.close()

    def setUp(self):
        self.collection.delete_many({})
        # ensure repository indexes are created
        UserRepository(self.collection)
        self.service = UserService(UserRepository(self.collection))
        self.client = TestClient(app)
        # create an admin account via service directly
        self.admin = self.service.create_user(
            None,
            {"id": "admin", "username": "admin", "email": "admin@x.com", "password": "pw", "role": "admin"},
        )
        # log in to get token
        r = self.client.post("/login", json={"username": "admin", "password": "pw"})
        assert r.status_code == 200
        self.token = r.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_and_authenticate_cycle(self):
        # admin uses API to create a new user
        r = self.client.post(
            "/users",
            json={"username": "u1", "email": "u1@x.com", "password": "secret"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        uid = r.json()["id"]
        # authenticate via login endpoint
        r2 = self.client.post("/login", json={"username": "u1", "password": "secret"})
        self.assertEqual(r2.status_code, 200)
        token2 = r2.json()["token"]
        # use new token to fetch own record
        h2 = {"Authorization": f"Bearer {token2}"}
        r3 = self.client.get(f"/users/{uid}", headers=h2)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["username"], "u1")

    def test_list_and_authorization(self):
        # ordinary user cannot list
        user = self.service.create_user(self.admin, {"username": "u2", "email": "u2@x.com", "password": "pw"})
        r = self.client.post("/login", json={"username": "u2", "password": "pw"})
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        r2 = self.client.get("/users", headers=h)
        self.assertEqual(r2.status_code, 403)
        # admin can list
        r3 = self.client.get("/users", headers=self.headers)
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(len(r3.json()) >= 1)

    def test_update_and_delete(self):
        u = self.service.create_user(self.admin, {"username": "u3", "email": "u3@x.com", "password": "pw"})
        # update via API
        r = self.client.put(f"/users/{u.id}", json={"email": "new@x.com"}, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["email"], "new@x.com")
        # delete via API
        r2 = self.client.delete(f"/users/{u.id}", headers=self.headers)
        self.assertEqual(r2.status_code, 204)
        # trying to get should give 404
        r3 = self.client.get(f"/users/{u.id}", headers=self.headers)
        self.assertEqual(r3.status_code, 404)

    def test_auth_failures(self):
        r = self.client.get("/users", headers={})
        self.assertEqual(r.status_code, 401)
        r2 = self.client.get("/users/nonexistent", headers=self.headers)
        self.assertEqual(r2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
