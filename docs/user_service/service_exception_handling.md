# User Service Exception Handling

This document describes the exception strategy used by the **service layer**
of the user package.  The service sits on top of the repository and adds
business rules such as authentication and authorization; accordingly it
wraps a subset of repository errors while introducing its own higher‑level
failures.

## Exception Hierarchy

```
UserServiceError (base)
├── RepositoryError              # wraps repository layer issues
├── DuplicateUsernameError
├── DuplicateEmailError
├── UserNotFoundError
├── InvalidUserDataError         # validation or missing fields
├── AuthenticationError
│   └── FailedAuthenticationError
└── AuthorizationError
    └── UnauthorizedRequestError
```

### Mapping from repository
The service layer intentionally defines its own versions of the repository
exceptions (duplicate username/email, not‑found, etc.) so that callers
need not import internals of the persistence layer.  All repository errors
are caught and translated; for example:

```python
try:
    self._repo.create(user)
except repo_exc.DuplicateUsernameError as e:
    raise svc_exc.DuplicateUsernameError(e.username) from e
```

This permits the service interface to remain stable if the repository is
later refactored or replaced.

## Service‑specific Exceptions

### Authentication errors
* **FailedAuthenticationError** – raised when provided credentials do not
  match any known user.  The message is deliberately generic so as not to
  reveal whether the username/email exists.

### Authorization errors
* **UnauthorizedRequestError** – raised when the ``requester`` user does not
  have permission to perform the requested action.  Actions are simple
  strings such as `"update user"` or `"list users"`.

### Invalid data
* **InvalidUserDataError** – used by the service to indicate that a call
  failed basic business validation (e.g. missing password during creation).
  Pydantic validation errors from model construction are wrapped in this
  class.

## Recommended Handling Patterns

Service exceptions are intended to be caught by the layer above the service
(e.g. controllers or command‑line scripts).  Handlers should distinguish
between classes where appropriate and fall back on the base type.

```python
try:
    service.create_user(requester, payload)
except svc_exc.DuplicateUsernameError:
    return response(409, "username already taken")
except svc_exc.FailedAuthenticationError:
    return response(401, "invalid credentials")
except svc_exc.AuthorizationError as e:
    return response(403, str(e))
except svc_exc.UserServiceError as e:
    # generic service error (includes RepositoryError)
    log.error(e)
    return response(500, "internal service error")
```

As with the repository, the service encourages logging of the original
exception (`from e`) so that traceback and context are preserved for
debugging while keeping the public message safe.

## Additional Scenarios

While the current implementation covers the common cases, the service
layer is a convenient place to introduce other domain errors such as:

* **InvalidPasswordError** – password does not meet complexity policies.
* **UserSuspendedError** – account has been deactivated or locked.
* **ConcurrentModificationError** – optimistic‑locking conflict detected.
* **RepositoryOperationTimeoutError** – database call took too long.

Each new error should be added to the hierarchy here, translated from any
lower layers, and documented with usage examples.

## Testing the Exception Behavior

Unit tests for the service exercise the translation logic by mocking the
repository and forcing it to raise each repository exception in turn.  It
is also useful to confirm that authorization failures occur before any
repository call is made (mock should not be touched).

Integration tests exercise the real repository and will surface any
untranslated errors as failures; such tests currently check that authentication
and basic CRUD operations raise the expected service exceptions when
misused.

A concise table summarizing statuses is helpful for API teams:

| Exception                   | When Raised                                   | Suggested HTTP Status |
|----------------------------|-----------------------------------------------|-----------------------|
| DuplicateUsernameError     | create with taken username                    | 409                   |
| DuplicateEmailError        | create with taken email                       | 409                   |
| UserNotFoundError          | lookup/update/delete non-existent user        | 404                   |
| InvalidUserDataError       | missing/invalid fields                        | 400                   |
| FailedAuthenticationError  | bad credentials                               | 401                   |
| UnauthorizedRequestError   | requester lacks permission                    | 403                   |
| RepositoryError            | unexpected backend/database error             | 500                   |


---

*Document maintained by the team.  Refer to `docs/user_service/exception_handling.md` for the repository‑level strategy.*
