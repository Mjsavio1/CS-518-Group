"""User Repository for database operations."""

from typing import Dict, List, Optional, Any
import uuid
from .models import User
from .mapper import db_to_model, model_to_db
from .exceptions import (
    DuplicateUsernameError,
    DuplicateEmailError,
    UserNotFoundError,
    InvalidUserDataError,
    RepositoryError,
)


class UserRepository:
    """Repository class for managing User database operations.
    
    This class abstracts database operations and provides a clean interface
    for CRUD operations on User entities. It handles validation and raises
    appropriate custom exceptions for error cases.
    """

    def __init__(self):
        """Initialize the repository with an in-memory storage.
        
        In a production environment, this would be replaced with actual
        database connection (MongoDB, PostgreSQL, etc.)
        """
        # In-memory storage for demo purposes
        self._storage: Dict[str, Dict[str, Any]] = {}
        # Indexes for quick lookups by username and email
        self._username_index: Dict[str, str] = {}  # username -> id
        self._email_index: Dict[str, str] = {}  # email -> id

    def create(self, user: User) -> User:
        """Create a new user in the database.
        
        Args:
            user: User model instance to create.
            
        Returns:
            The created User with assigned ID.
            
        Raises:
            DuplicateUsernameError: If username already exists.
            DuplicateEmailError: If email already exists.
            InvalidUserDataError: If user data is invalid.
            RepositoryError: If database operation fails.
        """
        try:
            # Check for duplicate username
            if user.username in self._username_index:
                raise DuplicateUsernameError(user.username)
            
            # Check for duplicate email
            if user.email in self._email_index:
                raise DuplicateEmailError(user.email)
            
            # Assign ID if not present
            if not user.id:
                user.id = str(uuid.uuid4())
            
            # Convert to database document format
            doc = model_to_db(user)
            
            # Store in database
            self._storage[user.id] = doc
            self._username_index[user.username] = user.id
            self._email_index[user.email] = user.id
            
            return user
            
        except (DuplicateUsernameError, DuplicateEmailError):
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to create user: {str(e)}")

    def read(self, user_id: str) -> User:
        """Retrieve a user by ID from the database.
        
        Args:
            user_id: The ID of the user to retrieve.
            
        Returns:
            The User model instance.
            
        Raises:
            UserNotFoundError: If user with given ID does not exist.
            RepositoryError: If database operation fails.
        """
        try:
            if user_id not in self._storage:
                raise UserNotFoundError(user_id=user_id)
            
            doc = self._storage[user_id]
            return db_to_model(doc)
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to read user: {str(e)}")

    def read_by_username(self, username: str) -> User:
        """Retrieve a user by username from the database.
        
        Args:
            username: The username of the user to retrieve.
            
        Returns:
            The User model instance.
            
        Raises:
            UserNotFoundError: If user with given username does not exist.
            RepositoryError: If database operation fails.
        """
        try:
            if username not in self._username_index:
                raise UserNotFoundError(username=username)
            
            user_id = self._username_index[username]
            return self.read(user_id)
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to read user by username: {str(e)}")

    def read_by_email(self, email: str) -> User:
        """Retrieve a user by email from the database.
        
        Args:
            email: The email of the user to retrieve.
            
        Returns:
            The User model instance.
            
        Raises:
            UserNotFoundError: If user with given email does not exist.
            RepositoryError: If database operation fails.
        """
        try:
            if email not in self._email_index:
                raise UserNotFoundError(email=email)
            
            user_id = self._email_index[email]
            return self.read(user_id)
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to read user by email: {str(e)}")

    def update(self, user_id: str, user: User) -> User:
        """Update an existing user in the database.
        
        Args:
            user_id: The ID of the user to update.
            user: The updated User model instance.
            
        Returns:
            The updated User model instance.
            
        Raises:
            UserNotFoundError: If user with given ID does not exist.
            DuplicateUsernameError: If new username already exists (not same user).
            DuplicateEmailError: If new email already exists (not same user).
            RepositoryError: If database operation fails.
        """
        try:
            # Check if user exists
            if user_id not in self._storage:
                raise UserNotFoundError(user_id=user_id)
            
            existing = db_to_model(self._storage[user_id])
            
            # Check for duplicate username if changed
            if user.username != existing.username:
                if user.username in self._username_index:
                    raise DuplicateUsernameError(user.username)
                # Update index
                del self._username_index[existing.username]
                self._username_index[user.username] = user_id
            
            # Check for duplicate email if changed
            if user.email != existing.email:
                if user.email in self._email_index:
                    raise DuplicateEmailError(user.email)
                # Update index
                del self._email_index[existing.email]
                self._email_index[user.email] = user_id
            
            # Ensure ID consistency
            user.id = user_id
            
            # Store updated document
            doc = model_to_db(user)
            self._storage[user_id] = doc
            
            return user
            
        except (UserNotFoundError, DuplicateUsernameError, DuplicateEmailError):
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to update user: {str(e)}")

    def delete(self, user_id: str) -> None:
        """Delete a user from the database.
        
        Args:
            user_id: The ID of the user to delete.
            
        Raises:
            UserNotFoundError: If user with given ID does not exist.
            RepositoryError: If database operation fails.
        """
        try:
            if user_id not in self._storage:
                raise UserNotFoundError(user_id=user_id)
            
            doc = self._storage[user_id]
            user = db_to_model(doc)
            
            # Remove from storage and indexes
            del self._storage[user_id]
            del self._username_index[user.username]
            del self._email_index[user.email]
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to delete user: {str(e)}")

    def list_all(self) -> List[User]:
        """Retrieve all users from the database.
        
        Returns:
            A list of all User model instances.
            
        Raises:
            RepositoryError: If database operation fails.
        """
        try:
            users = [db_to_model(doc) for doc in self._storage.values()]
            return users
        except Exception as e:
            raise RepositoryError(f"Failed to list users: {str(e)}")

    def exists_by_username(self, username: str) -> bool:
        """Check if a user with given username exists.
        
        Args:
            username: The username to check.
            
        Returns:
            True if user exists, False otherwise.
        """
        return username in self._username_index

    def exists_by_email(self, email: str) -> bool:
        """Check if a user with given email exists.
        
        Args:
            email: The email to check.
            
        Returns:
            True if user exists, False otherwise.
        """
        return email in self._email_index

    def count(self) -> int:
        """Get the total count of users in the database.
        
        Returns:
            The number of users.
        """
        return len(self._storage)
