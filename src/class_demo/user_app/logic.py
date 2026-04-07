import os
from typing import List, Optional

from ..user_service import service_exceptions as svc_exc
from ..user_service.models import User, UserRole
from ..user_service.service import UserService
from .interfaces import AppLogic as AppLogicInterface


class AppLogic(AppLogicInterface):
	"""App logic that talks directly to the local user service layer."""

	def __init__(self, service: UserService):
		self.service = service

	def seed_admin(self) -> None:
		admin_user = os.getenv("ADMIN_USERNAME", "admin")
		admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
		admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")

		try:
			self.service.authenticate(admin_user, admin_pass)
		except (svc_exc.FailedAuthenticationError, svc_exc.UserNotFoundError):
			try:
				self.service.create_user(
					None,
					{
						"username": admin_user,
						"email": admin_email,
						"password": admin_pass,
						"role": UserRole.admin,
					},
				)
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
