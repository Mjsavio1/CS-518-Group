import asyncio
import json

from nicegui import ui

from .listening_controller import ListeningController
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


def _inject_web_player(access_token: str) -> None:
        """Inject the Spotify Web Playback SDK and initialise the in-browser player."""
        js = f"""
(function() {{
    window._spotifyAccessToken = {repr(access_token)};
    window._spotifyPendingTrackUri = window._spotifyPendingTrackUri || null;
    if (window._spotifyPlayerReady) return;

    window.onSpotifyWebPlaybackSDKReady = function() {{
        var player = new Spotify.Player({{
            name: 'Nichetify Web Player',
            getOAuthToken: function(cb) {{ cb(window._spotifyAccessToken); }},
            volume: 0.5
        }});

        window._spotifyTogglePlay = async function() {{
            if (window._spotifyPlayer) await window._spotifyPlayer.togglePlay();
        }};

        window._spotifyNextTrack = async function() {{
            if (window._spotifyPlayer) await window._spotifyPlayer.nextTrack();
        }};

        window._spotifyPreviousTrack = async function() {{
            if (window._spotifyPlayer) await window._spotifyPlayer.previousTrack();
        }};

        window._spotifySetVolume = async function(volumePercent) {{
            if (!window._spotifyPlayer) return;
            var normalized = Math.max(0, Math.min(1, Number(volumePercent || 0) / 100));
            await window._spotifyPlayer.setVolume(normalized);
            localStorage.setItem('playerVolume', String(Math.round(normalized * 100)));
        }};

        window._spotifyPlayTrack = async function(uri) {{
            window._spotifyPendingTrackUri = uri;
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
            var savedVolume = Number(localStorage.getItem('playerVolume') || '50');
            player.setVolume(Math.max(0, Math.min(1, savedVolume / 100)));
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
            var playBtn = document.getElementById('spotify-toggle-button');
            if (playBtn) {{
                var iconEl = playBtn.querySelector('.q-icon');
                if (iconEl) {{
                    iconEl.textContent = state.paused ? 'play_arrow' : 'pause';
                }}
            }}
        }});

        player.connect();
        window._spotifyPlayer = player;
        window._spotifyPlayerReady = true;
    }};

    if (typeof Spotify !== 'undefined') {{
        window.onSpotifyWebPlaybackSDKReady();
    }} else {{
        var script = document.createElement('script');
        script.src = 'https://sdk.scdn.co/spotify-player.js';
        script.async = true;
        document.head.appendChild(script);
    }}
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
                        _inject_web_player(token)
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
                await ui.run_javascript("window._spotifyPreviousTrack && window._spotifyPreviousTrack();")

        async def next_track() -> None:
                await ui.run_javascript("window._spotifyNextTrack && window._spotifyNextTrack();")

        def on_volume_change(e) -> None:
                ui.run_javascript(f"window._spotifySetVolume && window._spotifySetVolume({int(e.value)});")

        with ui.card().classes("w-full gap-3"):
                with ui.row().classes("w-full items-center justify-between gap-3"):
                        ui.label("Player").classes("text-h6")
                        with ui.row().classes("items-center gap-2"):
                                ui.button("Connect Spotify", on_click=connect_spotify).props("icon=security color=green")
                                ui.button("Disconnect", on_click=disconnect_spotify).props("icon=logout color=negative")

                with ui.row().classes("w-full"):
                        ui.element("iframe") \
                                .props(
                                        'id=spotify-embed-player src="https://open.spotify.com/embed/track/11dFghVXANMlKmJXsNCbNl?utm_source=generator" '
                                        'width="100%" height="152" frameborder="0" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"'
                                ) \
                                .style("border-radius:12px; width:100%;")

                with ui.row().classes("items-center gap-3"):
                        ui.button(icon="skip_previous", on_click=previous_track).props("color=primary round")
                        ui.button(icon="play_arrow", on_click=toggle_playback).props("id=spotify-toggle-button color=primary round")
                        ui.button(icon="skip_next", on_click=next_track).props("color=primary round")
                        ui.slider(min=0, max=100, value=50, step=1, on_change=on_volume_change).props("label=Volume").classes("w-64")

        ui.timer(0.1, launch_web_player, once=True)


def render_listening_module(controller: ListeningController, logic: AppLogic, current_user: User) -> None:
    """Render the Listening History panel inside a tab panel."""
    with ui.column().classes("w-full gap-4"):
        tracks_container = ui.column().classes("w-full")

        async def refresh_tracks() -> None:
            if not current_user.id:
                tracks_container.clear()
                ui.notify("User session missing; re-login required.", type="negative")
                return

            tracks_container.clear()
            with tracks_container:
                with ui.row().classes("items-center gap-2"):
                    ui.spinner("dots")
                    ui.label("Loading top tracks…").classes("text-grey")

            try:
                tracks = await asyncio.to_thread(
                    controller.get_top_tracks,
                    current_user,
                    lambda u: logic.get_decrypted_refresh_token(u, u.id),
                )
            except Exception as exc:
                tracks_container.clear()
                ui.notify(str(exc), type="negative")
                return

            tracks_container.clear()
            with tracks_container:
                ui.label("Your Top Tracks").classes("text-h6 mt-2")
                ui.label("Click a track to play it in the web player.").classes("text-caption text-grey mb-2")

                for track in tracks:
                    track_uri = track.get("uri", "")
                    embed_url = _spotify_embed_url(str(track_uri))

                    async def _play(_, uri=track_uri, embed=embed_url) -> None:
                        try:
                            if embed:
                                safe_embed = json.dumps(embed)
                                await ui.run_javascript(
                                    "var frame=document.getElementById('spotify-embed-player');"
                                    "if(frame){frame.src=" + safe_embed + ";}"
                                )

                            token = controller.get_access_token_resilient(
                                current_user,
                                refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                force_refresh=True,
                            )
                            if not token:
                                ui.notify("Connect Spotify first.", type="warning")
                                return
                            _inject_web_player(token)
                            safe_uri = json.dumps(str(uri))
                            await ui.run_javascript(
                                "window._spotifyPendingTrackUri = " + safe_uri + ";"
                                "if(window._spotifyPlayTrack){window._spotifyPlayTrack(" + safe_uri + ");}"
                            )
                        except Exception as exc:
                            ui.notify(str(exc), type="negative")

                    with ui.row().classes(
                        "w-full items-center gap-4 px-3 py-2 rounded cursor-pointer "
                        "hover:bg-green-900 transition-colors"
                    ).on("click", _play):
                        ui.icon("play_circle").classes("text-green-400 text-2xl")
                        with ui.column().classes("gap-0"):
                            ui.label(track["title"]).classes("text-body1 font-bold")
                            ui.label(track["artist"]).classes("text-caption text-grey")
                        ui.label(f"Popularity: {track['plays']}").classes("text-caption text-grey ml-auto")

        def connect_spotify() -> None:
            if not current_user.id:
                ui.notify("Cannot connect Spotify: user ID is missing.", type="negative")
                return
            try:
                auth_url = controller.start_secure_connection(current_user.id)
                ui.notify("Opening Spotify secure login.", type="positive")
                ui.navigate.to(auth_url)
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        def disconnect_spotify() -> None:
            if not current_user.id:
                ui.notify("Cannot disconnect Spotify: user ID is missing.", type="negative")
                return
            controller.disconnect(current_user.id)
            tracks_container.clear()
            ui.notify("Spotify session removed.", type="positive")

        with ui.row().classes("items-center gap-3"):
            ui.button("Load Top Tracks", on_click=refresh_tracks).props("icon=queue_music color=secondary")

        ui.separator()
        ui.label("Discover Lesser-Known Songs").classes("text-h6")
        ui.label(
            "Based on your listening profile, these songs come from less familiar artists "
            "with lower popularity." 
        ).classes("text-caption text-grey")

        rec_container = ui.column().classes("w-full")

        async def load_recommendations() -> None:
            if not current_user.id:
                ui.notify("Cannot load recommendations: user session missing.", type="negative")
                return

            rec_container.clear()
            with rec_container:
                with ui.row().classes("items-center gap-2"):
                    ui.spinner("dots", color="deep-purple")
                    ui.label("Finding lesser-known songs…").classes("text-grey")

            try:
                recs = await asyncio.to_thread(
                    controller.get_song_recommendations_resilient,
                    current_user,
                    lambda u: logic.get_decrypted_refresh_token(u, u.id),
                    10,
                    65,
                )
                debug_info = controller.get_last_song_recommendation_debug(current_user.id)
                rec_container.clear()
                with rec_container:
                    if recs:
                        for rec in recs:
                            track_uri = rec.get("uri", "")
                            embed_url = _spotify_embed_url(str(track_uri)) if track_uri else ""

                            async def _play_rec(_, uri=track_uri, embed=embed_url) -> None:
                                try:
                                    if embed:
                                        safe_embed = json.dumps(embed)
                                        await ui.run_javascript(
                                            "var frame=document.getElementById('spotify-embed-player');"
                                            "if(frame){frame.src=" + safe_embed + ";}"
                                        )
                                    if not uri:
                                        ui.notify("No playback URI for this track.", type="warning")
                                        return
                                    token = controller.get_access_token_resilient(
                                        current_user,
                                        refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id),
                                        force_refresh=True,
                                    )
                                    if not token:
                                        ui.notify("Connect Spotify first.", type="warning")
                                        return
                                    _inject_web_player(token)
                                    safe_uri = json.dumps(str(uri))
                                    await ui.run_javascript(
                                        "window._spotifyPendingTrackUri = " + safe_uri + ";"
                                        "if(window._spotifyPlayTrack){window._spotifyPlayTrack(" + safe_uri + ");}"
                                    )
                                except Exception as exc:
                                    ui.notify(str(exc), type="negative")

                            with ui.row().classes(
                                "w-full items-center gap-4 px-3 py-2 rounded cursor-pointer "
                                "hover:bg-purple-900 transition-colors"
                            ).on("click", _play_rec):
                                icon_name = "play_circle" if track_uri else "music_note"
                                ui.icon(icon_name).classes("text-purple-400 text-2xl")
                                with ui.column().classes("gap-0"):
                                    ui.label(str(rec.get("track", "Unknown"))).classes("text-body1 font-bold")
                                    ui.label(str(rec.get("artist", "Unknown"))).classes("text-caption text-grey")
                                with ui.column().classes("gap-0 ml-auto items-end"):
                                    ui.label(f"Popularity: {rec.get('popularity', '?')}").classes("text-caption text-grey")
                                    ui.label(str(rec.get("genre", ""))).classes("text-caption text-purple-300")
                    else:
                        ui.label("No lesser-known song recommendations found. Try reconnecting Spotify and loading top tracks first.").classes("text-grey")
                        if debug_info:
                            with ui.expansion("Recommendation debug details", icon="bug_report").classes("w-full mt-2"):
                                ui.code(json.dumps(debug_info, indent=2), language="json").classes("w-full")
            except Exception as exc:
                rec_container.clear()
                ui.notify(str(exc), type="negative")

        ui.button("Get Recommendations", on_click=load_recommendations).props("icon=explore color=deep-purple")

        ui.separator()
        ui.label("Saved Music Preferences").classes("text-h6")
        playlists_input = ui.textarea(
            "Playlists (one per line)",
            value="\n".join(current_user.playlists),
        ).classes("w-full")
        liked_songs_input = ui.textarea(
            "Liked Songs (one per line)",
            value="\n".join(current_user.liked_songs),
        ).classes("w-full")

        settings = dict(current_user.settings)
        theme_setting = str(settings.get("theme", "system"))
        notifications_enabled = bool(settings.get("notifications_enabled", True))
        autoplay_enabled = bool(settings.get("autoplay_enabled", True))

        with ui.row().classes("items-center gap-6"):
            theme_select = ui.select(
                options=["system", "light", "dark"],
                value=theme_setting,
                label="Theme",
            )
            notifications_toggle = ui.switch("Notifications", value=notifications_enabled)
            autoplay_toggle = ui.switch("Autoplay", value=autoplay_enabled)

        def save_preferences() -> None:
            if not current_user.id:
                ui.notify("Cannot save preferences: user ID is missing.", type="negative")
                return

            updated_settings = {
                **settings,
                "theme": theme_select.value,
                "notifications_enabled": bool(notifications_toggle.value),
                "autoplay_enabled": bool(autoplay_toggle.value),
            }

            try:
                updated_user = logic.update_user_data(
                    requester=current_user,
                    user_id=current_user.id,
                    playlists=_parse_lines(playlists_input.value or ""),
                    liked_songs=_parse_lines(liked_songs_input.value or ""),
                    settings=updated_settings,
                )
                SessionManager.login(updated_user)
                current_user.playlists = list(updated_user.playlists)
                current_user.liked_songs = list(updated_user.liked_songs)
                current_user.settings = dict(updated_user.settings)
                ui.notify("Preferences saved.", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        ui.button("Save Preferences", on_click=save_preferences).props("color=primary")
