import unittest
import os
from pymongo import MongoClient
from dotenv import load_dotenv

from class_demo.user_service.service import UserService
from class_demo.user_service.repository import UserRepository
from class_demo.user_app.app_logic import AppLogic
from class_demo.user_service.models import UserRole

class TestAppLogicIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.db_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        cls.db_name = "test_db_app_logic"
        cls.client = MongoClient(cls.db_uri)
        cls.db = cls.client[cls.db_name]

    def setUp(self):
        # Clear database before each test
        self.db.users.delete_many({})
        
        # Initialize real layers
        self.repo = UserRepository(self.db["users"])
        self.service = UserService(self.repo)
        self.logic = AppLogic(self.service)

    def test_admin_seeding_logic(self):
        """Test that seeding creates an admin if one doesn't exist."""
        self.logic.seed_admin()
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        
        # Verify via repository (direct DB check for truth)
        user_doc = self.db.users.find_one({"username": admin_username})
        self.assertIsNotNone(user_doc)
        self.assertEqual(user_doc["role"], UserRole.admin)

    def test_login_flow(self):
        """Test the logic layer login flow with real hashing/auth."""
        # Setup: Create a user through the service
        self.service.create_user(None, {
            "username": "tester",
            "email": "test@example.com",
            "password": "securepassword",
            "role": UserRole.user
        })

        # Test valid login
        user = self.logic.login("tester", "securepassword")
        self.assertEqual(user.username, "tester")

        # Test invalid login
        with self.assertRaises(ValueError) as cm:
            self.logic.login("tester", "wrongpassword")
        self.assertEqual(str(cm.exception), "Invalid credentials provided.")

    def test_rbac_list_users(self):
        """Verify that logic layer enforces RBAC via the service."""
        # 1. Create an admin and a regular user
        admin = self.service.create_user(None, {
            "username": "adm", "email": "a@a.com", "password": "p", "role": "admin"
        })
        standard = self.service.create_user(None, {
            "username": "std", "email": "s@s.com", "password": "p", "role": "user"
        })

        # Admin should succeed
        users = self.logic.list_all_users(admin)
        self.assertGreaterEqual(len(users), 2)

        # Standard user should fail
        with self.assertRaises(PermissionError):
            self.logic.list_all_users(standard)

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db_name)
        cls.client.close()

if __name__ == "__main__":
    unittest.main()