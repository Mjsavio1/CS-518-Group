# Individual 9.2

## E2E Test Description
### tests/e2e/test_api_e2e.py
- Sends real HTTP requests to a running API service.
- Starts uvicorn and waits until the API is available.
- Uses a separate MongoDB database for e2e test runs.
- Checks the complete user workflow:
  - create admin account
  - login as admin
  - create regular user
  - login as regular user
  - confirm user can read own profile
  - confirm regular user cannot list all users
  - confirm admin can list all users
  - update user
  - delete user
  - confirm deleted user returns not found

## Integration Test Description
### tests/user_api/test_api_int.py
- API integration tests using FastAPI TestClient with a live MongoDB instance.
- Covers auth, role checks, CRUD flows, and not found cases.

### tests/user_app/test_app_logic_int.py
- App logic integration tests against the real service and repository layers.
- Covers admin seeding, successful and failed login paths, and role-based list access.

### tests/user_app/test_app_interface.py
- UI integration tests using NiceGUI browser testing.
- Verifies seeded admin login and access to dashboard/admin panel.
- Verifies invalid login shows an error and blocks admin panel access.

### tests/user_service/test_service_int.py
- Service-layer integration tests with live MongoDB.
- Covers create/authenticate, failed authentication, authorization checks, and get-update-delete flow.

### tests/test_repository_integration.py
- Repository integration tests with live MongoDB.
- Covers create, duplicate prevention, lookup by id/email, update, delete, and list users.
