You are coding inside my existing repo for Lab 06 (GUI interface for User authentication + management). Build a NiceGUI monolith app that uses my existing user_service package directly (DO NOT import or call repository classes anywhere in the app). Authorization MUST be enforced by the user_service.

LAB REQUIREMENTS (must satisfy):
- Authentication: login + logout
- RBAC user management:
  - user: view/update own profile
  - admin: list users + create new user
- Layered architecture / separation of concerns: UI layer should call an app “logic layer” that calls user_service
- Admin user: seed from variables stored in root .env
- Secrets: .env must be in .gitignore; config.py loads env vars
- Documentation: provide docs on functionality/usage + exception handling
- Testing (unittest):
  - unittest for logic layer
  - unittest + user_simulation for UI with a test client
- Add __init__.py as needed for unittest discovery
- If needed, reinstall package in editable mode so module class_demo.user_app is recognized

CONTEXT YOU CAN ASSUME EXISTS:
- Existing package: /src/class_demo/user_service/* (already implemented)
- Existing /src/class_demo/config.py loads .env via dotenv (if not, update it safely)
- I’m using Python, unittest, and NiceGUI

OUTPUTS YOU MUST CREATE/UPDATE EXACTLY:
1) docs:
   /docs/user_app_docs/
     - app_functionality.md
     - app_exception_handling.md

2) root support files:
   - /.env              (create template/example values if you can’t fill real secrets)
   - /.gitignore         (ensure .env is ignored)
   - /requirements.txt   (ensure all dependencies are included: nicegui, python-dotenv, pymongo if used by user_service, etc.)

3) source code:
   - /src/run_app.py     (entry point that launches NiceGUI)
   - /src/class_demo/user_app/   (new module with UI + logic layer)
     include __init__.py and any submodules needed

4) tests:
   - /tests/user_app/
     - test_app_logic_int.py     (integration tests: logic layer -> user_service -> DB; no mocking)
     - test_app_interface.py     (UI tests using unittest + user_simulation + a test client)

ARCHITECTURE REQUIREMENTS (be strict):
- UI must never talk to repository directly.
- Create a small “logic/service adapter” layer inside class_demo.user_app (e.g., app_logic.py) that wraps calls to user_service.
- Keep UI code (pages/components) separate from logic functions.
- Use clear exception boundaries: catch user_service exceptions in the logic layer and re-raise app-specific exceptions (or translate them) so the UI can show friendly messages.
- Store session/auth state safely (in-memory session per client). Do NOT store plaintext passwords beyond login input.

FUNCTIONALITY DETAILS TO IMPLEMENT:
A) Login page:
- Email/username + password inputs
- Call user_service.authenticate(...) or equivalent (use the actual interface in my package)
- On success store “current user” + role in session state
- Redirect to dashboard

B) Logout:
- Clear session state and return to login page

C) User dashboard (for any authenticated user):
- View self details (email/name/role/whatever user_service exposes)
- Update self (allowed fields only; call user_service with requester=current user)

D) Admin panel (only for admin role):
- List users (table)
- Create user form (email, name, password, role)
- All admin actions must pass requester=admin to user_service methods

E) Seeding admin:
- Read ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME from .env (and anything else needed)
- On app startup (or first request), ensure admin exists; if not, create via user_service (or repo init path exposed through user_service only)
- Do not print secrets to logs

TESTING REQUIREMENTS:
1) test_app_logic_int.py
- Uses real DB config from .env (or a test DB specified by env vars)
- Tests: admin seed exists; login works; user can update self; non-admin cannot list/create users; admin can list/create users
- No mocking: hit DB through user_service

2) test_app_interface.py
- Use unittest + user_simulation to drive UI:
  - load app
  - attempt login (valid/invalid)
  - confirm logout returns to login
  - confirm admin sees admin panel and user does not
- Use a test client approach recommended by NiceGUI/user_simulation patterns

DELIVERABLE QUALITY BAR:
- Provide complete code files, not pseudocode.
- Include comments where needed.
- Ensure imports and module paths are correct for /src layout.
- Ensure unittest discovery works (add __init__.py files).
- Update requirements.txt with pinned-ish minimum versions if necessary.

Before writing code:
1) Inspect the existing user_service public API (methods, models, exceptions).
2) Adapt your logic layer to call those exact methods (do NOT invent method names without checking).
3) If the existing API lacks a needed function, implement the missing functionality INSIDE user_service (only if permitted) OR implement the feature via existing service methods—but still never touch repository from the app.

Now generate:
- The full folder/file tree you will create/update
- Then the full contents of each file to paste into my repo
- Then short run instructions and how to run tests