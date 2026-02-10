"""Unit tests for UserRepository happy path scenarios."""

import unittest
from unittest.mock import Mock, MagicMock
from bson.objectid import ObjectId
from src.class_demo.user_service.models import User
from src.class_demo.user_service.repository import UserRepository
from src.class_demo.user_service.repository_exceptions import RepositoryError


class TestUserRepositoryHappyPath(unittest.TestCase):
    """Test successful CRUD operations in UserRepository."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.mock_collection = Mock()
        self.repo = UserRepository(self.mock_collection)
        
        self.test_user = User(
            email="john@example.com",
            username="johndoe",
            password="hashedpassword123",
            role="user"
        )

    def test_create_user_success(self):
        """Test successful user creation."""
        # Arrange
        self.mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())
        
        # Act
        result = self.repo.create(self.test_user)
        
        # Assert
        self.assertIsNotNone(result.id)
        self.assertEqual(result.username, "johndoe")
        self.assertEqual(result.email, "john@example.com")
        self.mock_collection.insert_one.assert_called_once()

    def test_create_user_with_provided_id(self):
        """Test user creation with pre-assigned ID."""
        # Arrange
        self.test_user.id = "custom-id-123"
        self.mock_collection.insert_one.return_value = Mock(inserted_id="custom-id-123")
        
        # Act
        result = self.repo.create(self.test_user)
        
        # Assert
        self.assertEqual(result.id, "custom-id-123")
        self.mock_collection.insert_one.assert_called_once()

    def test_read_user_by_id_success(self):
        """Test successful user retrieval by ID."""
        # Arrange
        user_id = str(ObjectId())
        user_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "hashedpassword123",
            "role": "user"
        }
        self.mock_collection.find_one.return_value = user_doc
        
        # Act
        result = self.repo.read(user_id)
        
        # Assert
        self.assertEqual(result.username, "johndoe")
        self.assertEqual(result.email, "john@example.com")
        self.mock_collection.find_one.assert_called_once()

    def test_read_user_by_username_success(self):
        """Test successful user retrieval by username."""
        # Arrange
        user_doc = {
            "_id": ObjectId(),
            "username": "johndoe",
            "email": "john@example.com",
            "password": "hashedpassword123",
            "role": "user"
        }
        self.mock_collection.find_one.return_value = user_doc
        
        # Act
        result = self.repo.read_by_username("johndoe")
        
        # Assert
        self.assertEqual(result.username, "johndoe")
        self.assertEqual(result.email, "john@example.com")

    def test_read_user_by_email_success(self):
        """Test successful user retrieval by email."""
        # Arrange
        user_doc = {
            "_id": ObjectId(),
            "username": "johndoe",
            "email": "john@example.com",
            "password": "hashedpassword123",
            "role": "user"
        }
        self.mock_collection.find_one.return_value = user_doc
        
        # Act
        result = self.repo.read_by_email("john@example.com")
        
        # Assert
        self.assertEqual(result.username, "johndoe")
        self.assertEqual(result.email, "john@example.com")

    def test_update_user_success(self):
        """Test successful user update."""
        # Arrange
        user_id = str(ObjectId())
        existing_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "oldpassword",
            "role": "user"
        }
        # find_one is called 3 times: get existing, check username duplicate, check email duplicate
        self.mock_collection.find_one.side_effect = [
            existing_doc,  # Get existing user
            None,          # No duplicate username found
            None           # No duplicate email found
        ]
        
        updated_user = User(
            id=user_id,
            email="john.updated@example.com",
            username="johndoe",
            password="newpassword",
            role="admin"
        )
        
        # Act
        result = self.repo.update(user_id, updated_user)
        
        # Assert
        self.assertEqual(result.role, "admin")
        self.assertEqual(result.password, "newpassword")
        self.mock_collection.replace_one.assert_called_once()

    def test_update_user_username_success(self):
        """Test successful update of username."""
        # Arrange
        user_id = str(ObjectId())
        existing_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "password",
            "role": "user"
        }
        self.mock_collection.find_one.side_effect = [
            existing_doc,  # First call: get existing user
            None            # Second call: check for duplicate username
        ]
        
        updated_user = User(
            id=user_id,
            email="john@example.com",
            username="janedoe",
            password="password",
            role="user"
        )
        
        # Act
        result = self.repo.update(user_id, updated_user)
        
        # Assert
        self.assertEqual(result.username, "janedoe")
        self.mock_collection.replace_one.assert_called_once()

    def test_delete_user_success(self):
        """Test successful user deletion."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.delete_one.return_value = Mock(deleted_count=1)
        
        # Act
        self.repo.delete(user_id)
        
        # Assert
        self.mock_collection.delete_one.assert_called_once()

    def test_list_all_users_success(self):
        """Test successful retrieval of all users."""
        # Arrange
        docs = [
            {
                "_id": ObjectId(),
                "username": "johndoe",
                "email": "john@example.com",
                "password": "password",
                "role": "user"
            },
            {
                "_id": ObjectId(),
                "username": "janedoe",
                "email": "jane@example.com",
                "password": "password",
                "role": "admin"
            }
        ]
        self.mock_collection.find.return_value = docs
        
        # Act
        results = self.repo.list_all()
        
        # Assert
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].username, "johndoe")
        self.assertEqual(results[1].username, "janedoe")

    def test_list_all_users_empty(self):
        """Test retrieval when no users exist."""
        # Arrange
        self.mock_collection.find.return_value = []
        
        # Act
        results = self.repo.list_all()
        
        # Assert
        self.assertEqual(len(results), 0)

    def test_exists_by_username_success(self):
        """Test checking if user exists by username."""
        # Arrange
        self.mock_collection.count_documents.return_value = 1
        
        # Act
        exists = self.repo.exists_by_username("johndoe")
        
        # Assert
        self.assertTrue(exists)
        self.mock_collection.count_documents.assert_called_once_with({"username": "johndoe"})

    def test_exists_by_username_not_found(self):
        """Test checking non-existent username."""
        # Arrange
        self.mock_collection.count_documents.return_value = 0
        
        # Act
        exists = self.repo.exists_by_username("nonexistent")
        
        # Assert
        self.assertFalse(exists)

    def test_exists_by_email_success(self):
        """Test checking if user exists by email."""
        # Arrange
        self.mock_collection.count_documents.return_value = 1
        
        # Act
        exists = self.repo.exists_by_email("john@example.com")
        
        # Assert
        self.assertTrue(exists)
        self.mock_collection.count_documents.assert_called_once_with({"email": "john@example.com"})

    def test_exists_by_email_not_found(self):
        """Test checking non-existent email."""
        # Arrange
        self.mock_collection.count_documents.return_value = 0
        
        # Act
        exists = self.repo.exists_by_email("nonexistent@example.com")
        
        # Assert
        self.assertFalse(exists)

    def test_count_users_success(self):
        """Test counting total users."""
        # Arrange
        self.mock_collection.count_documents.return_value = 5
        
        # Act
        count = self.repo.count()
        
        # Assert
        self.assertEqual(count, 5)
        self.mock_collection.count_documents.assert_called_once_with({})

    def test_count_users_empty(self):
        """Test count when no users exist."""
        # Arrange
        self.mock_collection.count_documents.return_value = 0
        
        # Act
        count = self.repo.count()
        
        # Assert
        self.assertEqual(count, 0)

    def test_repository_initialization_with_none_collection(self):
        """Test that repository raises error with None collection."""
        # Arrange & Act & Assert
        with self.assertRaises(RepositoryError):
            UserRepository(None)

    def test_setup_indexes_called_on_init(self):
        """Test that indexes are created during initialization."""
        # Arrange
        mock_collection = Mock()
        
        # Act
        UserRepository(mock_collection)
        
        # Assert
        self.assertEqual(mock_collection.create_index.call_count, 2)


if __name__ == "__main__":
    unittest.main()
