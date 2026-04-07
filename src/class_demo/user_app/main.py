from nicegui import ui

from ..listening_service.listening_service import ListeningService
from ..user_service.models import User
from .interfaces import AppLogic
from .listening.listening_controller import ListeningController
from .listening.listening_gui import render_listening_module
from .session import SessionManager
from .users.user_gui import render_user_module


def init_pages(
    user_logic: AppLogic,
    listening_controller: ListeningController | None = None,
):
    listening_controller = listening_controller or ListeningController(ListeningService())

    @ui.page("/login")
    def login_page():
        with ui.card().classes("absolute-center w-80"):
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

    @ui.page("/")
    def dashboard():
        if not SessionManager.is_authenticated():
            return ui.navigate.to("/login")

        current_user = SessionManager.get_current_user()
        if current_user is None:
            return ui.navigate.to("/login")

        _render_dashboard(current_user, user_logic, listening_controller)


def _render_dashboard(current_user: User, user_logic: AppLogic, listening_controller: ListeningController) -> None:
    with ui.header():
        ui.label(f"Welcome, {current_user.username}")
        ui.space()
        ui.button("Logout", on_click=lambda: [SessionManager.logout(), ui.navigate.to("/login")])

    with ui.tabs() as tabs:
        ui.tab("Users")
        ui.tab("Listening History")

    # Keep both modules on the same page so switching tabs does not reload.
    with ui.tab_panels(tabs, value="Users").classes("w-full"):
        with ui.tab_panel("Users"):
            render_user_module(user_logic, current_user)

        with ui.tab_panel("Listening History"):
            render_listening_module(listening_controller)
