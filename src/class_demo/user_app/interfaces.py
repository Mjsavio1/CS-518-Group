from abc import ABC, abstractmethod
from typing import List, Optional

from ..user_service.models import User


class AppLogic(ABC):
    @abstractmethod
    def seed_admin(self) -> None:
        """Seed an initial administrator account when needed."""

    @abstractmethod
    def login(self, username_or_email: str, password: str) -> User:
        """Authenticate and return the current user."""

    @abstractmethod
    def update_profile(self, requester: User, user_id: str, email: str, password: Optional[str]):
        """Update a user's profile details."""

    @abstractmethod
    def list_all_users(self, admin: User) -> List[User]:
        """Return all users for an admin requester."""
