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

        ui.button("Connect to Spotify", on_click=on_connect).props("icon=music_note color=green")
