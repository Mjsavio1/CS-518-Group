from nicegui import ui
import os
import asyncio
import logging
try:
    from version import APP_VERSION
except ImportError:
    APP_VERSION = "dev"

ICON_SRC = f"/static/icon.png?v={APP_VERSION}"

from ..listening_service.listening_service import ListeningService
from ..user_service.models import User
from .interfaces import AppLogic
from .listening.listening_controller import ListeningController
from .listening.listening_gui import render_listening_module, render_spotify_player
from .session import SessionManager
from .users.user_gui import render_user_module


def _apply_theme() -> None:
    ui.colors(
        primary="#22c55e",
        secondary="#16a34a",
        accent="#15803d",
        positive="#22c55e",
        negative="#ef4444",
        warning="#f59e0b",
        info="#4ade80",
    )
    ui.dark_mode().enable()
    ui.add_head_html(
        """
        <style>
            :root {
                color-scheme: dark;
            }

            body,
            .q-layout,
            .q-page-container,
            .q-page {
                background: #000000 !important;
                color: #dcfce7 !important;
            }

            /* Prevent text cursor from appearing on non-editable elements */
            *:not(input):not(textarea):not([contenteditable="true"]) {
                cursor: default;
            }
            button,
            [role="button"],
            .q-btn,
            .q-item,
            a,
            [onclick] {
                cursor: pointer !important;
            }
        </style>
        """
    )


def init_pages(
    user_logic: AppLogic,
    listening_controller: ListeningController | None = None,
):
    listening_controller = listening_controller or ListeningController(ListeningService())

    @ui.page("/login")
    def login_page():
        _apply_theme()
        with ui.card().classes("absolute-center w-80"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.image(ICON_SRC).classes("w-10 h-10")
                ui.label("Nichetify").classes("text-h5 font-bold text-primary")
            ui.label("User Authentication").classes("text-h6")
            user_input = ui.input("Username/Email")
            pass_input = ui.input("Password", password=True)

            def do_login():
                try:
                    username_or_email = (user_input.value or "").strip()
                    password = (pass_input.value or "").strip()
                    user = user_logic.login(username_or_email, password)
                    SessionManager.login(user)
                    ui.navigate.to("/")
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button("Login", on_click=do_login).classes("w-full")
            ui.link("Create account", "/signup").classes("text-primary")

    @ui.page("/signup")
    def signup_page():
        _apply_theme()
        with ui.card().classes("absolute-center w-96"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.image(ICON_SRC).classes("w-10 h-10")
                ui.label("Nichetify").classes("text-h5 font-bold text-primary")
            ui.label("Create Account").classes("text-h6")
            email_input = ui.input("Email")
            username_input = ui.input("Username")
            password_input = ui.input("Password", password=True)
            confirm_input = ui.input("Confirm Password", password=True)

            def do_signup():
                email = (email_input.value or "").strip()
                username = (username_input.value or "").strip()
                password = (password_input.value or "").strip()
                confirm_password = (confirm_input.value or "").strip()

                if not email or not username or not password:
                    ui.notify("Email, username, and password are required.", type="negative")
                    return

                if password != confirm_password:
                    ui.notify("Passwords do not match.", type="negative")
                    return

                try:
                    user_logic.create_user(email=email, username=username, password=password)
                    user = user_logic.login(username, password)
                    SessionManager.login(user)
                    ui.notify("Account created successfully.", type="positive")
                    ui.navigate.to("/")
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button("Create Account", on_click=do_signup).classes("w-full")
            ui.link("Back to login", "/login").classes("text-primary")

    @ui.page("/")
    def dashboard():
        _apply_theme()
        if not SessionManager.is_authenticated():
            return ui.navigate.to("/login")

        current_user = SessionManager.get_current_user()
        if current_user is None:
            return ui.navigate.to("/login")

        _render_dashboard(current_user, user_logic, listening_controller)

    @ui.page("/callback")
    def spotify_callback_page(code: str | None = None, state: str | None = None, error: str | None = None):
        _apply_theme()
        if not SessionManager.is_authenticated():
            ui.notify("Please log in before connecting Spotify.", type="negative")
            return ui.navigate.to("/login")

        current_user = SessionManager.get_current_user()
        if current_user is None or not current_user.id:
            ui.notify("Cannot complete Spotify callback: user session is unavailable.", type="negative")
            return ui.navigate.to("/login")

        with ui.card().classes("absolute-center w-[40rem]"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.image(ICON_SRC).classes("w-10 h-10")
                ui.label("Spotify Connection").classes("text-h6")
            try:
                result = listening_controller.complete_secure_connection_from_params(
                    user_id=current_user.id,
                    code=code,
                    state=state,
                    error=error,
                )

                # If a refresh token was returned, persist it to the user's record securely.
                refresh = result.get("refresh_token")
                spotify_id = result.get("spotify_id")
                expires_at = result.get("expires_at")
                display_name = result.get("display_name")
                if refresh or spotify_id or expires_at or display_name:
                    try:
                        updated = user_logic.update_spotify_tokens(
                            requester=current_user,
                            user_id=current_user.id,
                            spotify_id=spotify_id,
                            refresh_token=refresh,
                            expires_at=expires_at,
                            display_name=display_name,
                        )
                        # refresh session data
                        SessionManager.login(updated)
                        current_user = updated
                    except Exception:
                        # Non-fatal: continue but inform user
                        ui.label("Connected but failed to persist Spotify tokens (check server config)").classes("text-warning")

                ui.label(f"Connected safely as {result.get('display_name', 'Spotify User')}").classes("text-positive")
                ui.button("Return to Dashboard", on_click=lambda: ui.navigate.to("/")).props("color=primary")
            except Exception as exc:
                ui.label(str(exc)).classes("text-negative")
                ui.button("Try Again", on_click=lambda: ui.navigate.to("/")).props("color=negative")


def _render_dashboard(current_user: User, user_logic: AppLogic, listening_controller: ListeningController) -> None:
    with ui.header().classes("items-center gap-4"):
        ui.image(ICON_SRC).classes("w-14 h-14 p-2 rounded-full shadow-sm").style("background: #1d1d1d;").on("click", lambda: ui.navigate.to("/"))
        ui.label(f"Welcome, {current_user.username}")
        with ui.tabs().props("inline-label").classes("text-white") as tabs:
            ui.tab("Users")
            ui.tab("Listening History")
        ui.space()
        ui.badge(APP_VERSION).props("color=grey-7").classes("text-xs font-mono")
        ui.button("Logout", on_click=lambda: [SessionManager.logout(), ui.navigate.to("/login")])

    render_spotify_player(listening_controller, user_logic, current_user)

    # Keep both modules on the same page so switching tabs does not reload.
    with ui.tab_panels(tabs, value="Listening History").classes("w-full"):
        with ui.tab_panel("Users"):
            render_user_module(user_logic, current_user)

        with ui.tab_panel("Listening History"):
            render_listening_module(listening_controller, user_logic, current_user)


    # Start background task to refresh Spotify tokens periodically
    # Runs in the NiceGUI asyncio loop but executes blocking work in a thread.
    refresh_interval = int(os.getenv("SPOTIFY_REFRESH_INTERVAL_SECONDS", "300"))
    logger = logging.getLogger("app_background")

    async def _spotify_refresh_loop():
        while True:
            try:
                # run refresh in a background thread to avoid blocking the event loop
                refreshed = await asyncio.to_thread(user_logic.refresh_all_spotify_tokens)
                if refreshed:
                    logger.info("refreshed %d spotify tokens", refreshed)
            except Exception as e:
                logger.exception("background spotify refresh failed: %s", e)
            await asyncio.sleep(refresh_interval)

    # schedule the loop (non-blocking)
    try:
        asyncio.create_task(_spotify_refresh_loop())
    except Exception:
        # if event loop not running yet, schedule when it starts
        def _defer_start():
            asyncio.create_task(_spotify_refresh_loop())
        ui.timer(0.1, _defer_start, single_shot=True)
