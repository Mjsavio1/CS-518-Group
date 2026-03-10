from fastapi.testclient import TestClient
from src.run_api import app
from src.class_demo.user_service.models import User, UserRole
from unittest.mock import MagicMock

import class_demo.user_api.api as api_real
import src.class_demo.user_api.api as api_alt

print('real module', api_real)
print('alt module', api_alt)
print('same module object?', api_real is api_alt)
print('real.get_service', api_real.get_service, api_real.get_service.__module__)
print('alt.get_service', api_alt.get_service, api_alt.get_service.__module__)

print('initial overrides', app.dependency_overrides)
svc = MagicMock()
# use alt path as before
app.dependency_overrides[api_alt.get_service] = lambda: svc
print('after set overrides', app.dependency_overrides)

client = TestClient(app)
print('client created, overrides', app.dependency_overrides)

# call login
user = User(id='u1', username='u1', email='u1@x.com', password='pw', role=UserRole.user)
svc.authenticate.return_value = user
r = client.post('/login', json={'username':'u1','password':'pw'})
print('login status', r.status_code, r.text)
