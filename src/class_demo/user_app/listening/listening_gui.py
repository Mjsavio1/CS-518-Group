from nicegui import ui

from .listening_controller import ListeningController


def render_listening_module(controller: ListeningController) -> None:
    """Render the Listening History panel inside a tab panel."""
    with ui.column().classes("w-full gap-4"):
        ui.label("Listening History").classes("text-h5")
        ui.label("Discover insights from your Spotify listening activity.").classes("text-subtitle1 text-grey")

        status_label = ui.label("").classes("text-body1 text-primary")
        tracks_table: ui.table | None = None

        columns = [
            {"name": "title", "label": "Track", "field": "title", "align": "left"},
            {"name": "artist", "label": "Artist", "field": "artist", "align": "left"},
            {"name": "plays", "label": "Plays", "field": "plays", "align": "right"},
        ]
        tracks_container = ui.column().classes("w-full")

        def on_connect():
            status_label.set_text(controller.get_greeting())
            tracks = controller.get_top_tracks()
            tracks_container.clear()
            with tracks_container:
                ui.label("Your Top Tracks").classes("text-h6 mt-2")
                ui.table(columns=columns, rows=tracks).classes("w-full")

        ui.button("Connect to Spotify", on_click=on_connect).props("icon=music_note color=green")
