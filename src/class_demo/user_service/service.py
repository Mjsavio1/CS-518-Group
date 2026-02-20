"""Business logic layer for user operations.

Implements password hashing, authentication, role-based authorization,
requester checks, and logging. Translates repository exceptions into
service-specific errors.
"""

import logging
import os
import hashlib
import secrets
from typing import Any, Dict, Optional

from .models import User, UserRole
from . import repository as _repo_module
from . import repository_exceptions as repo_exc
from . import service_exceptions as svc_exc

# --- logging setup ----------------------------------------------------------
# logs directory adjacent to "src" (workspace root is three levels up)
LOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
)
os.makedirs(LOG_DIR, exist_ok=True)

_handler = logging.FileHandler(os.path.join(LOG_DIR, "user_service.log"))
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_handler.setFormatter(_formatter)

logger = logging.getLogger("user_service")
logger.setLevel(logging.DEBUG)
# avoid adding duplicate handlers if module reloaded
if not logger.handlers:
    logger.addHandler(_handler)

# --- helpers ---------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Return a salted hash for the given password.

    Uses SHA-256 + random hex salt.  Stored format is
    ``"{salt}${hash}"`` so that the salt is available for verification.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, hashed: str) -> bool:
    """Verify plain text password against stored salted hash."""
    try:
        salt, digest = hashed.split("$", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == digest


class UserService:
    """Service object that wraps a :class:`UserRepository` with
    higher level business rules.

    All methods that modify or view data take a ``requester`` argument;
    the value is typically the user performing the operation and is used
    to enforce role-based permissions.
    """

    def __init__(self, repository: _repo_module.UserRepository):
        if repository is None:
            raise svc_exc.ServiceError("Repository cannot be None")
        self._repo = repository
        self.logger = logger

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def create_user(self, requester: Optional[User], user_info: Dict[str, Any]) -> User:
        """Create a new user after applying business rules.

        ``requester`` is allowed to be ``None`` for self-registration;
        otherwise only admins may create other accounts.  Non-admin users
        may create/update themselves but not other identities.
        """
        self.logger.debug("create_user called by %s", getattr(requester, "username", None))

        if requester is not None and requester.role != UserRole.admin:
            # non-admins may only create an account for themselves
            if user_info.get("username") != requester.username:
                raise svc_exc.UnauthorizedRequestError(requester.id, "create user")

        # hash password before construction of model
        if "password" not in user_info:
            raise svc_exc.InvalidUserDataError("password is required")

        info = dict(user_info)
        info["password"] = _hash_password(info["password"])

        try:
            user = User(**info)
        except Exception as e:  # pydantic validation errors
            raise svc_exc.InvalidUserDataError(str(e)) from e

        try:
            return self._repo.create(user)
        except repo_exc.DuplicateUsernameError as e:
            raise svc_exc.DuplicateUsernameError(e.username) from e
        except repo_exc.DuplicateEmailError as e:
            raise svc_exc.DuplicateEmailError(e.email) from e
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

    def authenticate(self, username_or_email: str, password: str) -> User:
        """Verify credentials and return the corresponding ``User``.

        Raises :class:`service_exceptions.FailedAuthenticationError` when the
        credentials are invalid.
        """
        self.logger.debug("authenticate attempt for %s", username_or_email)

        # try lookup by username first, then email
        try:
            user = self._repo.read_by_username(username_or_email)
        except repo_exc.UserNotFoundError:
            try:
                user = self._repo.read_by_email(username_or_email)
            except repo_exc.UserNotFoundError:
                raise svc_exc.FailedAuthenticationError("invalid credentials")

        if not _verify_password(password, user.password):
            raise svc_exc.FailedAuthenticationError("invalid credentials")

        return user

    def get_user(self, requester: User, user_id: str) -> User:
        """Fetch a user by id with authorization checks.

        Admins may view anyone; ordinary users may only view their own record.
        """
        self.logger.debug("get_user %s by %s", user_id, requester.username)
        if requester.role != UserRole.admin and requester.id != user_id:
            raise svc_exc.UnauthorizedRequestError(requester.id, "view user")

        try:
            return self._repo.read(user_id)
        except repo_exc.UserNotFoundError as e:
            raise svc_exc.UserNotFoundError(user_id=user_id) from e
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

    def update_user(self, requester: User, user_id: str, updates: Dict[str, Any]) -> User:
        """Update fields of an existing user.

        Password values are automatically hashed.  Same authorization rules as
        :meth:`get_user` apply.
        """
        self.logger.debug("update_user %s by %s", user_id, requester.username)
        if requester.role != UserRole.admin and requester.id != user_id:
            raise svc_exc.UnauthorizedRequestError(requester.id, "update user")

        updated = dict(updates)
        if "password" in updated:
            updated["password"] = _hash_password(updated["password"])

        try:
            existing = self._repo.read(user_id)
        except repo_exc.UserNotFoundError as e:
            raise svc_exc.UserNotFoundError(user_id=user_id) from e
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

        # apply changes onto model instance
        for key, val in updated.items():
            setattr(existing, key, val)

        try:
            return self._repo.update(user_id, existing)
        except repo_exc.DuplicateUsernameError as e:
            raise svc_exc.DuplicateUsernameError(e.username) from e
        except repo_exc.DuplicateEmailError as e:
            raise svc_exc.DuplicateEmailError(e.email) from e
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

    def delete_user(self, requester: User, user_id: str) -> None:
        """Remove a user from the system.

        Only admins or the user themselves may delete the account.
        """
        self.logger.debug("delete_user %s by %s", user_id, requester.username)
        if requester.role != UserRole.admin and requester.id != user_id:
            raise svc_exc.UnauthorizedRequestError(requester.id, "delete user")

        try:
            self._repo.delete(user_id)
        except repo_exc.UserNotFoundError as e:
            raise svc_exc.UserNotFoundError(user_id=user_id) from e
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

    def list_users(self, requester: User):
        """Return all users; admin-only operation."""
        self.logger.debug("list_users by %s", requester.username)
        if requester.role != UserRole.admin:
            raise svc_exc.UnauthorizedRequestError(requester.id, "list users")

        try:
            return self._repo.list_all()
        except repo_exc.RepositoryError as e:
            raise svc_exc.RepositoryError(str(e)) from e

