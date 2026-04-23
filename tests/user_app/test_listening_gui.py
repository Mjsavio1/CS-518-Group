from unittest.mock import Mock

from class_demo.user_app.interfaces import AppLogic
from class_demo.user_app.listening import listening_gui
from class_demo.user_service.models import User


class _FakeElement:
    def __init__(self, value=None):
        self.value = value
        self.text = None

    def classes(self, _value):
        return self

    def props(self, _value):
        return self

    def set_text(self, text):
        self.text = text
        return self

    def set_value(self, value):
        self.value = value
        return self

    def clear(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeNavigate:
    def __init__(self):
        self.calls = []

    def to(self, url):
        self.calls.append(url)


class _FakeUI:
    def __init__(self):
        self.buttons = {}
        self.notifications = []
        self.navigate = _FakeNavigate()

    def column(self):
        return _FakeElement()

    def row(self):
        return _FakeElement()

    def label(self, text=""):
        element = _FakeElement()
        element.text = text
        return element

    def input(self, *_args, value=""):
        return _FakeElement(value=value)

    def textarea(self, *_args, value=""):
        return _FakeElement(value=value)

    def select(self, *, options, value, label):
        return _FakeElement(value=value)

    def switch(self, _label, value=False):
        return _FakeElement(value=value)

    def button(self, label, on_click):
        self.buttons[label] = on_click
        return _FakeElement()

    def separator(self):
        return _FakeElement()

    def table(self, **_kwargs):
        return _FakeElement()

    def notify(self, message, type=None):
        self.notifications.append((message, type))


def test_connect_spotify_button_generates_and_opens_link(monkeypatch):
    fake_ui = _FakeUI()
    monkeypatch.setattr(listening_gui, "ui", fake_ui)

    controller = Mock()
    controller.get_greeting.return_value = "Spotify integration is ready."
    controller.get_safety_notes.return_value = "Use secure connect to authorize your account."
    controller.start_secure_connection.return_value = "https://accounts.spotify.com/authorize?state=test"

    logic = Mock(spec=AppLogic)
    current_user = User(
        id="user-1",
        email="user@example.com",
        username="user",
        password="password123",
    )

    listening_gui.render_listening_module(controller, logic, current_user)

    fake_ui.buttons["Connect Spotify"]()

    controller.start_secure_connection.assert_called_once_with("user-1")
    assert fake_ui.navigate.calls == ["https://accounts.spotify.com/authorize?state=test"]
    assert ("Opening Spotify secure login.", "positive") in fake_ui.notifications