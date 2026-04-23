"""Listening History Service.

Provides business logic for analyzing a user's listening history.
This is an initial skeleton - full Spotify API integration and
repository persistence will be added in a future sprint.
"""

from typing import List, Dict


class ListeningService:
    """Service layer for listening-history features."""

    def hello_world(self) -> str:
        """Return a greeting message confirming the service is wired up."""
        return "Listening History Service is online! Connect your Spotify account to see your top tracks."

    def get_sample_top_tracks(self) -> List[Dict[str, str]]:
        """Return placeholder top-track data.

        Will be replaced by real Spotify API calls once the integration
        layer is implemented.
        """
        return [
            {"title": "Blinding Lights", "artist": "The Weeknd", "plays": "312"},
            {"title": "As It Was", "artist": "Harry Styles", "plays": "289"},
            {"title": "Anti-Hero", "artist": "Taylor Swift", "plays": "274"},
            {"title": "Flowers", "artist": "Miley Cyrus", "plays": "251"},
            {"title": "Cruel Summer", "artist": "Taylor Swift", "plays": "238"},
        ]

    def get_sample_recent_plays(self) -> List[Dict[str, str]]:
        """Return placeholder recent plays data.

        Will be replaced by real Spotify API calls once the integration
        layer is implemented.
        """
        return [
            {"title": "Blinding Lights", "artist": "The Weeknd", "played_at": "2026-04-23 10:32"},
            {"title": "Flowers", "artist": "Miley Cyrus", "played_at": "2026-04-23 09:15"},
            {"title": "Anti-Hero", "artist": "Taylor Swift", "played_at": "2026-04-22 21:48"},
            {"title": "As It Was", "artist": "Harry Styles", "played_at": "2026-04-22 20:01"},
            {"title": "Cruel Summer", "artist": "Taylor Swift", "played_at": "2026-04-22 19:30"},
        ]
