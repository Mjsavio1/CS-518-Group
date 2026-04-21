from typing import List, Dict

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

        # TODO: Integrate with Spotify API or playback backend        # TODO: Integrate with Spotify API or playback backend
