from typing import List, Dict
import requests

from ...listening_service.listening_service import ListeningService


class ListeningController:
    """Controller that mediates between the GUI and the ListeningService."""

    def __init__(self, service: ListeningService | None = None):
        self.service = service or ListeningService()

    def get_greeting(self) -> str:
        return self.service.hello_world()

    def get_top_tracks(self) -> List[Dict[str, str]]:
        return self.service.get_sample_top_tracks()

    def play_pause(self):
        """Toggle play/pause for the current track."""
        url = "https://api.spotify.com/v1/me/player/pause"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        requests.put(url, headers=headers)

    def skip_back(self):
        """Skip to the previous track."""
        url = "https://api.spotify.com/v1/me/player/next"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        requests.post(url, headers=headers)

    def skip_forward(self):
        """Skip to the next track."""
        url = "https://api.spotify.com/v1/me/player/previous"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        requests.post(url, headers=headers)

    def set_volume(self, volume_percent: int):
        """Set Spotify playback volume (0-100)."""
        url = f"https://api.spotify.com/v1/me/player/volume?volume_percent={volume_percent}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(url, headers=headers)
        if response.status_code != 204:
            print(f"Failed to set volume: {response.status_code} {response.text}")

    def get_playback_info(self):
        """Get current playback position and duration from Spotify."""
        url = "https://api.spotify.com/v1/me/player/currently-playing"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            progress_ms = data['progress_ms']
            duration_ms = data['item']['duration_ms']
            return progress_ms // 1000, duration_ms // 1000  # return in seconds
        return None, None

        # TODO: Integrate with Spotify API or playback backend
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

    def get_access_token(self, user_id: str) -> str | None:
        """Return the Spotify access token for the user if connected."""
        return self.service.get_access_token(user_id)

    def get_access_token_resilient(self, user, refresh_callback=None, force_refresh: bool = False) -> str | None:
        """Return an access token and refresh once when needed (or when forced)."""
        if not user or not getattr(user, "id", None):
            return None

        token = self.service.get_access_token(user.id)
        if force_refresh:
            token = None
        if token:
            return token

        if refresh_callback and getattr(user, "spotify_refresh_token", None):
            try:
                rt = refresh_callback(user)
                if rt:
                    self.service.refresh_session_with_refresh_token(user.id, rt)
                    refreshed = self.service.get_access_token(user.id)
                    if refreshed:
                        return refreshed
            except Exception:
                # Fall back to any currently-valid token instead of failing hard.
                pass

        return self.service.get_access_token(user.id)

    def disconnect(self, user_id: str) -> None:
        self.service.disconnect(user_id)

    def get_artist_recommendations(
        self,
        user_id: str,
        max_results: int = 10,
        popularity_max: int = 60,
    ) -> List[Dict]:
        """Return lesser-known artist recommendations based on the user's top tracks."""
        return self.service.get_artist_recommendations(
            user_id=user_id,
            max_results=max_results,
            popularity_max=popularity_max,
        )

    def get_artist_recommendations_resilient(
        self,
        user,
        refresh_callback=None,
        max_results: int = 10,
        popularity_max: int = 60,
    ) -> List[Dict]:
        """Fetch recommendations and retry once after token refresh when possible."""
        try:
            return self.service.get_artist_recommendations(
                user_id=user.id,
                max_results=max_results,
                popularity_max=popularity_max,
            )
        except Exception:
            if refresh_callback and user and getattr(user, "spotify_refresh_token", None):
                rt = refresh_callback(user)
                if rt:
                    self.service.refresh_session_with_refresh_token(user.id, rt)
                    return self.service.get_artist_recommendations(
                        user_id=user.id,
                        max_results=max_results,
                        popularity_max=popularity_max,
                    )
            raise

    def play_track_resilient(self, user, track_uri: str, device_id: str, refresh_callback=None) -> None:
        """Play a track on a device and retry once after refresh when needed."""
        try:
            self.service.play_track(user_id=user.id, track_uri=track_uri, device_id=device_id)
            return
        except Exception:
            if refresh_callback and user and getattr(user, "spotify_refresh_token", None):
                rt = refresh_callback(user)
                if rt:
                    self.service.refresh_session_with_refresh_token(user.id, rt)
                    self.service.play_track(user_id=user.id, track_uri=track_uri, device_id=device_id)
                    return
            raise

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
