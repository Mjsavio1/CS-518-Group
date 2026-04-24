import os
import time
import logging
from typing import Any, Dict, List, Optional

from ..user_service import service_exceptions as svc_exc
from ..user_service.models import User, UserRole
from ..user_service.service import UserService
from .interfaces import AppLogic as AppLogicInterface


class AppLogic(AppLogicInterface):
	"""App logic that talks directly to the local user service layer."""

	def __init__(self, service: UserService):
		self.service = service

		# logger for background refresh operations
		self._logger = logging.getLogger("app_logic")

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

	def create_user(self, email: str, username: str, password: str) -> User:
		try:
			return self.service.create_user(
				None,
				{
					"email": email,
					"username": username,
					"password": password,
					"role": UserRole.user,
				},
			)
		except svc_exc.DuplicateUsernameError:
			raise ValueError("That username is already in use.")
		except svc_exc.DuplicateEmailError:
			raise ValueError("That email is already registered.")
		except svc_exc.InvalidUserDataError as e:
			raise ValueError(str(e))
		except svc_exc.UserServiceError as e:
			raise ValueError(str(e))

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

	def update_user_data(
		self,
		requester: User,
		user_id: str,
		playlists: List[str],
		liked_songs: List[str],
		settings: Dict[str, Any],
	) -> User:
		updates = {
			"playlists": playlists,
			"liked_songs": liked_songs,
			"settings": settings,
		}

		try:
			return self.service.update_user(requester, user_id, updates)
		except svc_exc.UserServiceError as e:
			raise ValueError(str(e))

	def _get_token_secret(self) -> bytes | None:
		key = os.getenv("SPOTIFY_TOKEN_SECRET")
		if not key:
			return None
		return key.encode("utf-8")

	def _encrypt_token(self, token: str) -> str:
		if token is None:
			return ""
		key = self._get_token_secret()
		if key:
			try:
				from cryptography.fernet import Fernet
				f = Fernet(key)
				return f.encrypt(token.encode("utf-8")).decode("utf-8")
			except Exception:
				pass
		import base64
		return base64.b64encode(token.encode("utf-8")).decode("utf-8")

	def _decrypt_token(self, token_enc: str) -> str | None:
		if not token_enc:
			return None
		key = self._get_token_secret()
		if key:
			try:
				from cryptography.fernet import Fernet
				f = Fernet(key)
				return f.decrypt(token_enc.encode("utf-8")).decode("utf-8")
			except Exception:
				pass
		import base64
		try:
			return base64.b64decode(token_enc.encode("utf-8")).decode("utf-8")
		except Exception:
			return None

	def get_decrypted_refresh_token(self, requester: User, user_id: str) -> str | None:
		# authorization check: requester must be admin or the same user
		user = self.service.get_user(requester, user_id)
		enc = getattr(user, "spotify_refresh_token", None)
		return self._decrypt_token(enc) if enc else None

	def refresh_spotify_access(self, requester: User, user_id: str) -> str | None:
		# Use stored refresh token to obtain new access token and persist rotated refresh token
		rt = self.get_decrypted_refresh_token(requester, user_id)
		if not rt:
			raise ValueError("No refresh token available for user")

		client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
		if not client_secret:
			raise ValueError("SPOTIFY_CLIENT_SECRET not configured on server")

		# exchange refresh token
		import requests
		resp = requests.post(
			"https://accounts.spotify.com/api/token",
			data={
				"grant_type": "refresh_token",
				"refresh_token": rt,
				"client_id": os.getenv("SPOTIFY_CLIENT_ID", ""),
				"client_secret": client_secret,
			},
			timeout=15,
		)
		if resp.status_code != 200:
			raise ValueError("Failed to refresh spotify token")

		payload = resp.json()
		access = payload.get("access_token")
		expires_in = int(payload.get("expires_in", 3600))
		new_rt = payload.get("refresh_token")
		expires_at = time.time() + max(expires_in - 30, 30)

		# persist rotated refresh token if present, and update expires
		try:
			self.update_spotify_tokens(
				requester=requester,
				user_id=user_id,
				spotify_id=None,
				refresh_token=new_rt or rt,
				expires_at=expires_at,
				display_name=None,
			)
		except Exception:
			pass

		return access

	def refresh_all_spotify_tokens(self, max_per_run: int | None = None) -> int:
		"""Refresh Spotify access/refresh tokens for all users who look close to expiry.

		This method is intended to be run from a background worker. It will iterate
		all users in the repository, attempt a refresh for those with a stored
		refresh token and persist any rotated refresh tokens and new expiry times.

		Returns the number of users successfully refreshed.
		"""
		# PKCE/public-client refresh flow: do not require client_secret.
		client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
		if not client_id:
			self._logger.debug("SPOTIFY_CLIENT_ID not configured; skipping background refresh")
			return 0

		count = 0
		# fetch users
		try:
			users = self.service._repo.list_all()
		except Exception as e:
			self._logger.exception("failed to list users for refresh: %s", e)
			return 0

		now = time.time()
		for u in users:
			if max_per_run is not None and count >= max_per_run:
				break
			enc = getattr(u, "spotify_refresh_token", None)
			expires_at = getattr(u, "spotify_token_expires_at", None) or 0
			# refresh if expiry is missing or within 5 minutes
			if not enc or (expires_at and expires_at > now + 300):
				continue

			rt = self._decrypt_token(enc)
			if not rt:
				continue

			# attempt token exchange per-user
			try:
				import requests
				resp = requests.post(
					"https://accounts.spotify.com/api/token",
					data={
						"grant_type": "refresh_token",
						"refresh_token": rt,
						"client_id": client_id,
					},
					timeout=15,
				)
				if resp.status_code != 200:
					self._logger.warning("failed refresh for user %s: status %s", getattr(u, "id", "<nil>"), resp.status_code)
					continue
				payload = resp.json()
				new_rt = payload.get("refresh_token")
				expires_in = int(payload.get("expires_in", 3600))
				expires_at = time.time() + max(expires_in - 30, 30)

				# persist rotated token
				try:
					admin_user = User(id="system", username="system", email="system@example.com", password="", role=UserRole.admin)
					self.update_spotify_tokens(
						requester=admin_user,
						user_id=u.id,
						spotify_id=None,
						refresh_token=new_rt or rt,
						expires_at=expires_at,
						display_name=None,
					)
					count += 1
				except Exception:
					self._logger.exception("failed to persist rotated token for %s", getattr(u, "id", "<nil>"))
			except Exception:
				self._logger.exception("failed to refresh token for %s", getattr(u, "id", "<nil>"))

		return count

	def update_spotify_tokens(
		self,
		requester: User,
		user_id: str,
		spotify_id: str | None,
		refresh_token: str | None,
		expires_at: float | None,
		display_name: str | None,
	) -> User:
		updates: Dict[str, Any] = {}
		if spotify_id is not None:
			updates["spotify_id"] = spotify_id
		if refresh_token is not None:
			updates["spotify_refresh_token"] = self._encrypt_token(refresh_token)
		if expires_at is not None:
			updates["spotify_token_expires_at"] = expires_at
		if display_name is not None:
			updates["spotify_display_name"] = display_name

		try:
			return self.service.update_user(requester, user_id, updates)
		except svc_exc.UserServiceError as e:
			raise ValueError(str(e))
