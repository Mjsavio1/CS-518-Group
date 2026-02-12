import os
import unittest
from pymongo import MongoClient
from class_demo.config import Config
from class_demo.user_service.repository import UserRepository
from class_demo.user_service.models import User, UserRole
from class_demo.user_service.repository_exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    UserNotFoundError,
)


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS") == "1",
    "Integration tests require RUN_INTEGRATION_TESTS=1"
)
class TestUserRepositoryIntegration(unittest.TestCase):
    """Integration tests for UserRepository using a live MongoDB instance."""

    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(Config.MONGODB_URI)
        cls.db_name = Config.MONGODB_DB_NAME + "_test_unittest"
        cls.db = cls.client[cls.db_name]
        cls.collection = cls.db["users"]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db_name)
        cls.client.close()

    def setUp(self):
        self.collection.delete_many({})
        self.collection.create_index("email", unique=True)
        self.repo = UserRepository(self.collection)

    def test_create_user(self):
        user = User(
            id="user-123",
            username="jdoe",
            email="john@example.com",
            role=UserRole.user,
            password="hashed_password",
        )

        created_user = self.repo.create(user)

        self.assertEqual(created_user.id, "user-123")
        self.assertEqual(created_user.email, "john@example.com")

        # Verify it exists in the database
        doc = self.collection.find_one({"_id": "user-123"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["username"], "jdoe")

    def test_create_duplicate_user(self):
        # create first user
        user1 = User(id="u1", username="u1", email="dup@example.com", role=UserRole.user, password="p1")
        user2 = User(id="u2", username="u2", email="dup@example.com", role=UserRole.user, password="p2")
        self.repo.create(user1)

        with self.assertRaises(DuplicateEmailError):
            self.repo.create(user2)

    def test_get_user_by_id(self):
        user = User(id="user-123", username="jdoe", email="john@example.com", role=UserRole.user, password="pw")
        self.repo.create(user)

        found_user = self.repo.read("user-123")
        self.assertEqual(found_user.id, "user-123")
        self.assertEqual(found_user.username, "jdoe")

    def test_get_user_by_id_not_found(self):
        with self.assertRaises(UserNotFoundError):
            self.repo.read("non-existent")

    def test_get_user_by_email(self):
        user = User(id="user-123", username="jdoe", email="john@example.com", role=UserRole.user, password="pw")
        self.repo.create(user)

        found_user = self.repo.read_by_email("john@example.com")
        self.assertEqual(found_user.id, "user-123")
        self.assertEqual(found_user.email, "john@example.com")

    def test_update_user(self):
        user = User(id="user-123", username="jdoe", email="john@example.com", role=UserRole.user, password="pw")
        self.repo.create(user)

        user.username = "jdoe_updated"
        updated_user = self.repo.update("user-123", user)

        self.assertEqual(updated_user.username, "jdoe_updated")

        # Verify db state
        doc = self.collection.find_one({"_id": "user-123"})
        self.assertEqual(doc["username"], "jdoe_updated")

    def test_delete_user(self):
        user = User(id="user-123", username="jdoe", email="john@example.com", role=UserRole.user, password="pw")
        self.repo.create(user)

        # delete should not raise
        self.repo.delete("user-123")

        with self.assertRaises(UserNotFoundError):
            self.repo.read("user-123")

    def test_list_all_users(self):
        users = [
            User(id="1", username="U1", email="u1@ex.com", role=UserRole.user, password="hash1"),
            User(id="2", username="U2", email="u2@ex.com", role=UserRole.user, password="hash2"),
        ]
        for u in users:
            self.repo.create(u)

        all_users = self.repo.list_all()
        self.assertEqual(len(all_users), 2)
        ids = [u.id for u in all_users]
        self.assertIn("1", ids)
        self.assertIn("2", ids)


if __name__ == "__main__":
    unittest.main()
