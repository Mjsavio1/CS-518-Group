from nicegui import ui

from ...user_service.models import User, UserRole
from ..interfaces import AppLogic


def render_user_module(logic: AppLogic, current_user: User) -> None:
    with ui.tabs() as user_tabs:
        ui.tab("Profile")
        if current_user.role == UserRole.admin:
            ui.tab("Admin Panel")

    with ui.tab_panels(user_tabs, value="Profile").classes("w-full"):
        with ui.tab_panel("Profile"):
            ui.label("My Details").classes("text-h5")
            email_field = ui.input("Email", value=current_user.email)
            pw_field = ui.input("New Password", password=True)

            def update():
                try:
                    logic.update_profile(current_user, current_user.id, email_field.value, pw_field.value)
                    ui.notify("Profile updated!")
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button("Update", on_click=update)

        if current_user.role == UserRole.admin:
            with ui.tab_panel("Admin Panel"):
                ui.label("All Registered Users").classes("text-h5")
                try:
                    users = logic.list_all_users(current_user)
                    if not users:
                        ui.label("No registered users found.").classes("text-grey")
                    else:
                        columns = [
                            {"name": "username", "label": "Username", "field": "username"},
                            {"name": "email", "label": "Email", "field": "email"},
                            {"name": "role", "label": "Role", "field": "role"},
                        ]
                        ui.table(columns=columns, rows=[u.dict() for u in users])
                except Exception as e:
                    ui.label("Failed to load users. Please try again.").classes("text-negative")