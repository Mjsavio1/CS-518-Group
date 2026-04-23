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
