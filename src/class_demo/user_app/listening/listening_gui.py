from nicegui import ui

from .listening_controller import ListeningController
from ...user_service.models import User
from ..interfaces import AppLogic
from ..session import SessionManager


def _parse_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def render_listening_module(controller: ListeningController, logic: AppLogic, current_user: User) -> None:
    """Render the Listening History panel inside a tab panel."""
    with ui.column().classes("w-full gap-4"):
        ui.label("Listening History").classes("text-h5")
        ui.label("Discover insights from your Spotify listening activity.").classes("text-subtitle1 text-grey")

        status_label = ui.label(controller.get_greeting()).classes("text-body1 text-primary")
        ui.label(controller.get_safety_notes()).classes("text-caption text-secondary")

        tracks_container = ui.column().classes("w-full")

        def _inject_web_player(access_token: str) -> None:
            """Inject the Spotify Web Playback SDK and initialise the in-browser player."""
            js = f"""
(function() {{
  if (window._spotifyPlayerReady) return;
  window._spotifyAccessToken = {repr(access_token)};

  window.onSpotifyWebPlaybackSDKReady = function() {{
    var player = new Spotify.Player({{
      name: 'Nichetify Web Player',
      getOAuthToken: function(cb) {{ cb(window._spotifyAccessToken); }},
      volume: 0.5
    }});

    window._spotifyPlayTrack = function(uri) {{
      if (!window._spotifyDeviceId) {{ console.warn('Device not ready'); return; }}
      fetch('https://api.spotify.com/v1/me/player/play?device_id=' + window._spotifyDeviceId, {{
        method: 'PUT',
        headers: {{
          'Authorization': 'Bearer ' + window._spotifyAccessToken,
          'Content-Type': 'application/json'
        }},
        body: JSON.stringify({{ uris: [uri] }})
      }}).then(function() {{
        var el = document.getElementById('spotify-now-playing');
        if (el) el.textContent = 'Loading...';
      }});
    }};

    player.addListener('ready', function(data) {{
      window._spotifyDeviceId = data.device_id;
      console.log('Spotify Web Player ready. Device ID:', data.device_id);
      fetch('https://api.spotify.com/v1/me/player', {{
        method: 'PUT',
        headers: {{
          'Authorization': 'Bearer ' + window._spotifyAccessToken,
          'Content-Type': 'application/json'
        }},
        body: JSON.stringify({{ device_ids: [data.device_id], play: false }})
      }});
    }});

    player.addListener('not_ready', function(data) {{
      console.warn('Spotify Web Player device went offline:', data.device_id);
    }});

    player.addListener('player_state_changed', function(state) {{
      if (!state) return;
      var track = state.track_window.current_track;
      var el = document.getElementById('spotify-now-playing');
      if (el && track) {{
        el.textContent = track.name + ' - ' + track.artists.map(function(a){{return a.name;}}).join(', ');
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

        def refresh_tracks() -> None:
            if not current_user.id:
                tracks_container.clear()
                status_label.set_text("User session missing; re-login required.")
                return

            try:
                tracks = controller.get_top_tracks(
                    current_user,
                    refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id),
                )
            except Exception as exc:
                tracks_container.clear()
                status_label.set_text(str(exc))
                return

            tracks_container.clear()
            with tracks_container:
                ui.label("Your Top Tracks").classes("text-h6 mt-2")
                ui.label("Click a track to play it in the web player.").classes("text-caption text-grey mb-2")

                for track in tracks:
                    track_uri = track.get("uri", "")

                    def _play(_, uri=track_uri) -> None:
                        token = controller.get_access_token(current_user.id)
                        if not token:
                            ui.notify("Connect Spotify first.", type="warning")
                            return
                        _inject_web_player(token)
                        ui.run_javascript(
                            f"if(window._spotifyDeviceId){{"
                            f"  window._spotifyPlayTrack('{uri}');"
                            f"}} else {{"
                            f"  setTimeout(function(){{window._spotifyPlayTrack('{uri}');}}, 2000);"
                            f"}}"
                        )

                    with ui.row().classes(
                        "w-full items-center gap-4 px-3 py-2 rounded cursor-pointer "
                        "hover:bg-green-900 transition-colors"
                    ).on("click", _play):
                        ui.icon("play_circle").classes("text-green-400 text-2xl")
                        with ui.column().classes("gap-0"):
                            ui.label(track["title"]).classes("text-body1 font-bold")
                            ui.label(track["artist"]).classes("text-caption text-grey")
                        ui.label(f"Popularity: {track['plays']}").classes("text-caption text-grey ml-auto")

                # --- Media Player UI ---
                with ui.row().classes("items-center gap-4 mt-4"):
                    ui.button(icon="skip_previous", on_click=lambda: controller.skip_back()).props("color=primary")
                    ui.button(icon="play_arrow", on_click=lambda: controller.play_pause()).props("color=primary")
                    ui.button(icon="skip_next", on_click=lambda: controller.skip_forward()).props("color=primary")
                # -----------------------

                # --- Volume Slider with Local Storage and Spotify API ---
                def on_volume_change(e):
                    volume = int(e.value)
                    ui.run_javascript(f"localStorage.setItem('playerVolume', {volume});")
                    controller.set_volume(volume)

                ui.slider(
                    min=0, max=100, value=50, step=1, on_change=on_volume_change
                ).props("label=Volume")

                ui.run_javascript("""
                    const savedVolume = localStorage.getItem('playerVolume');
                    if (savedVolume !== null) {
                        document.querySelector('input[type=range]').value = savedVolume;
                    }
                """)
                # ------------------------------------------------------

                # --- Duration Countdown Display ---
                duration_label = ui.label("Time left: --").classes("text-body2")

                def update_duration():
                    progress, duration = controller.get_playback_info()
                    if progress is not None and duration is not None:
                        duration_label.set_text(f"Time left: {duration - progress} sec")
                    else:
                        duration_label.set_text("Time left: --")

                def poll_duration():
                    update_duration()
                    ui.timer(1.0, poll_duration, once=True)

                poll_duration()
                # ----------------------------------

        def connect_spotify() -> None:
            if not current_user.id:
                ui.notify("Cannot connect Spotify: user ID is missing.", type="negative")
                return
            try:
                auth_url = controller.start_secure_connection(current_user.id)
                status_label.set_text("Redirecting to Spotify secure login; callback completes automatically after approval.")
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
            status_label.set_text("Spotify disconnected.")
            ui.notify("Spotify session removed.", type="positive")

        with ui.row().classes("items-center gap-3"):
            ui.button("Connect Spotify", on_click=connect_spotify).props("icon=security color=green")
            ui.button("Disconnect", on_click=disconnect_spotify).props("icon=logout color=negative")

        with ui.row().classes("items-center gap-3"):
            ui.button("Load Top Tracks", on_click=refresh_tracks).props("icon=queue_music color=secondary")

        # --- Spotify Web Playback SDK player ---
        ui.separator()
        ui.label("Spotify Web Player").classes("text-h6")
        with ui.row().classes("items-center gap-3"):
            ui.label("No track playing").classes("text-body1 text-grey").props("id=spotify-now-playing")
        with ui.row().classes("items-center gap-3"):
            ui.button("Launch Web Player", on_click=lambda: (
                _inject_web_player(controller.get_access_token(current_user.id))
                if controller.get_access_token(current_user.id)
                else ui.notify("Connect Spotify first.", type="warning")
            )).props("icon=speaker color=green")
        # ----------------------------------------

        ui.separator()
        ui.label("Discover Lesser-Known Artists").classes("text-h6")
        ui.label(
            "Based on your top tracks, these artists are similar to what you like "
            "but have a lower mainstream popularity score."
        ).classes("text-caption text-grey")

        rec_columns = [
            {"name": "name",       "label": "Artist",     "field": "name",       "align": "left"},
            {"name": "popularity", "label": "Popularity", "field": "popularity", "align": "center"},
            {"name": "genres",     "label": "Genres",     "field": "genres",     "align": "left"},
        ]
        rec_container = ui.column().classes("w-full")

        def load_recommendations() -> None:
            if not current_user.id:
                ui.notify("Cannot load recommendations: user session missing.", type="negative")
                return
            try:
                recs = controller.get_artist_recommendations(
                    user_id=current_user.id,
                    max_results=10,
                    popularity_max=60,
                )
                rec_container.clear()
                with rec_container:
                    if recs:
                        ui.table(columns=rec_columns, rows=recs).classes("w-full")
                    else:
                        ui.label("No lesser-known recommendations found. Try listening to more tracks first.").classes("text-grey")
            except Exception as exc:
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
