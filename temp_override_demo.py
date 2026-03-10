from fastapi.testclient import TestClient
from src.run_api import app
from src.class_demo.user_service.models import User, UserRole
from unittest.mock import MagicMock

print('initial overrides', app.dependency_overrides)
svc = MagicMock()
import src.class_demo.user_api.api as api
app.dependency_overrides[api.get_service] = lambda: svc
print('after set overrides', app.dependency_overrides)

client = TestClient(app)
print('client created, overrides still', app.dependency_overrides)

# try a login
user = User(id='u1', username='u1', email='u1@x.com', password='pw', role=UserRole.user)
svc.authenticate.return_value = user
r = client.post('/login', json={'username':'u1','password':'pw'})
print('login status', r.status_code, r.text)

r2 = client.post('/users', json={'username':'u2','email':'u2@x.com','password':'pw'})
print('create status', r2.status_code, r2.text)
