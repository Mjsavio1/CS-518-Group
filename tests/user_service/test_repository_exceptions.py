"""Unit tests for UserRepository exception handling."""

import unittest
from unittest.mock import Mock
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from src.class_demo.user_service.models import User
from src.class_demo.user_service.repository import UserRepository
from src.class_demo.user_service.repository_exceptions import (
    DuplicateUsernameError,
    DuplicateEmailError,
    UserNotFoundError,
    RepositoryError,
    UserServiceException,
)


class TestUserRepositoryExceptions(unittest.TestCase):
    """Test exception handling in UserRepository."""

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

    # ===== CREATE OPERATION EXCEPTIONS =====

    def test_create_duplicate_username_error(self):
        """Test DuplicateUsernameError raised on duplicate username."""
        # Arrange
        error = DuplicateKeyError("duplicate key error collection: users index: username_1")
        self.mock_collection.insert_one.side_effect = error
        
        # Act & Assert
        with self.assertRaises(DuplicateUsernameError) as context:
            self.repo.create(self.test_user)
        
        self.assertEqual(context.exception.username, "johndoe")
        self.assertIn("johndoe", str(context.exception))

    def test_create_duplicate_email_error(self):
        """Test DuplicateEmailError raised on duplicate email."""
        # Arrange
        error = DuplicateKeyError("duplicate key error collection: users index: email_1")
        self.mock_collection.insert_one.side_effect = error
        
        # Act & Assert
        with self.assertRaises(DuplicateEmailError) as context:
            self.repo.create(self.test_user)
        
        self.assertEqual(context.exception.email, "john@example.com")
        self.assertIn("john@example.com", str(context.exception))

    def test_create_unexpected_error(self):
        """Test RepositoryError raised on unexpected database error."""
        # Arrange
        self.mock_collection.insert_one.side_effect = Exception("Database connection failed")
        
        # Act & Assert
        with self.assertRaises(RepositoryError):
            self.repo.create(self.test_user)

    # ===== READ OPERATION EXCEPTIONS =====

    def test_read_user_not_found_error(self):
        """Test UserNotFoundError raised when reading non-existent user."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.find_one.return_value = None
        
        # Act & Assert
        with self.assertRaises(UserNotFoundError) as context:
            self.repo.read(user_id)
        
        self.assertEqual(context.exception.user_id, user_id)
        self.assertIn(user_id, str(context.exception))

    def test_read_by_username_not_found_error(self):
        """Test UserNotFoundError raised when username not found."""
        # Arrange
        self.mock_collection.find_one.return_value = None
        
        # Act & Assert
        with self.assertRaises(UserNotFoundError) as context:
            self.repo.read_by_username("nonexistent")
        
        self.assertEqual(context.exception.username, "nonexistent")
        self.assertIn("nonexistent", str(context.exception))

    def test_read_by_email_not_found_error(self):
        """Test UserNotFoundError raised when email not found."""
        # Arrange
        self.mock_collection.find_one.return_value = None
        
        # Act & Assert
        with self.assertRaises(UserNotFoundError) as context:
            self.repo.read_by_email("nonexistent@example.com")
        
        self.assertEqual(context.exception.email, "nonexistent@example.com")
        self.assertIn("nonexistent@example.com", str(context.exception))

    def test_read_unexpected_error(self):
        """Test RepositoryError raised on unexpected read error."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.find_one.side_effect = Exception("Database error")
        
        # Act & Assert
        with self.assertRaises(RepositoryError):
            self.repo.read(user_id)

    # ===== UPDATE OPERATION EXCEPTIONS =====

    def test_update_user_not_found_error(self):
        """Test UserNotFoundError raised when updating non-existent user."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.find_one.return_value = None
        
        # Act & Assert
        with self.assertRaises(UserNotFoundError) as context:
            self.repo.update(user_id, self.test_user)
        
        self.assertEqual(context.exception.user_id, user_id)

    def test_update_duplicate_username_error(self):
        """Test DuplicateUsernameError raised when updating to duplicate username."""
        # Arrange
        user_id = str(ObjectId())
        existing_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "password",
            "role": "user"
        }
        
        # find_one called twice: first for existing user, second for duplicate check
        self.mock_collection.find_one.side_effect = [
            existing_doc,  # First: get existing user
            {"_id": str(ObjectId()), "username": "janedoe"}  # Second: duplicate found
        ]
        
        updated_user = User(
            id=user_id,
            email="john@example.com",
            username="janedoe",  # Different username
            password="password",
            role="user"
        )
        
        # Act & Assert
        with self.assertRaises(DuplicateUsernameError) as context:
            self.repo.update(user_id, updated_user)
        
        self.assertEqual(context.exception.username, "janedoe")

    def test_update_duplicate_email_error(self):
        """Test DuplicateEmailError raised when updating to duplicate email."""
        # Arrange
        user_id = str(ObjectId())
        existing_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "password",
            "role": "user"
        }
        
        # find_one called twice: first for existing user, second for duplicate email check
        self.mock_collection.find_one.side_effect = [
            existing_doc,  # First: get existing user
            {"_id": str(ObjectId()), "email": "jane@example.com"}  # Second: duplicate email found
        ]
        
        updated_user = User(
            id=user_id,
            email="jane@example.com",  # Different email that already exists
            username="johndoe",
            password="password",
            role="user"
        )
        
        # Act & Assert
        with self.assertRaises(DuplicateEmailError) as context:
            self.repo.update(user_id, updated_user)
        
        self.assertEqual(context.exception.email, "jane@example.com")

    def test_update_unexpected_error(self):
        """Test RepositoryError raised on unexpected update error."""
        # Arrange
        user_id = str(ObjectId())
        existing_doc = {
            "_id": user_id,
            "username": "johndoe",
            "email": "john@example.com",
            "password": "password",
            "role": "user"
        }
        self.mock_collection.find_one.return_value = existing_doc
        self.mock_collection.replace_one.side_effect = Exception("Database error")
        
        # Act & Assert
        with self.assertRaises(RepositoryError):
            self.repo.update(user_id, self.test_user)

    # ===== DELETE OPERATION EXCEPTIONS =====

    def test_delete_user_not_found_error(self):
        """Test UserNotFoundError raised when deleting non-existent user."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.delete_one.return_value = Mock(deleted_count=0)
        
        # Act & Assert
        with self.assertRaises(UserNotFoundError) as context:
            self.repo.delete(user_id)
        
        self.assertEqual(context.exception.user_id, user_id)

    def test_delete_unexpected_error(self):
        """Test RepositoryError raised on unexpected delete error."""
        # Arrange
        user_id = str(ObjectId())
        self.mock_collection.delete_one.side_effect = Exception("Database error")
        
        # Act & Assert
        with self.assertRaises(RepositoryError):
            self.repo.delete(user_id)

    # ===== LIST ALL OPERATION EXCEPTIONS =====

    def test_list_all_unexpected_error(self):
        """Test RepositoryError raised on list all error."""
        # Arrange
        self.mock_collection.find.side_effect = Exception("Database error")
        
        # Act & Assert
        with self.assertRaises(RepositoryError):
            self.repo.list_all()

    # ===== EXCEPTION HIERARCHY TESTS =====

    def test_duplicate_username_error_is_user_service_exception(self):
        """Test that DuplicateUsernameError inherits from UserServiceException."""
        # Arrange
        error = DuplicateUsernameError("test")
        
        # Assert
        self.assertIsInstance(error, UserServiceException)

    def test_duplicate_email_error_is_user_service_exception(self):
        """Test that DuplicateEmailError inherits from UserServiceException."""
        # Arrange
        error = DuplicateEmailError("test@example.com")
        
        # Assert
        self.assertIsInstance(error, UserServiceException)

    def test_user_not_found_error_is_user_service_exception(self):
        """Test that UserNotFoundError inherits from UserServiceException."""
        # Arrange
        error = UserNotFoundError(user_id="test-id")
        
        # Assert
        self.assertIsInstance(error, UserServiceException)

    def test_repository_error_is_user_service_exception(self):
        """Test that RepositoryError inherits from UserServiceException."""
        # Arrange
        error = RepositoryError("test error")
        
        # Assert
        self.assertIsInstance(error, UserServiceException)

    # ===== EXCEPTION MESSAGE TESTS =====

    def test_duplicate_username_error_message(self):
        """Test DuplicateUsernameError message format."""
        # Arrange
        username = "johndoe"
        
        # Act
        error = DuplicateUsernameError(username)
        
        # Assert
        self.assertIn(username, str(error))
        self.assertIn("already exists", str(error))

    def test_duplicate_email_error_message(self):
        """Test DuplicateEmailError message format."""
        # Arrange
        email = "john@example.com"
        
        # Act
        error = DuplicateEmailError(email)
        
        # Assert
        self.assertIn(email, str(error))
        self.assertIn("already registered", str(error))

    def test_user_not_found_by_id_message(self):
        """Test UserNotFoundError message when initialized with ID."""
        # Arrange
        user_id = "test-id"
        
        # Act
        error = UserNotFoundError(user_id=user_id)
        
        # Assert
        self.assertIn(user_id, str(error))
        self.assertIn("not found", str(error))

    def test_user_not_found_by_username_message(self):
        """Test UserNotFoundError message when initialized with username."""
        # Arrange
        username = "johndoe"
        
        # Act
        error = UserNotFoundError(username=username)
        
        # Assert
        self.assertIn(username, str(error))
        self.assertIn("not found", str(error))

    def test_user_not_found_by_email_message(self):
        """Test UserNotFoundError message when initialized with email."""
        # Arrange
        email = "john@example.com"
        
        # Act
        error = UserNotFoundError(email=email)
        
        # Assert
        self.assertIn(email, str(error))
        self.assertIn("not found", str(error))

    def test_repository_error_message(self):
        """Test RepositoryError message format."""
        # Arrange
        message = "Connection timeout"
        
        # Act
        error = RepositoryError(message)
        
        # Assert
        self.assertIn(message, str(error))
        self.assertIn("Repository error", str(error))


if __name__ == "__main__":
    unittest.main()
