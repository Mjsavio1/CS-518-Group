from typing import Optional
from nicegui import app
from ..user_service.models import User

class SessionManager:
    @staticmethod
    def login(user: User):
        app.storage.user['authenticated'] = True
        app.storage.user['user_data'] = user.dict()

    @staticmethod
    def logout():
        app.storage.user.clear()

    @staticmethod
    def get_current_user() -> Optional[User]:
        data = app.storage.user.get('user_data')
        return User(**data) if data else None

    @staticmethod
    def is_authenticated() -> bool:
        return app.storage.user.get('authenticated', False)