from nicegui import ui
from .session import SessionManager
from .app_logic import AppLogic
from ..user_service.models import UserRole

def init_pages(logic: AppLogic):
    
    @ui.page('/login')
    def login_page():
        with ui.card().classes('absolute-center w-80'):
            ui.label('User Authentication').classes('text-h6')
            user_input = ui.input('Username/Email')
            pass_input = ui.input('Password', password=True)
            
            def do_login():
                try:
                    user = logic.login(user_input.value, pass_input.value)
                    SessionManager.login(user)
                    ui.navigate.to('/')
                except Exception as e:
                    ui.notify(str(e), type='negative')
            
            ui.button('Login', on_click=do_login).classes('w-full')

    @ui.page('/')
    def dashboard():
        if not SessionManager.is_authenticated():
            return ui.navigate.to('/login')
        
        current_user = SessionManager.get_current_user()
        
        with ui.header():
            ui.label(f'Welcome, {current_user.username}')
            ui.space()
            ui.button('Logout', on_click=lambda: [SessionManager.logout(), ui.navigate.to('/login')])

        with ui.tabs() as tabs:
            ui.tab('Profile')
            if current_user.role == UserRole.admin:
                ui.tab('Admin Panel')

        with ui.tab_panels(tabs, value='Profile').classes('w-full'):
            with ui.tab_panel('Profile'):
                ui.label('My Details').classes('text-h5')
                email_field = ui.input('Email', value=current_user.email)
                pw_field = ui.input('New Password', password=True)
                
                def update():
                    try:
                        logic.update_profile(current_user, current_user.id, email_field.value, pw_field.value)
                        ui.notify('Profile updated!')
                    except Exception as e:
                        ui.notify(str(e), type='negative')
                ui.button('Update', on_click=update)

            if current_user.role == UserRole.admin:
                with ui.tab_panel('Admin Panel'):
                    ui.label('All Registered Users').classes('text-h5')
                    users = logic.list_all_users(current_user)
                    columns = [
                        {'name': 'username', 'label': 'Username', 'field': 'username'},
                        {'name': 'email', 'label': 'Email', 'field': 'email'},
                        {'name': 'role', 'label': 'Role', 'field': 'role'},
                    ]
                    ui.table(columns=columns, rows=[u.dict() for u in users])