import os
import unittest
from pymongo import MongoClient

from src.class_demo.config import Config
from src.class_demo.user_service.repository import UserRepository
from src.class_demo.user_service.service import UserService
from src.class_demo.user_service.models import User, UserRole
from src.class_demo.user_service.service_exceptions import (
    FailedAuthenticationError,
    UnauthorizedRequestError,
    UserNotFoundError,
)


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS") == "1",
    "Integration tests require RUN_INTEGRATION_TESTS=1"
)
class TestUserServiceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(Config.MONGODB_URI)
        cls.db_name = Config.MONGODB_DB_NAME + "_test_service"
        cls.db = cls.client[cls.db_name]
        cls.collection = cls.db["users"]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db_name)
        cls.client.close()

    def setUp(self):
        self.collection.delete_many({})
        # indexes will be created by repo init
        repo = UserRepository(self.collection)
        self.service = UserService(repo)

        # create an admin user for tests and keep reference
        self.admin = self.service.create_user(None, {"id": "admin", "username": "admin", "email": "admin@x.com", "password": "pw", "role": "admin"})

    def test_create_and_authenticate(self):
        user = self.service.create_user(self.admin, {"id": "u1", "username": "u1", "email": "u1@x.com", "password": "secret"})
        self.assertEqual(user.id, "u1")
        # authenticate using username
        found = self.service.authenticate("u1", "secret")
        self.assertEqual(found.id, "u1")

    def test_failed_authentication(self):
        with self.assertRaises(FailedAuthenticationError):
            self.service.authenticate("noone", "pw")

    def test_authorization_rules(self):
        user = self.service.create_user(self.admin, {"id": "u2", "username": "u2", "email": "u2@x.com", "password": "pw"})
        # user cannot list
        with self.assertRaises(UnauthorizedRequestError):
            self.service.list_users(user)
        # admin can list
        all_users = self.service.list_users(self.admin)
        self.assertTrue(len(all_users) >= 1)
        # user cannot delete other
        with self.assertRaises(UnauthorizedRequestError):
            self.service.delete_user(user, self.admin.id)

    def test_get_update_delete_cycle(self):
        user = self.service.create_user(self.admin, {"id": "u3", "username": "u3", "email": "u3@x.com", "password": "pw"})
        got = self.service.get_user(self.admin, "u3")
        self.assertEqual(got.username, "u3")
        self.service.update_user(self.admin, "u3", {"email": "new@x.com"})
        updated = self.service.get_user(self.admin, "u3")
        self.assertEqual(updated.email, "new@x.com")
        self.service.delete_user(self.admin, "u3")
        with self.assertRaises(UserNotFoundError):
            self.service.get_user(self.admin, "u3")


if __name__ == "__main__":
    unittest.main()
