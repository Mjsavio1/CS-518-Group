# Lab 4 Group Report - User Repository & Integration Testing

## Participants

- Mike Savio - mjs1438 (savio/lab-5-1)

## Review

### Summary of Work Completed

Implemented a local UserService package that provides password hashing, authentication (username/email), requester-aware role-based authorization, and repository-exception translation into service-level errors; activity is logged to a top-level user_service.log. Updated unit tests.

**Features Added:**
 - Password hashing
 - Authentication (username/email)
 - Role‑based authorization with requester parameter
 - File‑based logging to top‑level user_service.log
 - Repository‑exception translation into service exceptions
 - Custom service errors for auth failure & unauthorized request
 - Unit and integration unittest test suites in user_service


### Code & Testing Summary

**UserService (2/19/26):**
When you call methods on the new UserService class, it wraps the repository with the business rules: passwords are hashed with before storage and verified on login, and authentication tries username first, then email, raising a FailedAuthenticationError if the hash doesn’t match. Every action takes a requester and checks their UserRole (admins can act on anyone, ordinary users only on themselves), if that check fails an UnauthorizedRequestError is raised.

### Comparison of Versions
Nothing to compare, there is only one version.

### Winning Code: Mike mjs1438

- After a heated deliberation between myself and I we unanimously decided to go with my code. Not much to disscuss since Mag hasn't finished yet. All new (and old) tests passed. I'll be happy to review what I have done with them when they can make time to meet. Everything I would say has already been said previously in this document.

## Retrospective

### Selection of Implementation

### Use of AI

**Tools Used:** VS Code Copilot integration

**Models Used:** Claude Haiku

**Initial Prompt:**

[Initial Prompt file: 05_promps.md](../prompts/05_promps.md)

**Follow-up Actions:**

- Manual Edits: Simplified alot of spagetti code it wrote, made sure all tests alligned and passed.

## Teamwork:

- I feel like the team is not working together well. I haven't seen my partner all week. And for the second week in a row I am completing this lab completly by myself.
- My only idea to improve team functioning is to be doing the work together and sharing responsibilities.