## Test Case Summary

#### test_mapper.py

This test verifies the mapper layer that will convert between plain dictionaries, DB documents and the User model

Test_dict_to_model_valid: Calls mapper.dict_to_model with email,username and password role and will verify that the returned user has expected email,username and role

Test_model_to_db_and_back: This test constructs a models.User with an id and call mapper.model_to_db and assert the results contain the proper id

Test_default_role: Calls mapper.dict_to_model without a role and asserts the created user defaults role to user

#### test_repository_exceptions.py

This test purpose is to verify that the UserRepository can direct low-level pymongo failures to the apps repository and service exception and that those message work correctly

Main Coverage:
- Simulates DuplicateKeyErrors by configuring the mocked collection to raise that exception so the repository the repositorys error handling logic can be tested
- Tests missing data like UserNotFoundError by calling collection.find_one and returns none since there is no data matching that
- Tests updator methods by using a mocked collection and using updates, deltes and list functions to analyze how this collection reacts to these calls

#### test_repository.py

This test runs unit test for UserRepository to make sure CRUD and utility methods will behave as expected when the DB operations succeed

Main Coverage:
- Gives created user id and tests if there is a pre assigned one
- Maps DB docs to user and will return correct fields
- Tests update flows, ensures update_one is called and runs duplicate checks
- Checks if delete actaully deletes one and return delted_count

#### test_service_int.py

This integration test uses the User Service against a real MongoDB instance and validate end to end logic like user creation, authentication, authorization rules and a full get/update/delete lifecycle

Main Coverage:
- Uses the mongoclient and creates a test DB
- it clears the user collection initializes UserRepository and userservice and seeds an admin user thats used by tests

#### test_service_unit.py

These unit tests are for the UserService logic and use a mocked repository. They verify authentication, authorization, password hashing and proper translation of repo errors

Main Coverage:
- ensures create and update user hash passwords before calling the repo
- Tests non admin self registration
- Duplicates errors translate to service exceptions
- Successful auth by username and fallback to email
- get/update/delete/list on admin vs. self

#### test_app_interface.py

This provides e2e tests for the NiceGui app. This excercises the real app pages and the backend app logic using a real MongoDB instance

Main Coverage:
- Verifies UI login integration with the service layer and role based visibility works when pages are fully rendered
- Runs via nicegui testing harness 
``` pytestmark = pytest.mark.nicegui_main_file('src/run_app.py') ```
so the app is booted under test

#### test_app_logic_int.py

These are integration tests for applogic using a real mongodb instance to validate seeding, login and RBAC behavior end-to-end

Main Coverage:
- Uses seed_admin and creates an admin user when non exists and verifies DB documentation and role
- Creates a user and tests a successful login and invalid apssword failure
- confirms admins can list users and standard user are denied that exists

#### test_api_int.py

This integration test excercises the FastAPI endpoint end to end using testclient

How:
- POSTs JSON to api/v1/login with admin crednetials and asserts a 200 response
- extracts returned access_token and uses it as a bearer token to GET api/v1/users/me
- asserts the protected endpoint and returns the admin email

#### test_api_unit.py

Provides unit tests for the FASTAPI endpoints using testclient and dependency overriding to avoid a real DB/service

How:
- test_login_success: creates a MagicMock service and sets mock_service.login.return_value, overrides the route dependency to return the mock, posts JSON to api/v1/login and asserts a 200 response and that the response contains access_token
- test_protected_route_no_token: Calls GET /api/v1/users/me without authorization header and asserts the security dependecy return 401

#### test_api_e2e.py

e2e test that uses the real running api and verfiies its authentication and protected endpoint using HTTP requests

How:
- Posts JSON to api/v1/login with admin credentials and extracts the access token
- calls /api/v1/user/me with the Bearer token and asserts a 200 response and presence of an id in the json

#### standalone_remote_test.py

e2e tests that talks to the api and verifies authentication and a basic protected read

How:
- POSTs to api/v1/login with admin credentials and asserts a 200 + access_token
- Attempts login for a previously seeded test user and asserts a token is returned
- uses the admin token to GET api/v1/user/email for the test user abd asserts the response contains email or username
