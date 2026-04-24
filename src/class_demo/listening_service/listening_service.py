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
from collections import Counter
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
    _SEARCH_URL = "https://api.spotify.com/v1/search"
    _RELATED_ARTISTS_URL = "https://api.spotify.com/v1/artists/{}/related-artists"
    _DEFAULT_SCOPE = " ".join(
        [
            "user-top-read",
            "streaming",
            "user-read-email",
            "user-read-private",
            "user-read-playback-state",
            "user-modify-playback-state",
        ]
    )

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
        self.scope = scope or os.getenv("SPOTIFY_SCOPE", self._DEFAULT_SCOPE)
        self.timeout_seconds = timeout_seconds

        self._post_request = post_request or requests.post
        self._get_request = get_request or requests.get
        self._put_request = requests.put

        # Safety by design: tokens are never persisted to DB and are cleared on restart.
        self._pending_auth: Dict[str, Dict[str, object]] = {}
        self._sessions: Dict[str, Dict[str, object]] = {}
        self._last_song_recommendation_debug: Dict[str, Dict[str, object]] = {}
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

    def get_access_token(self, user_id: str) -> str | None:
        """Return the current access token for the user if a valid session exists."""
        if not self.is_connected(user_id):
            return None
        return str(self._sessions[user_id]["access_token"])

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
                        "uri": str(item.get("uri", "")),
                    }
            )
        return tracks

    def play_track(self, user_id: str, track_uri: str, device_id: str) -> None:
        """Start playback of a specific track URI on a specific Spotify device."""
        if not self.is_connected(user_id):
            raise SpotifyConnectionError("Spotify is not connected. Complete secure connection first.")
        if not track_uri:
            raise SpotifyConnectionError("Track URI is missing.")
        if not device_id:
            raise SpotifyConnectionError("Spotify web player device is not ready yet.")

        token = str(self._sessions[user_id]["access_token"])
        response = self._put_request(
            f"https://api.spotify.com/v1/me/player/play?device_id={device_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"uris": [track_uri]},
            timeout=self.timeout_seconds,
        )
        if response.status_code not in (202, 204):
            if response.status_code == 401:
                self._sessions.pop(user_id, None)
                raise SpotifyConnectionError("Spotify access expired while starting playback. Please reconnect.")
            raise SpotifyConnectionError(f"Spotify playback failed ({response.status_code}).")

    def get_last_song_recommendation_debug(self, user_id: str) -> Dict[str, object]:
        """Return diagnostics from the most recent song recommendation attempt."""
        return dict(self._last_song_recommendation_debug.get(user_id, {}))

    def get_song_recommendations(
        self,
        user_id: str,
        max_results: int = 10,
        popularity_max: int = 65,
    ) -> List[Dict[str, object]]:
        """Recommend lesser-known songs the user has never heard.

        Stages (each falls through to the next if it yields nothing):
        1. Collect top artists → heard_artist_ids, seed_genres.
        2. Collect top tracks → heard_track_ids.
        3. (Primary) /v1/recommendations with genre seeds only — NO artist/track
           seeds, because those bias toward music the user already knows.
           Filters out tracks by artists already in heard_artist_ids.
        4. (Fallback A) Related-artist discovery — pull artists related to each
           of the user's top artists via Spotify's graph, then find their tracks.
        5. (Fallback B) Genre search — keyword search for artists in seed genres,
           then fetch their tracks.
        Returns empty list if nothing new is found — never surfaces library songs.
        """
        debug: Dict[str, object] = {
            "user_id": user_id,
            "max_results": max_results,
            "popularity_max": popularity_max,
            "seed_genres": [],
            "heard_artist_count": 0,
            "heard_track_count": 0,
            "fallback_mode": None,
        }

        if not self.is_connected(user_id):
            debug["error"] = "spotify_not_connected"
            self._last_song_recommendation_debug[user_id] = debug
            raise SpotifyConnectionError("Spotify is not connected. Complete secure connection first.")

        token = str(self._sessions[user_id]["access_token"])
        headers = {"Authorization": f"Bearer {token}"}

        from urllib.parse import urlencode as _urlencode

        # ------------------------------------------------------------------ #
        # Stage 1: top artists → heard_artist_ids + seed_genres              #
        # ------------------------------------------------------------------ #
        heard_artist_ids: set[str] = set()
        ordered_seed_artist_ids: List[str] = []
        seed_genres: List[str] = []

        for time_range in ("short_term", "medium_term", "long_term"):
            resp = self._get_request(
                self._TOP_ARTISTS_URL,
                headers=headers,
                params={"limit": "50", "time_range": time_range},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                self._sessions.pop(user_id, None)
                raise SpotifyConnectionError("Spotify session expired. Reconnect and try again.")
            if resp.status_code != 200:
                continue
            for artist in resp.json().get("items", []):
                aid = str(artist.get("id") or "")
                if not aid:
                    continue
                if aid not in heard_artist_ids:
                    heard_artist_ids.add(aid)
                    if len(ordered_seed_artist_ids) < 5:
                        ordered_seed_artist_ids.append(aid)
                for g in (artist.get("genres") or []):
                    g = g.strip()
                    if g and g.lower() not in {s.lower() for s in seed_genres}:
                        seed_genres.append(g)

        debug["seed_genres"] = seed_genres
        debug["heard_artist_count"] = len(heard_artist_ids)

        # ------------------------------------------------------------------ #
        # Stage 2: top tracks → heard_track_ids                              #
        # ------------------------------------------------------------------ #
        heard_track_ids: set[str] = set()

        for time_range in ("short_term", "medium_term", "long_term"):
            resp = self._get_request(
                self._TOP_TRACKS_URL,
                headers=headers,
                params={"limit": "50", "time_range": time_range},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                self._sessions.pop(user_id, None)
                raise SpotifyConnectionError("Spotify session expired. Reconnect and try again.")
            if resp.status_code != 200:
                continue
            for item in resp.json().get("items", []):
                tid = item.get("id")
                if tid:
                    heard_track_ids.add(str(tid))

        debug["heard_track_count"] = len(heard_track_ids)

        # Shared dedup set across all stages — pre-seeded with heard tracks
        seen_track_ids: set[str] = set(heard_track_ids)
        candidates: List[Dict[str, object]] = []

        # ------------------------------------------------------------------ #
        # Stage 3 (primary): Spotify Recommendations API — genre seeds only  #
        #                                                                     #
        # WHY no artist/track seeds: seeding with the user's own top artists #
        # tells Spotify "give me more like these artists" — which returns     #
        # music the user already knows. Genre seeds alone find niche tracks   #
        # in the same style but from unfamiliar artists.                      #
        #                                                                     #
        # Spotify's Recommendations API uses hyphenated genre names           #
        # ("show-tunes") while artist genre tags use spaces ("show tunes").   #
        # ------------------------------------------------------------------ #
        norm_genres: List[str] = []
        seen_norm: set[str] = set()
        for g in seed_genres:
            n = g.lower().replace(" ", "-")
            if n not in seen_norm:
                norm_genres.append(n)
                seen_norm.add(n)

        rec_api_status = None
        if norm_genres:
            rec_resp = self._get_request(
                self._RECOMMENDATIONS_URL,
                headers=headers,
                params={
                    "seed_genres": ",".join(norm_genres[:5]),
                    "max_popularity": str(min(popularity_max, 50)),
                    "limit": "100",
                },
                timeout=self.timeout_seconds,
            )
            rec_api_status = rec_resp.status_code
            if rec_resp.status_code == 200:
                for track in rec_resp.json().get("tracks", []):
                    tid = str(track.get("id") or "")
                    if not tid or tid in seen_track_ids:
                        continue
                    primary_artist = (track.get("artists") or [{}])[0]
                    artist_id = str(primary_artist.get("id") or "")
                    # Skip tracks by artists the user already listens to
                    if artist_id in heard_artist_ids:
                        continue
                    pop_val = track.get("popularity")
                    try:
                        pop_num: int = int(pop_val) if pop_val is not None else 0
                    except (TypeError, ValueError):
                        pop_num = 0
                    seen_track_ids.add(tid)
                    candidates.append({
                        "track": str(track.get("name") or "Unknown Track"),
                        "artist": str(primary_artist.get("name") or "Unknown Artist"),
                        "popularity": pop_num,
                        "genre": seed_genres[0] if seed_genres else "recommended",
                        "uri": str(track.get("uri") or ""),
                    })

        debug["recommendations_api_status"] = rec_api_status
        debug["candidates_after_api"] = len(candidates)

        if candidates:
            candidates.sort(key=lambda r: int(r["popularity"]))
            result = candidates[:max_results]
            debug["fallback_mode"] = "spotify_recommendations_api"
            debug["result_count"] = len(result)
            self._last_song_recommendation_debug[user_id] = debug
            return result

        # ------------------------------------------------------------------ #
        # Stage 4 (fallback A): Related-artist discovery                     #
        #                                                                     #
        # Spotify's /related-artists uses its own listen-graph — more        #
        # reliable than genre-keyword search for finding artists in the same  #
        # musical neighbourhood that the user hasn't heard yet.              #
        # ------------------------------------------------------------------ #
        related: List[Dict[str, object]] = []
        seen_related: set[str] = set(heard_artist_ids)

        for seed_aid in ordered_seed_artist_ids[:5]:
            resp = self._get_request(
                self._RELATED_ARTISTS_URL.format(seed_aid),
                headers=headers,
                timeout=self.timeout_seconds,
            )
            if resp.status_code != 200:
                continue
            for artist in resp.json().get("artists", []):
                aid = str(artist.get("id") or "")
                aname = str(artist.get("name") or "").strip()
                if not aid or not aname or aid in seen_related:
                    continue
                pop = int(artist.get("popularity") or 0)
                genres = artist.get("genres") or []
                seen_related.add(aid)
                related.append({
                    "id": aid, "name": aname, "popularity": pop,
                    "genre": genres[0] if genres else (seed_genres[0] if seed_genres else "related"),
                })

        related.sort(key=lambda a: int(a["popularity"]))
        debug["related_artists_found"] = len(related)

        for artist_info in related[:30]:
            if len(candidates) >= max_results * 4:
                break
            aid = str(artist_info["id"])
            aname = str(artist_info["name"])
            genre_label = str(artist_info["genre"])
            url = self._SEARCH_URL + "?" + _urlencode({
                "q": f'artist:"{aname}"',
                "type": "track",
                "limit": "20",
            })
            resp = self._get_request(url, headers=headers, timeout=self.timeout_seconds)
            if resp.status_code != 200:
                continue
            for track in (resp.json().get("tracks") or {}).get("items", []):
                track_artist_ids = {
                    str(a.get("id") or "") for a in (track.get("artists") or [])
                }
                if aid not in track_artist_ids:
                    continue
                tid = str(track.get("id") or "")
                if not tid or tid in seen_track_ids:
                    continue
                pop_val = track.get("popularity")
                try:
                    pop_num = int(pop_val) if pop_val is not None else 0
                except (TypeError, ValueError):
                    pop_num = 0
                if pop_num > popularity_max:
                    continue
                primary_artist = (track.get("artists") or [{}])[0]
                seen_track_ids.add(tid)
                candidates.append({
                    "track": str(track.get("name") or "Unknown Track"),
                    "artist": str(primary_artist.get("name") or aname),
                    "popularity": pop_num,
                    "genre": genre_label,
                    "uri": str(track.get("uri") or ""),
                })

        debug["candidates_after_related"] = len(candidates)

        if candidates:
            candidates.sort(key=lambda r: int(r["popularity"]))
            result = candidates[:max_results]
            debug["fallback_mode"] = "related_artists"
            debug["result_count"] = len(result)
            self._last_song_recommendation_debug[user_id] = debug
            return result

        # ------------------------------------------------------------------ #
        # Stage 5 (fallback B): Genre keyword search → artist → track        #
        # ------------------------------------------------------------------ #
        genre_artist_searches: List[Dict[str, object]] = []
        track_searches: List[Dict[str, object]] = []
        discovered: List[Dict[str, object]] = []
        seen_discovered_ids: set[str] = set(heard_artist_ids)

        genres_to_search: List[tuple[str, str]] = [(g, g) for g in seed_genres]
        for broad in ("show tunes", "original cast recording", "broadway", "indie pop",
                      "indie folk", "chamber pop", "dream pop", "alternative rock",
                      "folk", "singer-songwriter", "j-pop", "anime", "lo-fi"):
            if broad.lower() not in {sg.lower() for sg in seed_genres}:
                genres_to_search.append((broad, broad))

        for genre_q, genre_label in genres_to_search:
            if len(discovered) >= 60:
                break
            url = self._SEARCH_URL + "?" + _urlencode({
                "q": f'genre:"{genre_q}"',
                "type": "artist",
                "limit": "50",
            })
            resp = self._get_request(url, headers=headers, timeout=self.timeout_seconds)
            entry: Dict[str, object] = {
                "genre": genre_q, "status": int(resp.status_code),
                "total_artists": 0, "new_artists": 0,
            }
            if resp.status_code == 200:
                for artist in (resp.json().get("artists") or {}).get("items", []):
                    aid = str(artist.get("id") or "")
                    aname = str(artist.get("name") or "").strip()
                    if not aid or not aname:
                        continue
                    entry["total_artists"] = int(entry["total_artists"]) + 1
                    if aid in seen_discovered_ids:
                        continue
                    pop = int(artist.get("popularity") or 0)
                    seen_discovered_ids.add(aid)
                    entry["new_artists"] = int(entry["new_artists"]) + 1
                    discovered.append({
                        "id": aid, "name": aname,
                        "popularity": pop, "genre": genre_label,
                    })
            genre_artist_searches.append(entry)

        discovered.sort(key=lambda a: int(a["popularity"]))
        debug["artists_discovered"] = len(discovered)

        for artist_info in discovered[:25]:
            if len(candidates) >= max_results * 8:
                break
            aid = str(artist_info["id"])
            aname = str(artist_info["name"])
            genre_label = str(artist_info["genre"])
            url = self._SEARCH_URL + "?" + _urlencode({
                "q": f'artist:"{aname}"',
                "type": "track",
                "limit": "20",
            })
            resp = self._get_request(url, headers=headers, timeout=self.timeout_seconds)
            tentry: Dict[str, object] = {
                "artist": aname, "status": int(resp.status_code), "added": 0,
            }
            if resp.status_code == 200:
                for track in (resp.json().get("tracks") or {}).get("items", []):
                    track_artist_ids = {
                        str(a.get("id") or "") for a in (track.get("artists") or [])
                    }
                    if aid not in track_artist_ids:
                        continue
                    tid = str(track.get("id") or "")
                    if not tid or tid in seen_track_ids:
                        continue
                    pop_val = track.get("popularity")
                    try:
                        pop_num = int(pop_val) if pop_val is not None else 0
                    except (TypeError, ValueError):
                        pop_num = 0
                    if pop_num > popularity_max:
                        continue
                    primary_artist = (track.get("artists") or [{}])[0]
                    seen_track_ids.add(tid)
                    tentry["added"] = int(tentry["added"]) + 1
                    candidates.append({
                        "track": str(track.get("name") or "Unknown Track"),
                        "artist": str(primary_artist.get("name") or aname),
                        "popularity": pop_num,
                        "genre": genre_label,
                        "uri": str(track.get("uri") or ""),
                    })
            track_searches.append(tentry)

        debug["genre_artist_searches"] = genre_artist_searches
        debug["track_searches"] = track_searches
        debug["candidates_found"] = len(candidates)

        if candidates:
            candidates.sort(key=lambda r: int(r["popularity"]))
            result = candidates[:max_results]
            debug["fallback_mode"] = "genre_artist_search"
            debug["result_count"] = len(result)
            self._last_song_recommendation_debug[user_id] = debug
            return result

        # All stages exhausted — return empty rather than surfacing library songs
        debug["fallback_mode"] = "empty"
        debug["result_count"] = 0
        self._last_song_recommendation_debug[user_id] = debug
        return []

    def get_artist_recommendations(
        self,
        user_id: str,
        max_results: int = 10,
        popularity_max: int = 65,
    ) -> List[Dict[str, object]]:
        """Artist recommendation path kept for backward compatibility and tests."""
        if not self.is_connected(user_id):
            raise SpotifyConnectionError("Spotify is not connected. Complete secure connection first.")

        token = str(self._sessions[user_id]["access_token"])
        headers = {"Authorization": f"Bearer {token}"}

        track_artist_ids: List[str] = []
        for time_range in ("short_term", "medium_term", "long_term"):
            resp = self._get_request(
                self._TOP_TRACKS_URL,
                headers=headers,
                params={"limit": 50, "time_range": time_range},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                self._sessions.pop(user_id, None)
                raise SpotifyConnectionError("Failed to fetch top tracks for recommendations.")
            if resp.status_code != 200:
                continue
            for item in resp.json().get("items", []):
                for artist in item.get("artists", []):
                    aid = artist.get("id")
                    if aid:
                        track_artist_ids.append(str(aid))

        if not track_artist_ids:
            return []

        top_artist_ids: set[str] = set()
        top_artist_names: set[str] = set()
        for time_range in ("short_term", "medium_term", "long_term"):
            top_resp = self._get_request(
                self._TOP_ARTISTS_URL,
                headers=headers,
                params={"limit": 50, "time_range": time_range},
                timeout=self.timeout_seconds,
            )
            if top_resp.status_code != 200:
                continue
            for artist in top_resp.json().get("items", []):
                aid = artist.get("id")
                aname = str(artist.get("name") or "").strip().lower()
                if aid:
                    top_artist_ids.add(str(aid))
                if aname:
                    top_artist_names.add(aname)

        candidates: Dict[str, Dict[str, object]] = {}
        dedup_ids = list(dict.fromkeys(track_artist_ids))
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
                aid = str(artist.get("id") or "")
                aname = str(artist.get("name") or "").strip()
                if not aid or not aname:
                    continue
                if aid in top_artist_ids or aname.lower() in top_artist_names:
                    continue
                popularity_val = artist.get("popularity")
                try:
                    popularity_num = int(popularity_val) if popularity_val is not None else None
                except (TypeError, ValueError):
                    popularity_num = None
                genres = artist.get("genres") or []
                candidates[aid] = {
                    "name": aname,
                    "popularity": popularity_num,
                    "genres": ", ".join(genres[:3]) if genres else "Unknown",
                }

        rows = list(candidates.values())
        strict = [r for r in rows if r["popularity"] is not None and int(r["popularity"]) <= popularity_max]
        if strict:
            strict.sort(key=lambda r: int(r["popularity"]))
            return strict[:max_results]

        relaxed = [
            r for r in rows if r["popularity"] is not None and int(r["popularity"]) <= min(popularity_max + 20, 100)
        ]
        if relaxed:
            relaxed.sort(key=lambda r: int(r["popularity"]))
            return relaxed[:max_results]

        rows.sort(key=lambda r: (r["popularity"] is None, int(r["popularity"] or 0)))
        return rows[:max_results]

    def refresh_session_with_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """Exchange a stored refresh token for a fresh access token and populate session.

        Uses PKCE public-client flow: no client_secret required.
        """
        self._validate_config()

        # PKCE token refresh: only grant_type, refresh_token, and client_id are sent.
        # Spotify rejects the request if client_secret is included for public (PKCE) clients.
        resp = self._post_request(
            self._TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
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
