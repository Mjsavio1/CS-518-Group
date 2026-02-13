Please create a User Repository (repository.py).  The Repository is in charge of database operations.
In addition to the UserRepository class, please implement custom exceptions (exceptions.py) to handle these cases:
- on create: duplicate username or email
- on read: user not found
Please suggest other custom exceptions, if necessary, in the documentation (repository_exception_handling.md)
----------------------------------------------------------------------------
Integration testing
Please implement integration tests that connect to a live DB.
here:

tests/class_demo/integration/test_repository_integration.py

The DB URL should be stored here:

src/class_demo/config.py