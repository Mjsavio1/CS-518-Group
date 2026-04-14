from typing import List, Dict

from ...listening_service.listening_service import ListeningService


class ListeningController:
    """Controller that mediates between the GUI and the ListeningService."""

    def __init__(self, service: ListeningService | None = None):
        self.service = service or ListeningService()

    def get_greeting(self) -> str:
        return self.service.hello_world()

    def get_safety_notes(self) -> str:
        return self.service.get_connection_safety_notes()

    def start_secure_connection(self, user_id: str) -> str:
        return self.service.start_secure_connection(user_id)

    def complete_secure_connection(self, user_id: str, callback_url: str) -> Dict[str, str]:
        return self.service.complete_secure_connection(user_id, callback_url)

    def complete_secure_connection_from_params(
        self,
        user_id: str,
        code: str | None,
        state: str | None,
        error: str | None = None,
    ) -> Dict[str, str]:
        return self.service.complete_secure_connection_from_params(
            user_id=user_id,
            code=code,
            state=state,
            error=error,
        )

    def is_connected(self, user_id: str) -> bool:
        return self.service.is_connected(user_id)

    def disconnect(self, user_id: str) -> None:
        self.service.disconnect(user_id)

    def get_top_tracks(self, user, refresh_callback=None) -> List[Dict[str, str]]:
        """Attempt to return top tracks. If session missing and a refresh_callback
        is provided (callable that takes a user and returns a refresh token string),
        attempt to refresh session using the stored refresh token and retry.
        """
        try:
            return self.service.get_top_tracks(user_id=user.id)
        except Exception:
            # Try to recover using provided refresh callback
            if refresh_callback and user and getattr(user, "spotify_refresh_token", None):
                rt = refresh_callback(user)
                if rt:
                    # attempt to refresh the session in the service
                    self.service.refresh_session_with_refresh_token(user.id, rt)
                    return self.service.get_top_tracks(user_id=user.id)
            raise
