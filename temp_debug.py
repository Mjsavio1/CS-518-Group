from fastapi.testclient import TestClient
from src.run_api import app
from unittest.mock import MagicMock
from src.class_demo.user_service.models import User, UserRole

client = TestClient(app)
import src.class_demo.user_api.api as api_mod
svc = MagicMock()
api_mod.get_service = lambda: svc
user = User(id="u1", username="u1", email="u1@x.com", password="pw", role=UserRole.user)
svc.authenticate.return_value = user
r = client.post("/login", json={"username": "u1", "password": "pw"})
print(r.status_code, r.text)
