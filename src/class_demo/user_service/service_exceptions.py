"""Exceptions specific to the business logic layer (UserService).

The service layer sits on top of the repository and therefore wraps a
subset of repository exceptions (duplication, not‑found, etc.) while
also introducing higher‑level error classes such as authentication and
authorization failures.
"""

from typing import Optional

# base class for all service errors
class UserServiceError(Exception):
    """Base exception for UserService operations."""
    pass


# repository-related errors are re-defined here at the service level so
# that clients of the service need not import repository_exceptions.
class DuplicateUsernameError(UserServiceError):
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username '{username}' already exists")


class DuplicateEmailError(UserServiceError):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already registered")


class UserNotFoundError(UserServiceError):
    def __init__(self, user_id: Optional[str] = None, username: Optional[str] = None, email: Optional[str] = None):
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


class RepositoryError(UserServiceError):
    def __init__(self, message: str):
        super().__init__(f"Repository error: {message}")


# business-specific errors
class AuthenticationError(UserServiceError):
    """Base class for authentication related failures."""
    pass


class FailedAuthenticationError(AuthenticationError):
    def __init__(self, message: str = "authentication failed"):
        super().__init__(message)


class AuthorizationError(UserServiceError):
    """Base class for authorization failures."""
    pass


class UnauthorizedRequestError(AuthorizationError):
    def __init__(self, user_id: Optional[str], action: str):
        self.user_id = user_id
        self.action = action
        super().__init__(f"User '{user_id}' not authorized to {action}")


class InvalidUserDataError(UserServiceError):
    def __init__(self, message: str):
        super().__init__(f"Invalid user data: {message}")
