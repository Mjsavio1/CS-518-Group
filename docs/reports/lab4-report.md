# Lab 4 Group Report - User Repository & Integration Testing

## Participants

- Mike Savio - mjs1438 (savio/lab4)
- Mag Reisch - mer1158 (reisch/lab-4)

## Review

### Summary of Work Completed

We built a Repository system with custom exception handling, and integration testing against MongoDB.

**Features Added:**
- `UserRepository` class for database (create, read, update, delete, list)
- Exceptions: `DuplicateUsernameError`, `DuplicateEmailError`, `UserNotFoundError`, `InvalidUserDataError`, `RepositoryError`
- Mapper functions to convert between Python and MongoDB
- Indexes for unique constraints on username and email
- Configuration system for MongoDB
- Integration tests connecting to my MongoDB 

### Code & Testing Summary

**Repository Creation (2/10/26):**
When the repository was created, it first checks that the collection actually exists. Then it sets up indexes on username and email so MongoDB knows these fields should be different. When ‘create()’ is called with a user object, it converts to MongoDB, changing ‘id’ to ‘_id’ then saves it to the database. For error prevention, if someone tries to create a user with an email that already exists, MongoDB won't let it happen and will show an error. Then it's determined if it's a duplicate username or email, and throws the right exception.

**Integration Tests (2/12/26):**
The integration tests connect to my MongoDB database using the settings from config.py. Before even running tests, the setup creates a test database (with "_test_unittest" added to the name) that stays around for all the tests in that class. Before each test runs, this is deleted to start fresh. Then the test runs ‘create()’ and ‘read()’ against the real database to make sure everything works. If you try to create a user with a duplicate email, it should fail and raise a DuplicateEmailError. When tests are done, the code deletes the test database and closes the connection.

## Retrospective

### Selection of Implementation

### Use of AI

**Tools Used:** VS Code Copilot integration

**Models Used:** Claude Haiku

**Initial Prompt:**
- Prompt: Create a UserRepository class for database operations with custom exceptions for duplicate username, duplicate email, and user not found scenarios
- Result: AI generated a complete repository class with proper error handling and exception definitions

**Follow-up Actions:**
- Prompt 2: Implement integration tests connecting to live MongoDB with proper test fixtures
- Manual Edits: Simplified alot of spagetti code it wrote, adjusted test database naming and added direct MongoDB connectio nto mine specificly.

### Winning Code: Mike mjs1438
- I had the code completed by the time of the report needing to be done. Not much to disscuss since Mag hasn't finished yet. All tests passed and connct to MongoDB. I'll be happy to review what I have done with them when they can make time to meet. Everything I would say has already been said previously in this document. 