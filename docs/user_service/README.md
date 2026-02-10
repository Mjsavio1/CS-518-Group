# User Repository Implementation Summary

## Overview
Complete User Repository implementation with PyMongo integration, custom exception handling, and comprehensive unit tests.

## Implementation Structure

### Source Files

#### `src/class_demo/user_service/repository.py`
**UserRepository class** - Manages all database operations with PyMongo

**Key Features:**
- **CRUD Operations**: create, read, read_by_username, read_by_email, update, delete
- **Utility Methods**: list_all, exists_by_username, exists_by_email, count
- **Index Management**: Automatic creation of unique indexes on username and email
- **MongoDB Integration**: Uses PyMongo Collection for all database operations
- **ID Management**: Converts between MongoDB ObjectId and string representations

**Public Methods:**
| Method | Purpose | Exceptions |
|--------|---------|-----------|
| `create(user)` | Create new user | DuplicateUsernameError, DuplicateEmailError, RepositoryError |
| `read(user_id)` | Get user by ID | UserNotFoundError, RepositoryError |
| `read_by_username(username)` | Get user by username | UserNotFoundError, RepositoryError |
| `read_by_email(email)` | Get user by email | UserNotFoundError, RepositoryError |
| `update(user_id, user)` | Update existing user | UserNotFoundError, DuplicateUsernameError, DuplicateEmailError, RepositoryError |
| `delete(user_id)` | Delete user | UserNotFoundError, RepositoryError |
| `list_all()` | Get all users | RepositoryError |
| `exists_by_username(username)` | Check user exists | None |
| `exists_by_email(email)` | Check email exists | None |
| `count()` | Get total user count | None |

#### `src/class_demo/user_service/repository_exceptions.py`
**Custom exception classes** for error handling

**Exception Hierarchy:**
```
UserServiceException (Base)
├── DuplicateUsernameError - Create operation with duplicate username
├── DuplicateEmailError - Create operation with duplicate email
├── UserNotFoundError - Read/Update/Delete on missing user
├── InvalidUserDataError - Data validation failure
└── RepositoryError - Unexpected database operation errors
```

**Exception Features:**
- Context-aware error messages
- Includes relevant data (username/email/user_id) for debugging
- Inherits from base UserServiceException for unified error handling
- Clear error messages suitable for logging and API responses

---

### Documentation

#### `docs/user_service/exception_handling.md`
Comprehensive guide for exception handling strategy

**Contents:**
- Exception hierarchy and relationships
- Detailed descriptions of each implemented exception
- **7 recommended additional exceptions** with use cases:
  - UnauthorizedUserError (authorization/permissions)
  - InvalidPasswordError (password validity)
  - UserAlreadyExistsError (duplicate user IDs)
  - DatabaseConstraintViolationError (constraint violations)
  - ConcurrentModificationError (race conditions)
  - UserSuspendedError (account status)
  - RepositoryOperationTimeoutError (performance/timeouts)
- Best practices for exception handling
- Testing strategies and recommendations
- Summary table with HTTP status codes

---

### Unit Tests

#### `tests/user_service/test_repository.py`
**Happy path tests** - Successful operations

**Test Coverage:**
- User creation (with/without pre-assigned ID)
- User retrieval (by ID, username, email)
- User updates (all scenarios)
- User deletion
- Listing all users
- Existence checks (by username/email)
- User count
- Repository initialization
- Index creation

**Features:**
- Uses Mock objects for database operations
- Validates return values and types
- Verifies correct database calls

#### `tests/user_service/test_repository_exceptions.py`
**Exception tests** - Error handling and edge cases

**Exception Test Coverage:**
- **Create Operations**: Duplicate username, duplicate email, unexpected errors
- **Read Operations**: User not found (by ID, username, email), unexpected errors
- **Update Operations**: User not found, duplicate username, duplicate email, unexpected errors
- **Delete Operations**: User not found, unexpected errors
- **List Operations**: Unexpected errors
- **Exception Hierarchy**: Validates inheritance and polymorphism
- **Exception Messages**: Verifies clear and contextual error messages

**Features:**
- Tests all exception raising conditions
- Validates exception context (user_id, username, email)
- Verifies exception inheritance relationships
- Tests message formatting and content

---

## Usage Example

### Basic Usage
```python
from pymongo import MongoClient
from src.class_demo.user_service.repository import UserRepository
from src.class_demo.user_service.models import User
from src.class_demo.user_service.repository_exceptions import (
    DuplicateUsernameError,
    UserNotFoundError
)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["myapp"]
users_collection = db["users"]

# Initialize repository
repo = UserRepository(users_collection)

# Create user
try:
    new_user = User(
        email="john@example.com",
        username="johndoe",
        password="hashed_password",
        role="user"
    )
    created = repo.create(new_user)
    print(f"Created user with ID: {created.id}")
except DuplicateUsernameError as e:
    print(f"Username taken: {e}")

# Read user
try:
    user = repo.read_by_username("johndoe")
    print(f"Found user: {user.email}")
except UserNotFoundError as e:
    print(f"User not found: {e}")

# Update user
try:
    user.role = "admin"
    updated = repo.update(user.id, user)
except DuplicateUsernameError:
    print("Cannot change to that username")

# Delete user
try:
    repo.delete(user.id)
except UserNotFoundError:
    print("User already deleted")

# List and count
all_users = repo.list_all()
total = repo.count()
print(f"Total users: {total}")
```

### Exception Handling Pattern
```python
from src.class_demo.user_service.repository_exceptions import UserServiceException

try:
    user = repo.read(user_id)
except UserNotFoundError as e:
    # Specific: Handle missing user - 404
    return error_response(str(e), 404)
except DuplicateUsernameError as e:
    # Specific: Handle duplicate - 409
    return error_response(str(e), 409)
except UserServiceException as e:
    # Generic: Handle any custom service error - 400/500
    return error_response(str(e), 500)
except Exception as e:
    # Fallback: Unexpected error
    log.error(f"Unexpected error: {e}")
    return error_response("Internal server error", 500)
```

---

## Running Tests

### Run all tests
```bash
python -m unittest discover tests/
```

### Run specific test file
```bash
python -m unittest tests.user_service.test_repository
python -m unittest tests.user_service.test_repository_exceptions
```

### Run specific test class
```bash
python -m unittest tests.user_service.test_repository.TestUserRepositoryHappyPath
python -m unittest tests.user_service.test_repository_exceptions.TestUserRepositoryExceptions
```

### Run specific test method
```bash
python -m unittest tests.user_service.test_repository.TestUserRepositoryHappyPath.test_create_user_success
```

### With coverage
```bash
pip install coverage
coverage run -m unittest discover tests/
coverage report
coverage html  # Generate HTML report
```

---

## Dependencies

**Required:**
- `pymongo` - MongoDB driver
- `pydantic` - Data validation
- `email-validator` - Email validation (used in User model)
- `bson` - BSON serialization (included with pymongo)

**Development:**
- `unittest` - Python standard library testing framework

---

## Database Indexes

The repository automatically creates two unique indexes during initialization:

1. **username index** - Ensures no duplicate usernames
2. **email index** - Ensures no duplicate emails

These indexes:
- Are automatically created on first repository instantiation
- Speed up queries by username or email
- Enforce uniqueness at the database level
- Support the duplicate detection in create/update operations

---

## File Locations

```
project_root/
├── src/class_demo/user_service/
│   ├── __init__.py
│   ├── models.py (existing User model)
│   ├── mapper.py (existing data mapping)
│   ├── repository.py (NEW - MongoDB operations)
│   ├── repository_exceptions.py (NEW - Custom exceptions)
│   └── exceptions.py (deprecated - use repository_exceptions.py)
├── tests/user_service/
│   ├── __init__.py
│   ├── test_repository.py (NEW - Happy path tests)
│   ├── test_repository_exceptions.py (NEW - Exception tests)
│   └── test_mapper.py (existing mapper tests)
└── docs/user_service/
    └── exception_handling.md (NEW - Exception documentation)
```

---

## Notes

- **Backward Compatibility**: `exceptions.py` still exists for compatibility but use `repository_exceptions.py` instead
- **MongoDB Ready**: All code assumes PyMongo connection is passed in, no hardcoded database connections
- **Type Hints**: Full type annotations for better IDE support and code clarity
- **Docstrings**: Comprehensive docstrings following Google style guide
- **Error Context**: Exceptions include relevant context (user_id, username, email) for debugging
- **Test Mocking**: All tests use mock objects, no actual database required

---

## Future Enhancements

Per the exception handling documentation, consider implementing:
1. Role-based access control (requires UnauthorizedUserError)
2. Password validation policies (requires InvalidPasswordError)
3. Account status tracking (requires UserSuspendedError)
4. Concurrent modification detection (requires ConcurrentModificationError)
5. Operation timeout handling (requires RepositoryOperationTimeoutError)
