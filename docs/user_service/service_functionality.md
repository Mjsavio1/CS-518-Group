# User Service Functionality

The service package implements business logic around the user domain.  It
exposes a clean interface that encapsulates password handling,
authentication, authorization, logging, and error translation.  This
layer is deliberately kept independent of any transport (HTTP, CLI, etc.)
and is suitable for reuse in multiple contexts.

## Core Features

* **Password hashing** – plaintext passwords provided during creation or
  update are hashed using a salted SHA‑256 scheme.  Hashes are stored in the
  database and validated on login.

* **Authentication** – credentials (username or email combined with
  password) are checked and the corresponding `User` returned on success.
  A generic `FailedAuthenticationError` is raised for any mismatch.

* **Role–based authorization** – each method accepts a ``requester``
  argument representing the actor.  Permissions are enforced according to
  roles defined in `UserRole`:
  * `admin` may perform any operation on any user.
  * regular users may only view or modify their own record.
  * non‑authenticated (`None`) callers may self‑register only.

* **Business methods** – service mirrors typical CRUD operations with
  richer semantics:
  * `create_user(requester, user_info)`
  * `authenticate(username_or_email, password)`
  * `get_user(requester, user_id)`
  * `update_user(requester, user_id, updates)`
  * `delete_user(requester, user_id)`
  * `list_users(requester)` – admin only

* **Repository translation** – all `repository_exceptions` are caught and
  wrapped in service exceptions, keeping persistence details hidden from
  callers.

* **Logging** – a file handler writes detailed debug and error messages to
  `logs/user_service.log` (folder adjacent to `src`).  Each method logs
  entry and significant events.

## Authorization Rules Summary

| Operation     | Allowed for Admin | Allowed for Self | Allowed for Others |
|---------------|-------------------|------------------|--------------------|
| create_user   | ✅                | ✅ (self)        | ❌                |
| authenticate  | –                 | –                | –                 |
| get_user      | ✅                | ✅               | ❌                |
| update_user   | ✅                | ✅               | ❌                |
| delete_user   | ✅                | ✅               | ❌                |
| list_users    | ✅                | ❌               | ❌                |

## Logging

A persistent `logging.FileHandler` is configured when the module is
imported.  It ensures:

* log files are created in a top‑level `logs` directory (created
  automatically).
* messages include timestamps and severity levels.
* duplicate handlers are avoided across reloads.

Services should log at **DEBUG** level for normal operations and escalate
unexpected conditions to **ERROR**.

## Exception Handling

Refer to `service_exception_handling.md` for the full strategy.  Key points
here are:

* service methods raise service-layer exceptions only
* errors from the repository never escape directly
* authentication/authorization failures are raised before repository calls
  when possible

## Suggested Future Enhancements

* **Password policies** – enforce minimum length, character classes,
  disallow reuse, integrate with breach databases; raise
  `InvalidPasswordError`.

* **Account lifecycle** – support activation, suspension, deletion with
  corresponding `UserSuspendedError` and status checks.

* **Audit logging** – record who performed each operation with timestamps
  (may be separate from debug log).

* **Multi-factor authentication** – extend `authenticate` to validate OTPs
  or security questions.

* **Password reset flows** – generate tokens, send emails, and validate
  them; could be part of service responsibility or delegated to a
  separate component.

* **Rate limiting/brute‑force protection** – track failed authentication
  attempts and temporarily block addresses or accounts.

* **Batch operations** – bulk create/update/delete users with partial
  success reporting.

* **Caching** – add an in‑memory cache for frequent lookups to reduce load
  on the repository.

* **Event publishing** – emit domain events (e.g. `user.created`) for
  downstream systems.

## Usage Examples

Simple usage is illustrated below:

```python
from pymongo import MongoClient
from src.class_demo.user_service.repository import UserRepository
from src.class_demo.user_service.service import UserService

client = MongoClient("mongodb://localhost:27017")
db = client["myapp"]
service = UserService(UserRepository(db["users"]))

# create self user
user = service.create_user(None, {"username": "alice", "email": "a@a.com", "password": "secret"})

# authenticate
user = service.authenticate("alice", "secret")

# update profile
service.update_user(user, user.id, {"password": "newpass"})

# admin lists users
admin = service.authenticate("admin", "...")
users = service.list_users(admin)
```

Wrap calls in appropriate try/except blocks as shown in
`service_exception_handling.md`.
