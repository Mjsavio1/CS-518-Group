"""Custom exceptions for User Repository operations."""


class UserServiceException(Exception):
    """Base exception for all User Service operations."""
    pass


class DuplicateUsernameError(UserServiceException):
    """Raised when attempting to create a user with a username that already exists."""
    
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username '{username}' already exists")


class DuplicateEmailError(UserServiceException):
    """Raised when attempting to create a user with an email that already exists."""
    
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already registered")


class DuplicateUserError(UserServiceException):
    """Compatibility exception raised when attempting to create a user that already exists."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"User '{identifier}' already exists")


class UserNotFoundError(UserServiceException):
    """Raised when attempting to read/update/delete a user that does not exist."""
    
    def __init__(self, user_id: str = None, username: str = None, email: str = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        
        if user_id:
            message = f"User with ID '{user_id}' not found"
        elif username:
            message = f"User with username '{username}' not found"
        elif email:
            message = f"User with email '{email}' not found"
        else:
            message = "User not found"
        
        super().__init__(message)


class InvalidUserDataError(UserServiceException):
    """Raised when user data validation fails."""
    
    def __init__(self, message: str):
        super().__init__(f"Invalid user data: {message}")


class RepositoryError(UserServiceException):
    """Raised when database/repository operations fail."""
    
    def __init__(self, message: str):
        super().__init__(f"Repository error: {message}")
