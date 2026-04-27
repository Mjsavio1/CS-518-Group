import asyncio
import json

from nicegui import ui

from .listening_controller import ListeningController, SpotifyRateLimitError
from ...user_service.models import User
from ..interfaces import AppLogic
from ..session import SessionManager


def _parse_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _spotify_embed_url(track_uri: str) -> str:
    """Build a Spotify embed URL from a Spotify track URI or URL."""
    if not track_uri:
        return ""
    if track_uri.startswith("spotify:track:"):
        track_id = track_uri.split(":")[-1].strip()
        if track_id:
            return f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator"
    marker = "track/"
    if marker in track_uri:
        tail = track_uri.split(marker, 1)[1]
        track_id = tail.split("?", 1)[0].strip().strip("/")
        if track_id:
            return f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator"
    return ""


def _inject_web_player(access_token: str, autoplay: bool = True, volume: int = 50) -> None:
        """Inject the Spotify Web Playback SDK and initialise the in-browser player."""
        autoplay_js = "true" if autoplay else "false"
        volume_normalized = max(0.0, min(1.0, volume / 100))
        js = f"""
(function() {{
    window._spotifyAccessToken = {repr(access_token)};
    window._spotifyPendingTrackUri = window._spotifyPendingTrackUri || null;
    window._nicheAutoplayEnabled = {autoplay_js};
    window._nicheWasPlaying = false;
    if (window._spotifyPlayerReady) return;

    window.onSpotifyWebPlaybackSDKReady = function() {{
        var player = new Spotify.Player({{
            name: 'Nichetify Web Player',
            getOAuthToken: function(cb) {{ cb(window._spotifyAccessToken); }},
            volume: {volume_normalized}
        }});

        window._spotifyTogglePlay = async function() {{
            if (window._spotifyPlayer) await window._spotifyPlayer.togglePlay();
        }};

        // Context-aware next / previous.
        window._nichePlaylist = window._nichePlaylist || [];
        window._nicheCurrentIndex = window._nicheCurrentIndex || 0;

        window._nicheSetPlaylist = function(uris, startIndex) {{
            window._nichePlaylist = uris || [];
            window._nicheCurrentIndex = startIndex || 0;
            if (uris && uris.length > 0) {{
                var _pos = (window._nicheCurrentIndex + 1) + ' / ' + uris.length;
                var _ctr = document.getElementById('nicheify-rec-counter');
                if (_ctr) _ctr.textContent = _pos;
                var _card = document.getElementById('nicheify-rec-card-pos');
                if (_card) _card.textContent = _pos;
            }}
        }};

        window._nichePlayAtIndex = async function(idx) {{
            var list = window._nichePlaylist;
            if (!list || list.length === 0) return;
            idx = ((idx % list.length) + list.length) % list.length;
            window._nicheCurrentIndex = idx;
            var _pos = (idx + 1) + ' / ' + list.length;
            var _ctr = document.getElementById('nicheify-rec-counter');
            if (_ctr) _ctr.textContent = _pos;
            var _card = document.getElementById('nicheify-rec-card-pos');
            if (_card) _card.textContent = _pos;
            // Update purple card track/artist labels if metadata is available.
            var _meta = window._nichePlaylistMeta;
            if (_meta && _meta[idx]) {{
                var m = _meta[idx];
                var _tn = document.getElementById('nicheify-rec-card-track');
                if (_tn) _tn.textContent = m.track || '';
                var _an = document.getElementById('nicheify-rec-card-artist');
                if (_an) _an.textContent = m.artist || '';
                var _gn = document.getElementById('nicheify-rec-card-genre');
                if (_gn) _gn.textContent = m.genre || '';
            }}
            var uri = list[idx];
            if (!uri) return;
            await window._spotifyPlayTrack(uri);
        }};

        window._spotifyNextTrack = async function() {{
            if (window._nichePlaylist && window._nichePlaylist.length > 0) {{
                await window._nichePlayAtIndex(window._nicheCurrentIndex + 1);
            }} else if (window._spotifyPlayer) {{
                await window._spotifyPlayer.nextTrack();
            }}
        }};

        window._spotifyPreviousTrack = async function() {{
            if (window._nichePlaylist && window._nichePlaylist.length > 0) {{
                await window._nichePlayAtIndex(window._nicheCurrentIndex - 1);
            }} else if (window._spotifyPlayer) {{
                await window._spotifyPlayer.previousTrack();
            }}
        }};

        window._spotifySetVolume = async function(volumePercent) {{
            if (!window._spotifyPlayer) return;
            var normalized = Math.max(0, Math.min(1, Number(volumePercent || 0) / 100));
            await window._spotifyPlayer.setVolume(normalized);
            // Update volume icon
            var volIcon = document.getElementById('nicheify-vol-icon');
            if (volIcon) {{
                volIcon.textContent = normalized === 0 ? 'volume_off'
                    : normalized < 0.4 ? 'volume_down' : 'volume_up';
            }}
        }};

        window._spotifyPlayTrack = async function(uri) {{
            window._spotifyPendingTrackUri = uri;
            // Extract track ID from URI immediately so liked-songs works even
            // before player_state_changed fires (e.g. not the active device).
            if (uri && uri.startsWith('spotify:track:')) {{
                window._nicheCurrentTrackId = uri.split(':')[2] || null;
            }}
            if (window._spotifyPlayer && window._spotifyPlayer.activateElement) {{
                try {{
                    await window._spotifyPlayer.activateElement();
                }} catch (err) {{
                    console.warn('Spotify activateElement failed', err);
                }}
            }}
            if (!window._spotifyDeviceId) return;

            var response = await fetch('https://api.spotify.com/v1/me/player/play?device_id=' + window._spotifyDeviceId, {{
                method: 'PUT',
                headers: {{
                    'Authorization': 'Bearer ' + window._spotifyAccessToken,
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{ uris: [uri] }})
            }});
            if (response.ok) {{
                window._spotifyPendingTrackUri = null;
            }} else {{
                console.warn('Spotify play failed', response.status);
            }}
        }};

        player.addListener('ready', function(data) {{
            window._spotifyDeviceId = data.device_id;
            player.setVolume({volume_normalized});
            fetch('https://api.spotify.com/v1/me/player', {{
                method: 'PUT',
                headers: {{
                    'Authorization': 'Bearer ' + window._spotifyAccessToken,
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{ device_ids: [data.device_id], play: false }})
            }}).finally(function() {{
                if (window._spotifyPendingTrackUri) {{
                    var pending = window._spotifyPendingTrackUri;
                    window._spotifyPlayTrack(pending);
                }}
            }});
        }});

        player.addListener('player_state_changed', function(state) {{
            if (!state) return;

            // Autoplay: detect natural track end (paused at position 0 after playing)
            if (window._nicheAutoplayEnabled && window._nicheWasPlaying &&
                    state.paused && state.position === 0 && state.duration > 0) {{
                window._spotifyNextTrack && window._spotifyNextTrack();
            }}
            window._nicheWasPlaying = !state.paused;

            // Update play/pause button icon
            var playBtn = document.getElementById('spotify-toggle-button');
            if (playBtn) {{
                var iconEl = playBtn.querySelector('.q-icon');
                if (iconEl) iconEl.textContent = state.paused ? 'play_arrow' : 'pause';
            }}

            // Update now-playing display
            var track = state.track_window.current_track;
            var nameEl   = document.getElementById('nicheify-track-name');
            var artistEl = document.getElementById('nicheify-artist-name');
            var artEl    = document.getElementById('nicheify-album-art');
            var seekBar  = document.getElementById('nicheify-seek-bar');
            var durLabel = document.getElementById('nicheify-dur-label');

            window._nicheCurrentTrackId = track.id || null;
            if (nameEl)   nameEl.textContent   = track.name;
            if (artistEl) artistEl.textContent = track.artists.map(function(a) {{ return a.name; }}).join(', ');
            if (artEl && track.album && track.album.images && track.album.images.length > 0) {{
                var imgs = track.album.images;
                artEl.src = imgs[imgs.length > 1 ? 1 : 0].url;
                artEl.style.display = 'block';
                var artPh = document.getElementById('nicheify-album-placeholder');
                if (artPh) artPh.style.display = 'none';
            }} else if (artEl) {{
                artEl.style.display = 'none';
                var artPh = document.getElementById('nicheify-album-placeholder');
                if (artPh) artPh.style.display = 'block';
            }}
            var dur = state.duration;
            if (seekBar) seekBar.max = dur;
            if (durLabel) {{
                var ds = Math.floor(dur / 1000);
                durLabel.textContent = Math.floor(ds / 60) + ':' + String(ds % 60).padStart(2, '0');
            }}

            // Snapshot for progress interpolation
            window._niche_pos    = state.position;
            window._niche_dur    = state.duration;
            window._niche_paused = state.paused;
            window._niche_ts     = Date.now();
        }});

        player.connect();
        window._spotifyPlayer = player;
        window._spotifyPlayerReady = true;

        // â”€â”€ Progress bar polling (500 ms tick) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if (window._nicheProgressInterval) clearInterval(window._nicheProgressInterval);
        window._nicheProgressInterval = setInterval(function() {{
            var seekBar  = document.getElementById('nicheify-seek-bar');
            var posLabel = document.getElementById('nicheify-pos-label');
            if (!seekBar || !posLabel || !window._niche_ts) return;
            var elapsed = window._niche_paused ? 0 : (Date.now() - window._niche_ts);
            var pos = Math.min((window._niche_pos || 0) + elapsed, window._niche_dur || 0);
            if (!seekBar._dragging) seekBar.value = pos;
            var ps = Math.floor(pos / 1000);
            posLabel.textContent = Math.floor(ps / 60) + ':' + String(ps % 60).padStart(2, '0');
        }}, 500);

        // â”€â”€ Seek bar drag-to-seek â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if (!window._nicheSeekListeners) {{
            window._nicheSeekListeners = true;
            document.addEventListener('mousedown', function(e) {{
                if (e.target && e.target.id === 'nicheify-seek-bar') e.target._dragging = true;
            }});
            function doSeek(target) {{
                target._dragging = false;
                if (window._spotifyPlayer) {{
                    var ms = Number(target.value);
                    window._spotifyPlayer.seek(ms).then(function() {{
                        window._niche_pos = ms;
                        window._niche_ts  = Date.now();
                    }});
                }}
            }}
            document.addEventListener('mouseup', function(e) {{
                if (e.target && e.target.id === 'nicheify-seek-bar') doSeek(e.target);
            }});
            document.addEventListener('touchend', function(e) {{
                var t = e.target || (e.changedTouches && e.changedTouches[0] && e.changedTouches[0].target);
                if (t && t.id === 'nicheify-seek-bar') doSeek(t);
            }});
        }}
    }};

    if (typeof Spotify !== 'undefined') {{
        window.onSpotifyWebPlaybackSDKReady();
    }} else {{
        var script = document.createElement('script');
        script.src = 'https://sdk.scdn.co/spotify-player.js';
        script.async = true;
        document.head.appendChild(script);
    }}

    // Always define toast + liked-songs outside the SDK-ready guard so the
    // button works even if onSpotifyWebPlaybackSDKReady fires before this IIFE.
    window._nicheToast = function(msg, color) {{
        var t = document.createElement('div');
        t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:' + color + ';color:#fff;padding:10px 20px;border-radius:10px;z-index:99999;font-size:14px;pointer-events:none;box-shadow:0 2px 12px rgba(0,0,0,0.4);';
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(function() {{ if (t.parentNode) t.parentNode.removeChild(t); }}, 3000);
    }};

    window._nicheAddToLiked = async function() {{
        var trackId = window._nicheCurrentTrackId || null;
        if (!trackId) {{
            window._nicheToast('Play a track first.', '#555');
            return;
        }}
        var btn = document.getElementById('nicheify-like-btn');
        var icon = btn ? btn.querySelector('.material-icons') : null;
        var resp = await fetch('https://api.spotify.com/v1/me/tracks', {{
            method: 'PUT',
            headers: {{
                'Authorization': 'Bearer ' + window._spotifyAccessToken,
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{ ids: [trackId] }})
        }});
        if (resp.ok) {{
            if (btn) btn.style.color = '#1db954';
            if (icon) icon.textContent = 'check_circle';
            window._nicheToast('Added to Liked Songs!', '#1db954');
            setTimeout(function() {{
                if (btn) btn.style.color = 'rgba(255,255,255,0.4)';
                if (icon) icon.textContent = 'add_circle';
            }}, 2500);
        }} else if (resp.status === 403) {{
            if (btn) btn.style.color = '#f59e0b';
            if (icon) icon.textContent = 'error';
            window._nicheToast('Re-connect Spotify to enable Liked Songs.', '#f59e0b');
            setTimeout(function() {{
                if (btn) btn.style.color = 'rgba(255,255,255,0.4)';
                if (icon) icon.textContent = 'add_circle';
            }}, 3000);
        }} else {{
            if (btn) btn.style.color = '#ef4444';
            if (icon) icon.textContent = 'error';
            window._nicheToast('Could not save. Try again.', '#ef4444');
            setTimeout(function() {{
                if (btn) btn.style.color = 'rgba(255,255,255,0.4)';
                if (icon) icon.textContent = 'add_circle';
            }}, 2500);
        }}
    }};
}})();
"""
        ui.run_javascript(js)


def render_spotify_player(controller: ListeningController, logic: AppLogic, current_user: User) -> None:
        """Render the global Spotify player at the top of the dashboard."""

        def launch_web_player() -> None:
                try:
                        token = controller.get_access_token_resilient(
                                current_user,
                                refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                force_refresh=True,
                        )
                        if not token:
                                return
                        _inject_web_player(token, volume=current_user.settings.get("volume", 50))
                except Exception:
                        return

        def connect_spotify() -> None:
                if not current_user.id:
                        ui.notify("Cannot connect Spotify: user ID is missing.", type="negative")
                        return
                try:
                        auth_url = controller.start_secure_connection(current_user.id)
                        ui.notify("Opening Spotify secure login.", type="positive")
                        ui.navigate.to(auth_url)
                except SpotifyRateLimitError:
                        ui.notify(
                                "Spotify is rate-limited — please wait a minute, then click Recommend again.",
                                type="warning",
                        )
                        _rec_state["active"] = False
                        return
                except Exception as exc:
                        ui.notify(str(exc), type="negative")

        def disconnect_spotify() -> None:
                if not current_user.id:
                        ui.notify("Cannot disconnect Spotify: user ID is missing.", type="negative")
                        return
                controller.disconnect(current_user.id)
                ui.notify("Spotify session removed.", type="positive")

        async def toggle_playback() -> None:
                await ui.run_javascript("window._spotifyTogglePlay && window._spotifyTogglePlay();")

        async def previous_track() -> None:
                if _rec_state.get("active") and _rec_state["pool"]:
                        # Recommendation mode: drive navigation through Python
                        new_idx = max(_rec_state["index"] - 1, 0)
                        _rec_state["index"] = new_idx
                        await _play_rec_current()
                else:
                        await ui.run_javascript("window._spotifyPreviousTrack && window._spotifyPreviousTrack();")

        async def next_track() -> None:
                if _rec_state.get("active") and _rec_state["pool"]:
                        # Recommendation mode: drive navigation through Python
                        new_idx = _rec_state["index"] + 1
                        if new_idx >= len(_rec_state["pool"]):
                                ui.notify("End of recommendations. Click Recommend again for more.", type="info")
                                _rec_state["active"] = False
                                return
                        _rec_state["index"] = new_idx
                        await _play_rec_current()
                else:
                        await ui.run_javascript("window._spotifyNextTrack && window._spotifyNextTrack();")

        def on_volume_change(e) -> None:
                vol = int(e.value)
                ui.run_javascript(f"window._spotifySetVolume && window._spotifySetVolume({vol});")
                current_user.settings["volume"] = vol
                asyncio.ensure_future(asyncio.to_thread(
                        logic.update_user_data,
                        current_user, current_user.id,
                        current_user.playlists,
                        current_user.liked_songs,
                        current_user.settings,
                ))

        # â”€â”€ Discover: lesser-known recs wired directly into the player â”€â”€â”€â”€â”€â”€â”€â”€
        _rec_state: dict = {"pool": [], "index": 0, "active": False}

        async def _save_rec_to_history(rec: dict) -> None:
                import time as _time
                history = list(current_user.settings.get("rec_history", []))
                uri = str(rec.get("uri") or "")
                recent_uris = {e.get("uri") for e in history[-30:]}
                if uri and uri in recent_uris:
                        return
                entry = {
                        "track": str(rec.get("track", "")),
                        "artist": str(rec.get("artist", "")),
                        "genre": str(rec.get("genre", "") or ""),
                        "uri": uri,
                        "ts": int(_time.time()),
                }
                history.append(entry)
                if len(history) > 100:
                        history = history[-100:]
                current_user.settings["rec_history"] = history
                try:
                        await asyncio.to_thread(
                                logic.update_user_data,
                                current_user, current_user.id,
                                current_user.playlists,
                                current_user.liked_songs,
                                current_user.settings,
                        )
                except Exception:
                        pass

        async def _play_rec_current() -> None:
                pool = _rec_state["pool"]
                idx = _rec_state["index"]
                if not pool:
                        return
                rec = pool[idx]
                track_name = str(rec.get("track", "Unknown"))
                artist_name = str(rec.get("artist", "Unknown"))
                try:
                        preloaded_uri = str(rec.get("uri") or "")
                        if preloaded_uri:
                                uri = preloaded_uri
                        else:
                                uri = await asyncio.to_thread(
                                        controller.search_track_uri,
                                        current_user,
                                        track_name,
                                        artist_name,
                                        lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                )
                        if not uri:
                                # Silently skip tracks not found on Spotify — iTunes has many
                                # tracks that aren't available in the Spotify catalogue.
                                # Keep advancing until a playable track is found or pool exhausted.
                                next_idx = idx + 1
                                if next_idx < len(pool):
                                        _rec_state["index"] = next_idx
                                        await _play_rec_current()
                                else:
                                        ui.notify("No playable tracks found in this set. Click Recommend again.", type="negative")
                                        _rec_state["active"] = False
                                return
                        safe_uri = json.dumps(str(uri))
                        pool_uris = [str(r.get("uri") or "") for r in pool]
                        safe_pool_uris = json.dumps(pool_uris)
                        pool_meta = [{"track": str(r.get("track", "")), "artist": str(r.get("artist", "")), "genre": str(r.get("genre", "") or "")} for r in pool]
                        safe_pool_meta = json.dumps(pool_meta)
                        _pos = f"{idx + 1} / {len(pool)}"
                        await ui.run_javascript(
                                "if(window._nicheSetPlaylist){"
                                "  window._nicheSetPlaylist(" + safe_pool_uris + ", " + str(idx) + ");"
                                "}"
                                "window._nichePlaylistMeta = " + safe_pool_meta + ";"
                                "if(window._spotifyPlayTrack){window._spotifyPlayTrack(" + safe_uri + ");}"
                                "window.scrollTo({top:0,behavior:'smooth'});"
                        )
                        ui.run_javascript(
                                f"var el=document.getElementById('nicheify-rec-counter');"
                                f"if(el) el.textContent={json.dumps(_pos)};"
                        )
                        await _save_rec_to_history(rec)
                        _rec_state["skips"] = 0
                except Exception as exc:
                        ui.notify(str(exc), type="negative")

        async def _fetch_pool() -> None:
                if not current_user.id:
                        ui.notify("Cannot load recommendations -- please log in.", type="negative")
                        return
                _loading_row.set_visibility(True)
                try:
                        recs = await asyncio.to_thread(
                                controller.get_song_recommendations_resilient,
                                current_user,
                                lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                30,
                                85,
                                30.0,
                        )
                except Exception as exc:
                        _loading_row.set_visibility(False)
                        ui.notify(str(exc), type="negative")
                        return
                _loading_row.set_visibility(False)
                if not recs:
                        ui.notify("No recommendations found -- try loading your top tracks first.", type="warning")
                        return
                _rec_state["pool"] = recs
                _rec_state["index"] = 0
                _rec_state["active"] = True
                await _play_rec_current()

        with ui.card().classes("w-full gap-3"):
                with ui.row().classes("w-full items-center justify-between gap-3"):
                        ui.label("Player").classes("text-h6")
                        with ui.row().classes("items-center gap-2"):
                                ui.button("Connect Spotify", on_click=connect_spotify).props("icon=security color=green")
                                ui.button("Disconnect", on_click=disconnect_spotify).props("icon=logout color=negative")

                # Custom now-playing display â€” driven by the Spotify Web Playback SDK.
                # No iframe needed; album art, track name, artist, and a seek bar are
                # all updated via player_state_changed events in JavaScript.
                ui.html("""
                    <div id="nicheify-now-playing" style="
                        display:flex; align-items:center; gap:14px;
                        background:#121212; border-radius:12px; padding:12px 16px;
                        width:100%; box-sizing:border-box;">
                      <div style="width:72px; height:72px; border-radius:8px; background:#282828; flex-shrink:0; display:flex; align-items:center; justify-content:center; overflow:hidden; position:relative;">
                        <span id="nicheify-album-placeholder" class="material-icons" style="color:#535353; font-size:36px; position:absolute;">music_note</span>
                        <img id="nicheify-album-art" src="" style="width:72px; height:72px; object-fit:cover; display:none; position:relative; z-index:1;" onerror="this.style.display='none'; var ph=document.getElementById('nicheify-album-placeholder'); if(ph) ph.style.display='block';" />
                      </div>
                      <div style="flex:1; min-width:0;">
                        <div style="display:flex; align-items:center; gap:6px;">
                          <div id="nicheify-track-name"
                            style="color:#fff; font-size:15px; font-weight:700;
                                   white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; min-width:0;">
                            Not Playing
                          </div>
                          <button id="nicheify-like-btn"
                            onclick="window._nicheAddToLiked && window._nicheAddToLiked()"
                            title="Add to Liked Songs"
                            style="background:none; border:none; cursor:pointer;
                                   color:rgba(255,255,255,0.4); padding:0; line-height:1;
                                   flex-shrink:0; transition:color 0.2s; display:flex;">
                            <span class="material-icons" style="font-size:20px;">add_circle</span>
                          </button>
                        </div>
                        <div id="nicheify-artist-name"
                          style="color:#b3b3b3; font-size:13px; margin-top:2px;
                                 white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                          &mdash;
                        </div>
                        <div style="display:flex; align-items:center; gap:8px; margin-top:10px;">
                          <span id="nicheify-pos-label"
                            style="color:#b3b3b3; font-size:11px; min-width:32px; font-family:monospace;">0:00</span>
                          <input id="nicheify-seek-bar" type="range" min="0" max="100" value="0"
                            style="flex:1; height:4px; accent-color:#1db954; cursor:pointer; outline:none;" />
                          <span id="nicheify-dur-label"
                            style="color:#b3b3b3; font-size:11px; min-width:32px;
                                   text-align:right; font-family:monospace;">0:00</span>
                        </div>
                      </div>
                    </div>
                """).classes("w-full")

                with ui.row().classes("items-center gap-3 mt-1 flex-wrap"):
                        ui.button(icon="skip_previous", on_click=previous_track).props("color=primary round")
                        ui.button(icon="play_arrow", on_click=toggle_playback).props("id=spotify-toggle-button color=primary round")
                        ui.button(icon="skip_next", on_click=next_track).props("color=primary round")
                        ui.html('<span id="nicheify-rec-counter" style="color:#b3b3b3; font-size:13px; font-family:monospace; min-width:48px;">- / -</span>')
                        ui.icon("volume_up").props("id=nicheify-vol-icon").classes("text-grey-5 text-2xl ml-4")
                        ui.slider(min=0, max=100, value=current_user.settings.get("volume", 50), step=1, on_change=on_volume_change).props("color=green track-size=8px thumb-size=16px").classes("w-48")
                        ui.button("Recommend a Song", icon="explore", on_click=_fetch_pool).props("color=deep-purple rounded")
                with ui.row().classes("items-center gap-2 mt-1"):
                        ui.icon("info").classes("text-grey-6 text-sm")
                        ui.label("Discover lesser-known songs based on your listening profile. Use the skip button to go to the next one.").classes("text-caption text-grey-5")
                _loading_row = ui.row().classes("items-center gap-2 mt-2")
                with _loading_row:
                        ui.spinner("dots", color="deep-purple", size="sm")
                        ui.label("Finding a lesser-known song for you...").classes("text-caption text-purple-300")
                _loading_row.set_visibility(False)

        ui.timer(0.1, launch_web_player, once=True)




def render_listening_module(controller: ListeningController, logic: AppLogic, current_user: User) -> None:
    """Render the Listening History panel inside a tab panel."""

    def _expansion(*args, **kwargs):
        """Fallback to a plain column for lightweight test UI stubs."""
        expansion_fn = getattr(ui, "expansion", None)
        if callable(expansion_fn):
            return expansion_fn(*args, **kwargs)
        return ui.column()

    def _notify(msg: str, *, type: str = "info") -> None:  # noqa: A002
        """Show a notification only if the user has notifications enabled."""
        if current_user.settings.get("notifications_enabled", True):
            ui.notify(msg, type=type)

    with ui.column().classes("w-full gap-4"):

        # â”€â”€ Top Tracks expansion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        top_tracks_expansion = _expansion(
            "Your Top Tracks"
        ).classes("w-full").props("default-opened header-class=text-h6")

        with top_tracks_expansion:
            tracks_container = ui.column().classes("w-full")

        async def refresh_tracks() -> None:
            if not current_user.id:
                tracks_container.clear()
                _notify("User session missing; re-login required.", type="negative")
                return

            tracks_container.clear()
            if hasattr(top_tracks_expansion, "open"):
                top_tracks_expansion.open()
            with tracks_container:
                with ui.row().classes("items-center gap-2"):
                    ui.spinner("dots")
                    ui.label("Loading top tracksâ€¦").classes("text-grey")

            try:
                tracks = await asyncio.to_thread(
                    controller.get_top_tracks,
                    current_user,
                    lambda u: logic.get_decrypted_refresh_token(u, u.id),
                )
            except Exception as exc:
                tracks_container.clear()
                _notify(str(exc), type="negative")
                return

            tracks_container.clear()
            # Build a flat list of URIs to drive prev/next navigation.
            track_uris = [str(t.get("uri", "")) for t in tracks]
            safe_track_uris = json.dumps(track_uris)

            with tracks_container:
                ui.label("Click a track to play it in the web player.").classes("text-caption text-grey mb-2")

                for idx, track in enumerate(tracks):
                    track_uri = track.get("uri", "")
                    embed_url = _spotify_embed_url(str(track_uri))

                    async def _play(_, uri=track_uri, embed=embed_url, track_idx=idx) -> None:
                        try:
                            token = controller.get_access_token_resilient(
                                current_user,
                                refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                force_refresh=True,
                            )
                            if not token:
                                _notify("Connect Spotify first.", type="warning")
                                return
                            _inject_web_player(token, autoplay=bool(current_user.settings.get("autoplay_enabled", True)), volume=current_user.settings.get("volume", 50))
                            safe_uri = json.dumps(str(uri))
                            # Register this track list as the active playlist so
                            # prev/next buttons walk the top-tracks list.
                            await ui.run_javascript(
                                "window._spotifyPendingTrackUri = " + safe_uri + ";"
                                "if(window._nicheSetPlaylist){"
                                "  window._nicheSetPlaylist(" + safe_track_uris + ", " + str(track_idx) + ");"
                                "}"
                                "if(window._spotifyPlayTrack){window._spotifyPlayTrack(" + safe_uri + ");}"
                            )
                        except Exception as exc:
                            _notify(str(exc), type="negative")

                    with ui.row().classes(
                        "w-full items-center gap-4 px-3 py-2 rounded cursor-pointer "
                        "hover:bg-green-900 transition-colors"
                    ).on("click", _play):
                        ui.icon("play_circle").classes("text-green-400 text-2xl")
                        with ui.column().classes("gap-0"):
                            ui.label(track["title"]).classes("text-body1 font-bold")
                            ui.label(track["artist"]).classes("text-caption text-grey")
                        ui.label(f"Popularity: {track['plays']}").classes("text-caption text-grey ml-auto")

        # Load button sits below the expansion header but is always visible.
        with ui.row().classes("items-center gap-3"):
            ui.button("Load Top Tracks", on_click=refresh_tracks).props("icon=queue_music color=secondary")

        # ---- Recommendation History ----------------------------------------
        history_expansion = _expansion(
            "Recommendation History", icon="history"
        ).classes("w-full").props("header-class=text-subtitle2")

        with history_expansion:
            hist_container = ui.column().classes("w-full")

            def _render_history() -> None:
                hist_container.clear()
                history = current_user.settings.get("rec_history", [])
                if not history:
                    with hist_container:
                        ui.label("No recommendations yet. Use 'Recommend a Song' to discover tracks.").classes("text-caption text-grey-5 px-2")
                    return
                with hist_container:
                    for entry in reversed(history[-30:]):
                        with ui.row().classes("w-full items-center gap-3 px-2 py-1"):
                            ui.icon("music_note").classes("text-purple-400 text-sm flex-shrink-0")
                            with ui.column().classes("gap-0 flex-1 min-w-0"):
                                ui.label(entry.get("track", "Unknown")).classes("text-body2 font-bold")
                                ui.label(entry.get("artist", "")).classes("text-caption text-grey")
                            if entry.get("genre"):
                                ui.badge(entry["genre"]).props("color=purple")

            async def _clear_history() -> None:
                current_user.settings["rec_history"] = []
                try:
                    await asyncio.to_thread(
                        logic.update_user_data,
                        current_user, current_user.id,
                        current_user.playlists,
                        current_user.liked_songs,
                        current_user.settings,
                    )
                except Exception:
                    pass
                _render_history()
                ui.notify("Recommendation history cleared.", type="positive")

            with ui.row().classes("w-full justify-end items-center gap-2 mb-1"):
                ui.button("Refresh", icon="refresh", on_click=_render_history).props("color=secondary flat size=sm")
                ui.button("Clear History", icon="delete_sweep", on_click=_clear_history).props("color=negative flat size=sm")

            _render_history()
