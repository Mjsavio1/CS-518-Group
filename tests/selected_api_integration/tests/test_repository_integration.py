import os
import unittest
from pymongo import MongoClient
from class_demo.config import Config
from class_demo.user_service.repository import UserRepository
from class_demo.user_service.models import User, UserRole
from class_demo.user_service.repository_exceptions import DuplicateUserError, UserNotFoundError


@unittest.skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS") == "1",
    "Integration tests require RUN_INTEGRATION_TESTS=1"
)
class TestUserRepositoryIntegration(unittest.TestCase):
    """Integration tests for UserRepository using a live MongoDB instance."""

    @classmethod
    def setUpClass(cls):
        """Set up the MongoDB client and test database once for all tests."""
        cls.client = MongoClient(Config.MONGODB_URI)
        cls.db_name = Config.MONGODB_DB_NAME + "_test_unittest"
        cls.db = cls.client[cls.db_name]
        cls.collection = cls.db["users"]

    @classmethod
    def tearDownClass(cls):
        """Drop the test database and close the connection."""
        cls.client.drop_database(cls.db_name)
        cls.client.close()

    def setUp(self):
        """Clean the collection before each test and ensure indexes."""
        self.collection.delete_many({})
        self.collection.create_index("email", unique=True)
        self.repo = UserRepository(self.collection)

    def test_create_user(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="hashed_password"
        )
        
        created_user = self.repo.create(user)
        
        self.assertEqual(created_user.id, "user-123")
        self.assertEqual(created_user.email, "john@example.com")
        
        # Verify it exists in the database
        doc = self.collection.find_one({"_id": "user-123"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["name"], "John Doe")

    def test_create_duplicate_user(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="password_hash"
        )
        self.repo.create(user)
        
        with self.assertRaises(DuplicateUserError):
            self.repo.create(user)

    def test_get_user_by_id(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="password_hash"
        )
        self.repo.create(user)
        
        found_user = self.repo.get_by_id("user-123")
        self.assertEqual(found_user.id, "user-123")
        self.assertEqual(found_user.name, "John Doe")

    def test_get_user_by_id_not_found(self):
        with self.assertRaises(UserNotFoundError):
            self.repo.get_by_id("non-existent")

    def test_get_user_by_email(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="password_hash"
        )
        self.repo.create(user)
        
        found_user = self.repo.get_by_email("john@example.com")
        self.assertEqual(found_user.id, "user-123")
        self.assertEqual(found_user.email, "john@example.com")

    def test_update_user(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="password_hash"
        )
        self.repo.create(user)
        
        user.name = "John Updated"
        updated_user = self.repo.update(user)
        
        self.assertEqual(updated_user.name, "John Updated")
        
        # Verify db state
        doc = self.collection.find_one({"_id": "user-123"})
        self.assertEqual(doc["name"], "John Updated")

    def test_delete_user(self):
        user = User(
            id="user-123",
            name="John Doe",
            email="john@example.com",
            role=UserRole.USER,
            password_hash="password_hash"
        )
        self.repo.create(user)
        
        result = self.repo.delete("user-123")
        self.assertTrue(result)
        
        with self.assertRaises(UserNotFoundError):
            self.repo.get_by_id("user-123")

    def test_list_all_users(self):
        users = [
            User(id="1", name="U1", email="u1@ex.com", role=UserRole.USER, password_hash="hash1"),
            User(id="2", name="U2", email="u2@ex.com", role=UserRole.USER, password_hash="hash2")
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
