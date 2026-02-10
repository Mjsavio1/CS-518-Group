"""User Repository for database operations."""

from typing import Dict, List, Optional, Any
import uuid
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, OperationFailure
from bson.objectid import ObjectId
from .models import User
from .mapper import db_to_model, model_to_db
from .repository_exceptions import (
    DuplicateUsernameError,
    DuplicateEmailError,
    UserNotFoundError,
    InvalidUserDataError,
    RepositoryError,
)


class UserRepository:
    """Repository class for managing User database operations.
    
    This class abstracts MongoDB database operations and provides a clean interface
    for CRUD operations on User entities. It handles validation and raises
    appropriate custom exceptions for error cases.
    """

    def __init__(self, collection: Collection):
        """Initialize the repository with a MongoDB collection.
        
        Args:
            collection: PyMongo collection instance for users.
            
        Raises:
            RepositoryError: If collection is invalid.
        """
        if not collection:
            raise RepositoryError("Collection cannot be None")
        
        self._collection = collection
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        """Create database indexes for efficient queries.
        
        Creates unique indexes on username and email fields.
        """
        try:
            self._collection.create_index("username", unique=True)
            self._collection.create_index("email", unique=True)
        except Exception as e:
            raise RepositoryError(f"Failed to create indexes: {str(e)}")

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
            # Assign ID if not present
            if not user.id:
                user.id = str(uuid.uuid4())
            
            # Convert to database document format
            doc = model_to_db(user)
            
            # Insert into database
            result = self._collection.insert_one(doc)
            user.id = str(result.inserted_id)
            
            return user
            
        except DuplicateKeyError as e:
            # Determine which field caused the duplicate
            error_msg = str(e)
            if "username" in error_msg:
                raise DuplicateUsernameError(user.username)
            elif "email" in error_msg:
                raise DuplicateEmailError(user.email)
            else:
                raise RepositoryError(f"Duplicate key error: {error_msg}")
        except Exception as e:
            if isinstance(e, (DuplicateUsernameError, DuplicateEmailError)):
                raise
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
            # Convert string ID to ObjectId if needed
            try:
                obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            except Exception:
                obj_id = user_id
            
            doc = self._collection.find_one({"_id": obj_id})
            
            if not doc:
                raise UserNotFoundError(user_id=user_id)
            
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
            doc = self._collection.find_one({"username": username})
            
            if not doc:
                raise UserNotFoundError(username=username)
            
            return db_to_model(doc)
            
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
            doc = self._collection.find_one({"email": email})
            
            if not doc:
                raise UserNotFoundError(email=email)
            
            return db_to_model(doc)
            
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
            # Convert string ID to ObjectId if needed
            try:
                obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            except Exception:
                obj_id = user_id
            
            # Check if user exists
            existing_doc = self._collection.find_one({"_id": obj_id})
            if not existing_doc:
                raise UserNotFoundError(user_id=user_id)
            
            existing = db_to_model(existing_doc)
            
            # Check for duplicate username if changed
            if user.username != existing.username:
                duplicate_user = self._collection.find_one({"username": user.username})
                if duplicate_user:
                    raise DuplicateUsernameError(user.username)
            
            # Check for duplicate email if changed
            if user.email != existing.email:
                duplicate_user = self._collection.find_one({"email": user.email})
                if duplicate_user:
                    raise DuplicateEmailError(user.email)
            
            # Ensure ID consistency
            user.id = user_id
            
            # Convert to database document format and update
            doc = model_to_db(user)
            self._collection.replace_one({"_id": obj_id}, doc)
            
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
            # Convert string ID to ObjectId if needed
            try:
                obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            except Exception:
                obj_id = user_id
            
            result = self._collection.delete_one({"_id": obj_id})
            
            if result.deleted_count == 0:
                raise UserNotFoundError(user_id=user_id)
            
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
            users = [db_to_model(doc) for doc in self._collection.find()]
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
        return self._collection.count_documents({"username": username}) > 0

    def exists_by_email(self, email: str) -> bool:
        """Check if a user with given email exists.
        
        Args:
            email: The email to check.
            
        Returns:
            True if user exists, False otherwise.
        """
        return self._collection.count_documents({"email": email}) > 0

    def count(self) -> int:
        """Get the total count of users in the database.
        
        Returns:
            The number of users.
        """
        return self._collection.count_documents({})
