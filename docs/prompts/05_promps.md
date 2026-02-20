# User Service

Please implement User Service.  This is a local service package, not an API.

## functionality

* handles business logic, e.g.:
    - password hashing
    - authentication

* role-based authorization
    - most Service methods should have a parameter "requester"

* logging
    - set up a log handler so that log files go to a top-level "logs" directory (adjacent to "src")

* Exception handling
    * The User Service handles User Repository exceptions and raises custom User Service exceptions.
    * some examples of exceptions include:
        - failed authentication
        - unauthorized request

## Documentation 

- exception handling, including suggestions (service_exception_handling.md)
- functionality and suggestions for other possible functionality (service_functionality.md)

# Context and output

## Context

The User Service uses:

* src/class_demo/user_service/*

## Output

Please generate the following:

* docs/user_service/
    - service_exception_handling.md
    - service_functionality.md
* src/class_demo/user_service/
    - service.py
    - service_exceptions.py
* tests/user_service/
    - test_service_int.py     # integration tests connect to live DB
    - test_service_unit.py    # unit cases

Please implement tests using unittest.
Please add __init__.py files as needed for unittest discovery.