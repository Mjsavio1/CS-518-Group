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

        columns = [
            {"name": "title", "label": "Track", "field": "title", "align": "left"},
            {"name": "artist", "label": "Artist", "field": "artist", "align": "left"},
            {"name": "plays", "label": "Popularity", "field": "plays", "align": "right"},
        ]
        tracks_container = ui.column().classes("w-full")

        def refresh_tracks() -> None:
            if not current_user.id:
                tracks_container.clear()
                status_label.set_text("User session missing; re-login required.")
                return

            try:
                tracks = controller.get_top_tracks(current_user, refresh_callback=lambda u: logic.get_decrypted_refresh_token(u, u.id))
            except Exception as exc:
                tracks_container.clear()
                status_label.set_text(str(exc))
                return
            tracks_container.clear()
            with tracks_container:
                ui.label("Your Top Tracks").classes("text-h6 mt-2")
                ui.table(columns=columns, rows=tracks).classes("w-full")

                # --- Media Player UI ---
                with ui.row().classes("items-center gap-4 mt-4"):
                    ui.button(icon='skip_previous', on_click=lambda: controller.skip_back()).props('color=primary')
                    ui.button(icon='play_arrow', on_click=lambda: controller.play_pause()).props('color=primary')
                    ui.button(icon='skip_next', on_click=lambda: controller.skip_forward()).props('color=primary')
                # -----------------------

                # --- Volume Slider with Local Storage and Spotify API ---
                def on_volume_change(e):
                    volume = int(e.value)
                    ui.run_javascript(f"localStorage.setItem('playerVolume', {volume});")
                    controller.set_volume(volume)

                slider = ui.slider(
                    min=0, max=100, value=50, step=1, on_change=on_volume_change
                ).props('label=Volume')

                # Restore slider value from local storage on page load
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
                        time_left = duration - progress
                        duration_label.set_text(f"Time left: {time_left} sec")
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
