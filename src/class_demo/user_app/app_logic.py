import os
from typing import List, Optional
from ..user_service.service import UserService
from ..user_service.models import User, UserRole
from ..user_service import service_exceptions as svc_exc

class AppLogic:
    def __init__(self, service: UserService):
        self.service = service

    def seed_admin(self):
        """Seed admin from .env using ONLY the service layer."""
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")

        try:
            # Check if admin exists via a mock authentication or lookup
            self.service.authenticate(admin_user, admin_pass)
        except (svc_exc.FailedAuthenticationError, svc_exc.UserNotFoundError):
            try:
                # Create if missing. Requester is None for initial seeding.
                self.service.create_user(None, {
                    "username": admin_user,
                    "email": admin_email,
                    "password": admin_pass,
                    "role": UserRole.admin
                })
            except svc_exc.DuplicateUsernameError:
                pass 

    def login(self, username_or_email: str, password: str) -> User:
        try:
            return self.service.authenticate(username_or_email, password)
        except svc_exc.FailedAuthenticationError:
            raise ValueError("Invalid credentials provided.")

    def update_profile(self, requester: User, user_id: str, email: str, password: Optional[str]):
        updates = {"email": email}
        if password:
            updates["password"] = password
        
        try:
            return self.service.update_user(requester, user_id, updates)
        except svc_exc.UserServiceError as e:
            raise ValueError(str(e))

    def list_all_users(self, admin: User) -> List[User]:
        try:
            return self.service.list_users(admin)
        except svc_exc.UnauthorizedRequestError:
            raise PermissionError("Access denied: Administrator privileges required.")