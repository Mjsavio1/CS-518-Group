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

    def get_recent_plays(self) -> List[Dict[str, str]]:
        return self.service.get_sample_recent_plays()