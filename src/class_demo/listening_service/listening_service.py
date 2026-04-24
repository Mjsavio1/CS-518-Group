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
        """Discover lesser-known songs using only endpoints available post-2024.

        The /recommendations and /artists/{id}/related-artists endpoints are
        discontinued (return 404). The /search limit cap is now 10 (was 50).
        Sending limit > 10 causes a 400 error.

        Pipeline:
        1. /me/top/artists  — build heard_artist_ids exclusion set + seed_genres
        2. /me/top/tracks   — build heard_track_ids + collect title seeds
        3. Artist keyword search (type=artist, limit=10, paginated with offset)
           to discover niche artists across many style/genre terms
        4. Track search by discovered artist names (type=track, limit=10)
        5. Cover search — search each heard track title to find lesser-known
           artists who recorded the same song (covers, fan arrangements, etc.)
        6. Direct keyword track search as final fallback
        Returns [] if nothing found; never returns songs from the user's library.
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

        # ------------------------------------------------------------------ #
        # Stage 1: /me/top/artists → heard_artist_ids + seed_genres          #
        # ------------------------------------------------------------------ #
        heard_artist_ids: set[str] = set()
        heard_artist_names_lc: set[str] = set()
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
                aname = str(artist.get("name") or "").strip()
                if aid:
                    heard_artist_ids.add(aid)
                if aname:
                    heard_artist_names_lc.add(aname.lower())
                for g in (artist.get("genres") or []):
                    g = g.strip()
                    if g and g.lower() not in {s.lower() for s in seed_genres}:
                        seed_genres.append(g)

        debug["seed_genres"] = seed_genres
        debug["heard_artist_count"] = len(heard_artist_ids)

        # ------------------------------------------------------------------ #
        # Stage 2: /me/top/tracks → heard_track_ids + title seeds            #
        # Track titles are used in Stage 5 to search for covers/             #
        # interpretations by artists the user has never heard.               #
        # ------------------------------------------------------------------ #
        heard_track_ids: set[str] = set()
        heard_track_titles: List[str] = []

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
                tname = str(item.get("name") or "").strip()
                if tname and tname not in heard_track_titles:
                    heard_track_titles.append(tname)

        debug["heard_track_count"] = len(heard_track_ids)

        seen_track_ids: set[str] = set(heard_track_ids)
        candidates: List[Dict[str, object]] = []

        def _try_add_track(track: dict, genre_hint: str) -> None:
            """Add track to candidates if it passes all filters."""
            tid = str(track.get("id") or "")
            if not tid or tid in seen_track_ids:
                return
            artists = track.get("artists") or [{}]
            primary_id = str(artists[0].get("id") or "")
            primary_name = str(artists[0].get("name") or "").strip()
            if primary_id in heard_artist_ids or primary_name.lower() in heard_artist_names_lc:
                return
            pop_val = track.get("popularity")
            try:
                pop_num: int = int(pop_val) if pop_val is not None else 0
            except (TypeError, ValueError):
                pop_num = 0
            if pop_num > popularity_max:
                return
            seen_track_ids.add(tid)
            candidates.append({
                "track": str(track.get("name") or "Unknown Track"),
                "artist": primary_name or "Unknown Artist",
                "popularity": pop_num,
                "genre": genre_hint,
                "uri": str(track.get("uri") or ""),
            })

        # ------------------------------------------------------------------ #
        # Stage 3: Artist keyword search (type=artist, limit=10)             #
        #                                                                     #
        # /recommendations and /related-artists are discontinued (404).      #
        # The search limit cap is now 10 — sending limit > 10 causes 400.    #
        # Use offset pagination to collect up to 30 artists per keyword.     #
        # ------------------------------------------------------------------ #
        search_keywords: List[str] = list(seed_genres)
        for broad in (
            "musical theatre", "broadway", "show tunes", "west end",
            "cast recording", "sondheim", "original cast", "musical",
            "anime soundtrack", "anime ost", "j-pop", "vocaloid",
            "indie folk", "singer songwriter", "folk acoustic",
            "chamber pop", "dream pop", "alternative rock", "indie pop",
            "lo-fi", "ambient", "classical crossover", "neo-classical",
            "art pop", "experimental", "underground", "bedroom pop",
        ):
            if broad.lower() not in {k.lower() for k in search_keywords}:
                search_keywords.append(broad)

        discovered_artists: List[Dict[str, object]] = []
        seen_discovered_ids: set[str] = set(heard_artist_ids)
        artist_search_log: List[Dict[str, object]] = []

        for kw in search_keywords:
            if len(discovered_artists) >= 120:
                break
            for offset in (0, 10, 20):
                if len(discovered_artists) >= 120:
                    break
                r = self._get_request(
                    self._SEARCH_URL,
                    headers=headers,
                    params={
                        "q": kw,
                        "type": "artist",
                        "limit": "10",
                        "offset": str(offset),
                    },
                    timeout=self.timeout_seconds,
                )
                log_entry: Dict[str, object] = {
                    "kw": kw, "offset": offset,
                    "status": int(r.status_code), "new": 0,
                }
                if r.status_code == 200:
                    for artist in (r.json().get("artists") or {}).get("items", []):
                        aid = str(artist.get("id") or "")
                        aname = str(artist.get("name") or "").strip()
                        if not aid or not aname:
                            continue
                        if aid in seen_discovered_ids or aname.lower() in heard_artist_names_lc:
                            continue
                        genres = artist.get("genres") or []
                        seen_discovered_ids.add(aid)
                        log_entry["new"] = int(log_entry["new"]) + 1
                        discovered_artists.append({
                            "id": aid, "name": aname,
                            "popularity": int(artist.get("popularity") or 0),
                            "genre": genres[0] if genres else kw,
                        })
                artist_search_log.append(log_entry)
                if r.status_code != 200:
                    break  # skip pagination if the call failed

        discovered_artists.sort(key=lambda a: int(a["popularity"]))
        debug["artists_discovered"] = len(discovered_artists)
        debug["artist_search_log"] = artist_search_log

        # ------------------------------------------------------------------ #
        # Stage 4: Track search by each discovered artist name               #
        # ------------------------------------------------------------------ #
        for artist_info in discovered_artists[:40]:
            if len(candidates) >= max_results * 6:
                break
            aname = str(artist_info["name"])
            genre_label = str(artist_info["genre"])
            r = self._get_request(
                self._SEARCH_URL,
                headers=headers,
                params={"q": f'artist:"{aname}"', "type": "track", "limit": "10"},
                timeout=self.timeout_seconds,
            )
            if r.status_code == 200:
                for track in (r.json().get("tracks") or {}).get("items", []):
                    _try_add_track(track, genre_label)

        debug["candidates_after_artist_tracks"] = len(candidates)

        # ------------------------------------------------------------------ #
        # Stage 5: Cover / interpretation search                             #
        #                                                                     #
        # Search each heard track title. Less-known artists who covered the  #
        # same song appear here — fan arrangements, indie covers, alternate   #
        # cast recordings of the same show, etc. The primary artist filter   #
        # in _try_add_track ensures the user's familiar version is excluded. #
        # This is the strongest fallback for Broadway/niche-genre fans        #
        # because it uses exactly the songs we know the user loves.          #
        # ------------------------------------------------------------------ #
        if len(candidates) < max_results * 2:
            for title in heard_track_titles[:30]:
                if len(candidates) >= max_results * 6:
                    break
                # Strip parentheticals like "(Reprise)" for broader matches
                clean = title.split("(")[0].split("[")[0].strip()
                if len(clean) < 4:
                    continue
                r = self._get_request(
                    self._SEARCH_URL,
                    headers=headers,
                    params={"q": clean, "type": "track", "limit": "10"},
                    timeout=self.timeout_seconds,
                )
                if r.status_code == 200:
                    for track in (r.json().get("tracks") or {}).get("items", []):
                        _try_add_track(track, "cover / interpretation")

        debug["candidates_after_covers"] = len(candidates)

        # ------------------------------------------------------------------ #
        # Stage 6: Direct keyword track search (last resort)                 #
        # ------------------------------------------------------------------ #
        if len(candidates) < max_results:
            direct_queries = [
                "original cast recording",
                "original broadway cast",
                "original london cast",
                "world premiere cast recording",
                "musical theatre",
                "anime ost",
                "anime soundtrack",
                "lo-fi jazz",
                "indie folk acoustic",
                "chamber music vocal",
                "art song recital",
            ]
            for q in direct_queries:
                if len(candidates) >= max_results * 3:
                    break
                r = self._get_request(
                    self._SEARCH_URL,
                    headers=headers,
                    params={"q": q, "type": "track", "limit": "10"},
                    timeout=self.timeout_seconds,
                )
                if r.status_code == 200:
                    for track in (r.json().get("tracks") or {}).get("items", []):
                        _try_add_track(track, q)

        debug["candidates_found"] = len(candidates)
        debug["track_searches"] = []  # schema compat with old debug consumers

        if candidates:
            candidates.sort(key=lambda r: int(r["popularity"]))
            result = candidates[:max_results]
            debug["fallback_mode"] = "search_based"
            debug["result_count"] = len(result)
            self._last_song_recommendation_debug[user_id] = debug
            return result

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
