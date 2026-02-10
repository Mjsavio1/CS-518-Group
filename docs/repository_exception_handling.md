# User Repository Exception Handling Strategy

## Overview
The User Repository implements a comprehensive exception handling strategy through custom exception classes. This document outlines the implemented exceptions, exception hierarchy, and recommended practices.

## Exception Hierarchy

```
UserServiceException (Base)
├── DuplicateUsernameError
├── DuplicateEmailError
├── UserNotFoundError
├── InvalidUserDataError
└── RepositoryError
```

## Implemented Exceptions

### 1. UserServiceException
**Base exception** for all User Service operations.
- Used as the parent class for all custom exceptions
- Allows catching all user service errors with a single except clause
- Enables clear error categorization and handling

### 2. DuplicateUsernameError
**Raised on CREATE operation** when username already exists.
- Contains the duplicate username for context
- Helps distinguish between username and email duplicates
- HTTP Status: 409 Conflict

### 3. DuplicateEmailError
**Raised on CREATE operation** when email already exists.
- Contains the duplicate email for context
- Helps distinguish between username and email duplicates
- HTTP Status: 409 Conflict

### 4. UserNotFoundError
**Raised on READ, UPDATE, DELETE operations** when user doesn't exist.
- Can be initialized with user_id, username, or email for context
- Provides flexibility for different lookup methods
- HTTP Status: 404 Not Found

### 5. InvalidUserDataError
**Raised when user data validation fails.**
- Caught from Pydantic validation errors
- Provides detailed validation error messages
- HTTP Status: 400 Bad Request

### 6. RepositoryError
**Raised for unexpected database/repository operation failures.**
- Generic container for unexpected errors
- Wraps low-level database exceptions
- Prevents database implementation details from leaking to consumers
- HTTP Status: 500 Internal Server Error

## Recommended Additional Exceptions

### 1. UnauthorizedUserError
**Raised when user lacks permissions for an operation.**
```python
class UnauthorizedUserError(UserServiceException):
    """Raised when user lacks required permissions."""
    def __init__(self, user_id: str, action: str):
        self.user_id = user_id
        self.action = action
        super().__init__(f"User '{user_id}' not authorized to {action}")
```

**Use Cases:**
- Non-admin trying to delete other users
- User attempting to update someone else's profile
- Role-based access control (RBAC) violations

**HTTP Status:** 403 Forbidden

---

### 2. InvalidPasswordError
**Raised when password validation fails.**
```python
class InvalidPasswordError(UserServiceException):
    """Raised when password does not meet requirements."""
    def __init__(self, message: str):
        super().__init__(f"Password requirement not met: {message}")
```

**Use Cases:**
- Password too short
- Password lacks required complexity
- Password is compromised/in breach database
- Password matches username

**HTTP Status:** 400 Bad Request
**Implementation Note:** Would require password validation policies

---

### 3. UserAlreadyExistsError
**Raised when attempting to create a user entity that already exists (different from duplicate username/email).**
```python
class UserAlreadyExistsError(UserServiceException):
    """Raised when user already exists with same identity."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User with ID '{user_id}' already exists")
```

**Use Cases:**
- User creation with explicit ID that already exists
- Bulk user import with duplicates
- Account restoration/recovery scenarios

**HTTP Status:** 409 Conflict

---

### 4. DatabaseConstraintViolationError
**Raised when database constraint violations occur (beyond uniqueness).**
```python
class DatabaseConstraintViolationError(RepositoryError):
    """Raised when database constraint is violated."""
    def __init__(self, constraint: str, message: str):
        self.constraint = constraint
        super().__init__(f"Constraint violation ({constraint}): {message}")
```

**Use Cases:**
- Foreign key violations in related tables
- Check constraint violations
- Type constraint violations
- Future: email domain whitelist constraints

**HTTP Status:** 400 Bad Request

---

### 5. ConcurrentModificationError
**Raised when concurrent modification conflicts occur.**
```python
class ConcurrentModificationError(RepositoryError):
    """Raised when concurrent modification is detected."""
    def __init__(self, user_id: str, field: str):
        self.user_id = user_id
        self.field = field
        super().__init__(
            f"User '{user_id}' was modified by another request. "
            f"Field '{field}' changed. Please refresh and retry."
        )
```

**Use Cases:**
- Optimistic locking conflicts
- Update conflicts when field was already modified
- Race condition scenarios
- Requires: versioning/timestamp tracking

**HTTP Status:** 409 Conflict

---

### 6. UserSuspendedError
**Raised when operation attempted on suspended/inactive user.**
```python
class UserSuspendedError(UserServiceException):
    """Raised when operation attempted on suspended user."""
    def __init__(self, user_id: str, reason: str = None):
        self.user_id = user_id
        self.reason = reason
        msg = f"User '{user_id}' is suspended"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
```

**Use Cases:**
- User account suspension for violations
- User account deactivation
- Blocked users attempting operations
- Requires: status field in User model

**HTTP Status:** 403 Forbidden

---

### 7. RepositoryOperationTimeoutError
**Raised when database operation exceeds timeout threshold.**
```python
class RepositoryOperationTimeoutError(RepositoryError):
    """Raised when repository operation times out."""
    def __init__(self, operation: str, duration_ms: float):
        self.operation = operation
        self.duration_ms = duration_ms
        super().__init__(
            f"Operation '{operation}' timed out after {duration_ms}ms"
        )
```

**Use Cases:**
- Slow database operations
- Network timeouts
- Connection pool exhaustion
- Monitoring and alerting

**HTTP Status:** 504 Gateway Timeout

---

## Exception Handling Best Practices

### 1. **Specific Exception Handling**
```python
try:
    user_repo.create(user)
except DuplicateUsernameError as e:
    # Handle duplicate username
    log.warning(f"Signup rejected: {e}")
    return error_response("Username already taken", 409)
except DuplicateEmailError as e:
    # Handle duplicate email
    log.warning(f"Signup rejected: {e}")
    return error_response("Email already registered", 409)
except InvalidUserDataError as e:
    # Handle validation errors
    log.warning(f"Invalid data: {e}")
    return error_response(str(e), 400)
```

### 2. **Generic Exception Handling**
```python
try:
    user = user_repo.read(user_id)
except UserNotFoundError:
    return not_found_response("User not found")
except UserServiceException as e:
    # Catch all custom service exceptions
    log.error(f"Service error: {e}")
    return error_response("Server error", 500)
```

### 3. **Logging and Monitoring**
- Log all exceptions with appropriate severity levels
- Include context (user_id, username, email) in logs
- Track exception frequencies for alerting
- Use exception types for monitoring dashboards

### 4. **User-Facing Messages**
- Never expose internal database errors to users
- Use custom exceptions to provide safe error messages
- Maps technical errors to business-friendly messages
- Prevents information leakage

## Migration Path for Additional Exceptions

To add new exceptions in the future:

1. **Extend the hierarchy** - Add new class inheriting from `UserServiceException` or appropriate base
2. **Update repository** - Add raise statements where condition occurs
3. **Update tests** - Add test cases for new exception scenarios
4. **Update API handlers** - Add handler for new exception type
5. **Document behavior** - Update this document with new exception details

## Testing Exception Scenarios

Recommended test cases for each exception:

- **Create duplicates** - Test username and email duplicates separately
- **Read missing** - Test by ID, username, email
- **Update missing** - Attempt update on non-existent user
- **Delete missing** - Attempt delete on non-existent user
- **Invalid data** - Test with malformed user objects
- **Concurrent operations** - Test parallel create/update scenarios

## Summary Table

| Exception | When Raised | HTTP Status | Recoverable |
|-----------|------------|------------|------------|
| DuplicateUsernameError | CREATE: username exists | 409 | Yes |
| DuplicateEmailError | CREATE: email exists | 409 | Yes |
| UserNotFoundError | READ/UPDATE/DELETE: user missing | 404 | Yes |
| InvalidUserDataError | Validation failure | 400 | Yes |
| RepositoryError | DB operation fails | 500 | Partial |
| UnauthorizedUserError* | Insufficient permissions | 403 | No |
| InvalidPasswordError* | Password invalid | 400 | Yes |
| UserAlreadyExistsError* | User ID exists | 409 | Yes |
| DatabaseConstraintViolationError* | Constraint violation | 400 | No |
| ConcurrentModificationError* | Concurrent update | 409 | Yes |
| UserSuspendedError* | User suspended | 403 | No |
| RepositoryOperationTimeoutError* | Timeout | 504 | Maybe |

*Recommended for implementation
