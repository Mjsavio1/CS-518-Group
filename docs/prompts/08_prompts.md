# API
Please implement an API for the user_service.

Authentication:
 - Authorization is handled in the user_service module.  API routes should implement basic authentication, so that the API user must login and pass a token in the header with subsequent requests.
 - Authentication and Authorization exceptions should be handled appropriately.

# context and tools
Uses the user_service package:

 - src/class_demo/user_service/*

Tools:

 - FastAPI


# Output
Source:

 - /src/
    run_api.py  # entry point for API

 - /src/class_demo/user_api/     # source code for the API

Tests:

 - tests/user_api/
    test_api_unit.py      # unit tests - mock the User service
    test_api_int.py       # integration tests - live DB


 - tests/e2e/
    test_api_e2e.py       # e2e tests - live API

Note:
    e2e tests go in a separate folder because they are slow.