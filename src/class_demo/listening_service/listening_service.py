"""Listening History Service.

Provides business logic for Spotify listening history with a safety-first
OAuth flow. The integration uses Authorization Code + PKCE, validates CSRF
state, requests minimal scopes, and keeps Spotify tokens in memory only.
"""

import base64
import hashlib
import os
import secrets
import time
from typing import Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests


class SpotifyConnectionError(ValueError):
    """Raised when Spotify connection cannot be completed safely."""


class ListeningService:
    """Service layer for listening-history features and Spotify OAuth."""

    _AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
    _TOKEN_URL = "https://accounts.spotify.com/api/token"
    _ME_URL = "https://api.spotify.com/v1/me"
    _TOP_TRACKS_URL = "https://api.spotify.com/v1/me/top/tracks"
    _TOP_ARTISTS_URL = "https://api.spotify.com/v1/me/top/artists"
    _RECOMMENDATIONS_URL = "https://api.spotify.com/v1/recommendations"
    _ARTISTS_URL = "https://api.spotify.com/v1/artists"

    def __init__(
        self,
        client_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scope: Optional[str] = None,
        timeout_seconds: int = 15,
        post_request: Optional[Callable[..., requests.Response]] = None,
        get_request: Optional[Callable[..., requests.Response]] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "")
        self.redirect_uri = redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback")
        self.scope = scope or os.getenv("SPOTIFY_SCOPE", "user-top-read")
        self.timeout_seconds = timeout_seconds

        self._post_request = post_request or requests.post
        self._get_request = get_request or requests.get

        # Safety by design: tokens are never persisted to DB and are cleared on restart.
        self._pending_auth: Dict[str, Dict[str, object]] = {}
        self._sessions: Dict[str, Dict[str, object]] = {}
        # allow injecting client_secret for testing or explicit config
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")

    def hello_world(self) -> str:
        return "Spotify integration is ready. Use secure connect to authorize your account."

    def get_connection_safety_notes(self) -> str:
        return (
            "Safety mode enabled: PKCE + state verification, minimal scope, "
            "and no Spotify tokens are stored in the database."
        )

    def start_secure_connection(self, user_id: str) -> str:
        self._validate_config()
        if not user_id:
            raise SpotifyConnectionError("Cannot start Spotify connection without a user ID.")

        state = secrets.token_urlsafe(24)
        verifier, challenge = self._build_pkce_pair()

        self._pending_auth[user_id] = {
            "state": state,
            "verifier": verifier,
            "created_at": time.time(),
        }

        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": self.scope,
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": challenge,
            }
        )
        return f"{self._AUTHORIZE_URL}?{query}"

    def complete_secure_connection(self, user_id: str, callback_url: str) -> Dict[str, str]:
        self._validate_config()
        if not user_id:
            raise SpotifyConnectionError("Cannot complete Spotify connection without a user ID.")
        if not callback_url:
            raise SpotifyConnectionError("Paste the full callback URL to complete Spotify connection.")

        pending = self._pending_auth.get(user_id)
        if pending is None:
            raise SpotifyConnectionError("No pending Spotify authorization found. Start secure connect first.")

        if time.time() - float(pending["created_at"]) > 10 * 60:
            self._pending_auth.pop(user_id, None)
            raise SpotifyConnectionError("Spotify authorization expired. Generate a new secure login link.")

        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]
        return self.complete_secure_connection_from_params(
            user_id=user_id,
            code=code,
            state=state,
            error=error,
        )

    def complete_secure_connection_from_params(
        self,
        user_id: str,
        code: Optional[str],
        state: Optional[str],
        error: Optional[str] = None,
    ) -> Dict[str, str]:
        self._validate_config()
        if not user_id:
            raise SpotifyConnectionError("Cannot complete Spotify connection without a user ID.")

        pending = self._pending_auth.get(user_id)
        if pending is None:
            raise SpotifyConnectionError("No pending Spotify authorization found. Start secure connect first.")

        if time.time() - float(pending["created_at"]) > 10 * 60:
            self._pending_auth.pop(user_id, None)
            raise SpotifyConnectionError("Spotify authorization expired. Generate a new secure login link.")

        if error:
            self._pending_auth.pop(user_id, None)
            raise SpotifyConnectionError(f"Spotify authorization was not approved: {error}")

        if not code or not state:
            raise SpotifyConnectionError("Callback parameters are missing required code/state values.")
        if state != pending["state"]:
            raise SpotifyConnectionError("State validation failed. Please retry secure Spotify connect.")

        token_response = self._post_request(
            self._TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "code_verifier": str(pending["verifier"]),
            },
            timeout=self.timeout_seconds,
        )

        if token_response.status_code != 200:
            self._pending_auth.pop(user_id, None)
            raise SpotifyConnectionError("Spotify token exchange failed. Please try connecting again.")

        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        expires_in = int(token_payload.get("expires_in", 3600))
        if not access_token:
            self._pending_auth.pop(user_id, None)
            raise SpotifyConnectionError("Spotify token response missing access token.")

        profile_response = self._get_request(
            self._ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.timeout_seconds,
        )
        profile: Dict[str, object] = {}
        if profile_response.status_code == 200:
            profile = profile_response.json()
        refresh_token = token_payload.get("refresh_token")
        spotify_user_id = profile.get("id")
        expires_at = time.time() + max(expires_in - 30, 30)

        self._sessions[user_id] = {
            "access_token": access_token,
            "expires_at": expires_at,
            "display_name": profile.get("display_name") or "Spotify User",
        }
        self._pending_auth.pop(user_id, None)

        result: Dict[str, str | float] = {
            "display_name": str(self._sessions[user_id]["display_name"]),
            "status": "connected",
        }
        if refresh_token:
            result["refresh_token"] = str(refresh_token)
        if spotify_user_id:
            result["spotify_id"] = str(spotify_user_id)
        result["expires_at"] = float(expires_at)
        return result

    def is_connected(self, user_id: str) -> bool:
        session = self._sessions.get(user_id)
        if session is None:
            return False
        if float(session.get("expires_at", 0)) <= time.time():
            self._sessions.pop(user_id, None)
            return False
        return True

    def disconnect(self, user_id: str) -> None:
        self._pending_auth.pop(user_id, None)
        self._sessions.pop(user_id, None)

    def get_top_tracks(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        if not self.is_connected(user_id):
            raise SpotifyConnectionError("Spotify is not connected. Complete secure connection first.")

        token = str(self._sessions[user_id]["access_token"])
        response = self._get_request(
            self._TOP_TRACKS_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": max(1, min(limit, 50)), "time_range": "medium_term"},
            timeout=self.timeout_seconds,
        )
        if response.status_code != 200:
            if response.status_code == 401:
                self._sessions.pop(user_id, None)
            raise SpotifyConnectionError("Failed to fetch Spotify top tracks. Reconnect and try again.")

        items = response.json().get("items", [])
        tracks: List[Dict[str, str]] = []
        for index, item in enumerate(items, start=1):
            artists = item.get("artists", [])
            artist_names = ", ".join([a.get("name", "") for a in artists if a.get("name")]) or "Unknown"
            popularity = item.get("popularity")
            popularity_display = str(popularity) if popularity is not None else f"Rank {index}"
            tracks.append(
                {
                    "title": str(item.get("name", "Unknown")),
                    "artist": artist_names,
                    "plays": popularity_display,
                }
            )
        return tracks

    def get_artist_recommendations(
        self,
        user_id: str,
        max_results: int = 10,
        popularity_max: int = 60,
    ) -> List[Dict[str, object]]:
        """Recommend lesser-known artists based on the user's Spotify top tracks.

          Algorithm (with fallbacks):
          1. Fetch the user's top 50 tracks to collect unique seed artist IDs.
          2. Fetch the user's top artists to improve known-artist exclusion.
          2. Query related-artists for up to 12 seeds.
          3. If sparse, call recommendations endpoint using seed artists, then enrich
              artist IDs via /artists?ids=... so we can rank by popularity.
          4. Remove already-known artists where possible, de-duplicate, and rank by
              ascending popularity so the least-mainstream artists appear first.

        popularity_max=60 targets artists below mainstream chart level (70+).
        """
        if not self.is_connected(user_id):
            raise SpotifyConnectionError("Spotify is not connected. Complete secure connection first.")

        token = str(self._sessions[user_id]["access_token"])
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1 – fetch top tracks (raw) to extract artist IDs
        response = self._get_request(
            self._TOP_TRACKS_URL,
            headers=headers,
            params={"limit": 50, "time_range": "medium_term"},
            timeout=self.timeout_seconds,
        )
        if response.status_code != 200:
            if response.status_code == 401:
                self._sessions.pop(user_id, None)
            raise SpotifyConnectionError("Failed to fetch top tracks for recommendations.")

        items = response.json().get("items", [])

        seen_ids: set = set()
        seed_artists: List[tuple] = []      # (artist_id, artist_name)
        seed_artist_ids: set = set()
        seed_primary_names: set = set()
        top_artist_names: set = set()       # lower-cased top-artist names already known to user

        for item in items:
            primary_name = ""
            if item.get("artists"):
                primary_name = (item.get("artists")[0].get("name") or "").strip()
            if primary_name:
                seed_primary_names.add(primary_name.lower())

            for artist in item.get("artists", []):
                aid = artist.get("id")
                aname = (artist.get("name") or "").strip()
                if aid and aid not in seen_ids:
                    seen_ids.add(aid)
                    seed_artists.append((aid, aname))
                    seed_artist_ids.add(aid)

        top_artist_ids: set = set()
        top_artists_resp = self._get_request(
            self._TOP_ARTISTS_URL,
            headers=headers,
            params={"limit": 50, "time_range": "medium_term"},
            timeout=self.timeout_seconds,
        )
        if top_artists_resp.status_code == 200:
            for artist in top_artists_resp.json().get("items", []):
                aid = artist.get("id")
                aname = (artist.get("name") or "").strip()
                if aid:
                    top_artist_ids.add(aid)
                if aname:
                    top_artist_names.add(aname.lower())

        def _add_candidate(artist_obj: Dict[str, object]) -> None:
            ra_id = artist_obj.get("id")
            ra_name = str((artist_obj.get("name") or "")).strip()
            if not ra_id or not ra_name:
                return
            if (
                ra_id in seed_artist_ids
                or ra_id in top_artist_ids
                or ra_name.lower() in seed_primary_names
                or ra_name.lower() in top_artist_names
            ):
                return
            if ra_id in candidates:
                return

            popularity_val = artist_obj.get("popularity")
            try:
                popularity_num = int(popularity_val) if popularity_val is not None else None
            except (TypeError, ValueError):
                popularity_num = None

            genres = artist_obj.get("genres") or []
            genre_text = ", ".join(genres[:3]) if genres else "Unknown"
            candidates[ra_id] = {
                "name": ra_name,
                "popularity": popularity_num,
                "genres": genre_text,
            }

        # Step 2 – query related-artists for each seed (cap to reduce rate-limit pressure)
        candidates: Dict[str, Dict] = {}

        for artist_id, _ in seed_artists[:12]:
            rel_url = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"
            rel_resp = self._get_request(rel_url, headers=headers, timeout=self.timeout_seconds)
            if rel_resp.status_code != 200:
                continue
            for ra in rel_resp.json().get("artists", []):
                _add_candidate(ra)

        # Step 3 – fallback via recommendations endpoint + artist enrichment.
        if seed_artists:
            seed_ids = [aid for aid, _ in seed_artists[:5]]
            rec_resp = self._get_request(
                self._RECOMMENDATIONS_URL,
                headers=headers,
                params={
                    "seed_artists": ",".join(seed_ids),
                    "limit": 100,
                    "max_popularity": min(popularity_max + 20, 100),
                },
                timeout=self.timeout_seconds,
            )
            if rec_resp.status_code == 200:
                rec_artist_ids: List[str] = []
                for track in rec_resp.json().get("tracks", []):
                    for artist in track.get("artists", []):
                        ra_id = artist.get("id")
                        ra_name = (artist.get("name") or "").strip()
                        if (
                            ra_id
                            and ra_name
                            and ra_id not in top_artist_ids
                            and ra_name.lower() not in top_artist_names
                        ):
                            rec_artist_ids.append(ra_id)

                # De-duplicate while preserving order.
                dedup_ids = list(dict.fromkeys(rec_artist_ids))
                for i in range(0, len(dedup_ids), 50):
                    chunk = dedup_ids[i : i + 50]
                    artist_resp = self._get_request(
                        self._ARTISTS_URL,
                        headers=headers,
                        params={"ids": ",".join(chunk)},
                        timeout=self.timeout_seconds,
                    )
                    if artist_resp.status_code != 200:
                        continue
                    for artist in artist_resp.json().get("artists", []):
                        if not artist:
                            continue
                        _add_candidate(artist)

        # Step 5 – filter and rank with a relaxed fallback threshold.
        filtered = [v for v in candidates.values() if v["popularity"] is not None and v["popularity"] <= popularity_max]
        if not filtered:
            filtered = [
                v
                for v in candidates.values()
                if v["popularity"] is not None and v["popularity"] <= min(popularity_max + 20, 100)
            ]
        if not filtered:
            filtered = [v for v in candidates.values() if v["popularity"] is not None]

        # If every candidate is missing metadata, do a soft fallback instead of
        # fabricating neutral values that look broken in the UI.
        if not filtered:
            filtered = [
                {
                    "name": v["name"],
                    "popularity": "Unknown",
                    "genres": v["genres"],
                }
                for v in candidates.values()
            ]

        filtered.sort(key=lambda x: x["popularity"])
        return filtered[:max_results]

    def refresh_session_with_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """Exchange a stored refresh token for a fresh access token and populate session."""
        self._validate_config()
        client_secret = self.client_secret
        if not client_secret:
            raise SpotifyConnectionError("SPOTIFY_CLIENT_SECRET is not configured. Cannot refresh tokens.")

        resp = self._post_request(
            self._TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": client_secret,
            },
            timeout=self.timeout_seconds,
        )

        if resp.status_code != 200:
            raise SpotifyConnectionError("Failed to refresh Spotify access token.")

        payload = resp.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        new_refresh = payload.get("refresh_token")

        if not access_token:
            raise SpotifyConnectionError("Refresh response missing access token.")

        expires_at = time.time() + max(expires_in - 30, 30)

        # Update session
        self._sessions[user_id] = {
            "access_token": access_token,
            "expires_at": expires_at,
            "display_name": self._sessions.get(user_id, {}).get("display_name", "Spotify User"),
        }

        # If a new refresh token was issued, return it in a minimal fashion by storing it in _sessions
        if new_refresh:
            self._sessions[user_id]["refresh_token_rotated"] = new_refresh

        return True

    def _validate_config(self) -> None:
        if not self.client_id:
            raise SpotifyConnectionError(
                "SPOTIFY_CLIENT_ID is not configured. Add it to your environment before connecting."
            )
        parsed = urlparse(self.redirect_uri)
        if not parsed.scheme or not parsed.netloc:
            raise SpotifyConnectionError("SPOTIFY_REDIRECT_URI must be an absolute URL.")

    @staticmethod
    def _build_pkce_pair() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64).rstrip("=")
        challenge_bytes = hashlib.sha256(verifier.encode("utf-8")).digest()
        challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
        return verifier, challenge
