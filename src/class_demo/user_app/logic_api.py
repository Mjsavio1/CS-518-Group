from typing import Any, Dict, List, Optional

import requests

from ..user_service.models import User
from .interfaces import AppLogic as AppLogicInterface


class ApiAppLogic(AppLogicInterface):
	"""Alternate app logic that communicates with the deployed/local User API."""

	def __init__(self, api_base_url: str, timeout_seconds: int = 30):
		self.api_base_url = api_base_url.rstrip("/")
		self.timeout_seconds = timeout_seconds
		self._tokens_by_user_id: Dict[str, str] = {}
		self._tokens_by_username: Dict[str, str] = {}

	def seed_admin(self) -> None:
		payload = {
			"username": "admin",
			"email": "admin@example.com",
			"password": "admin123",
			"role": "admin",
		}
		response = requests.post(
			f"{self.api_base_url}/users",
			json=payload,
			timeout=self.timeout_seconds,
		)
		if response.status_code not in (200, 409):
			self._raise_for_http_error(response)

	def create_user(self, email: str, username: str, password: str) -> User:
		response = requests.post(
			f"{self.api_base_url}/users",
			json={
				"email": email,
				"username": username,
				"password": password,
				"role": "user",
			},
			timeout=self.timeout_seconds,
		)
		if response.status_code != 200:
			self._raise_for_http_error(response)

		return self._to_user(response.json())

	def login(self, username_or_email: str, password: str) -> User:
		auth_response = requests.post(
			f"{self.api_base_url}/login",
			json={"username": username_or_email, "password": password},
			timeout=self.timeout_seconds,
		)
		if auth_response.status_code != 200:
			raise ValueError("Invalid credentials provided.")

		token = auth_response.json().get("token")
		if not token:
			raise ValueError("Authentication failed: token missing in response.")

		me_response = requests.get(
			f"{self.api_base_url}/me",
			headers={"Authorization": f"Bearer {token}"},
			timeout=self.timeout_seconds,
		)
		if me_response.status_code != 200:
			self._raise_for_http_error(me_response)

		user = self._to_user(me_response.json())
		if user.id:
			self._tokens_by_user_id[user.id] = token
		self._tokens_by_username[user.username] = token
		return user

	def update_profile(self, requester: User, user_id: str, email: str, password: Optional[str]):
		updates = {"email": email}
		if password:
			updates["password"] = password

		response = requests.put(
			f"{self.api_base_url}/users/{user_id}",
			json=updates,
			headers=self._auth_headers_for(requester),
			timeout=self.timeout_seconds,
		)
		if response.status_code != 200:
			self._raise_for_http_error(response)

		return self._to_user(response.json())

	def list_all_users(self, admin: User) -> List[User]:
		response = requests.get(
			f"{self.api_base_url}/users",
			headers=self._auth_headers_for(admin),
			timeout=self.timeout_seconds,
		)
		if response.status_code == 403:
			raise PermissionError("Access denied: Administrator privileges required.")
		if response.status_code != 200:
			self._raise_for_http_error(response)

		return [self._to_user(item) for item in response.json()]

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

		response = requests.put(
			f"{self.api_base_url}/users/{user_id}",
			json=updates,
			headers=self._auth_headers_for(requester),
			timeout=self.timeout_seconds,
		)
		if response.status_code != 200:
			self._raise_for_http_error(response)

		return self._to_user(response.json())

	def update_spotify_tokens(
		self,
		requester: User,
		user_id: str,
		spotify_id: str | None,
		refresh_token: str | None,
		expires_at: float | None,
		display_name: str | None,
	) -> User:
		updates: Dict[str, object] = {}
		if spotify_id is not None:
			updates["spotify_id"] = spotify_id
		if refresh_token is not None:
			updates["spotify_refresh_token"] = refresh_token
		if expires_at is not None:
			updates["spotify_token_expires_at"] = expires_at
		if display_name is not None:
			updates["spotify_display_name"] = display_name

		response = requests.put(
			f"{self.api_base_url}/users/{user_id}",
			json=updates,
			headers=self._auth_headers_for(requester),
			timeout=self.timeout_seconds,
		)
		if response.status_code != 200:
			self._raise_for_http_error(response)

		return self._to_user(response.json())

	def disconnect_spotify(self, requester: User, user_id: str) -> User:
		response = requests.delete(
			f"{self.api_base_url}/users/{user_id}/spotify",
			headers=self._auth_headers_for(requester),
			timeout=self.timeout_seconds,
		)
		if response.status_code not in (200, 204):
			self._raise_for_http_error(response)
		# fetch updated user
		me = requests.get(f"{self.api_base_url}/me", headers=self._auth_headers_for(requester), timeout=self.timeout_seconds)
		if me.status_code != 200:
			self._raise_for_http_error(me)
		return self._to_user(me.json())

	def _auth_headers_for(self, user: User) -> Dict[str, str]:
		token: Optional[str] = None
		if user.id:
			token = self._tokens_by_user_id.get(user.id)
		if not token:
			token = self._tokens_by_username.get(user.username)
		if not token:
			raise ValueError("No API token available for requester. Login first.")
		return {"Authorization": f"Bearer {token}"}

	@staticmethod
	def _raise_for_http_error(response: requests.Response) -> None:
		try:
			detail = response.json().get("detail")
		except ValueError:
			detail = response.text
		message = detail or f"API error {response.status_code}"
		raise ValueError(message)

	@staticmethod
	def _to_user(payload: Dict[str, object]) -> User:
		normalized = dict(payload)
		normalized.setdefault("password", "")
		return User(**normalized)
