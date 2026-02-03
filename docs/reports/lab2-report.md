# Models & Mapper — Final Consolidated Report

## Overview
This report documents how the `User` Pydantic model and mapper were implemented, how the solution was tested and verified, planning notes, AI usage summary, and a short discussion of the code and tests.

## PLANNING
- Goal: Implement Pydantic `User` model, mapper between dict/model/pymongo document, and unit tests using `unittest`.
- Constraints: Use Pydantic for models; repository layer with `pymongo` was requested but optional for this lab; tests should use `unittest`.

Planned steps:
- Create `src/class_demo/user_service/models.py` with `User` model.
- Create `src/class_demo/user_service/mapper.py` with conversion functions: `dict_to_model`, `model_to_dict`, `model_to_db`, `db_to_model`.
- Add package `__init__.py` files for importability.
- Create `tests/user_service/test_mapper.py` verifying mappings and defaults.
- Run tests and incorporate output into this report.

Status: All planned implementation steps were completed; tests executed and passed.

## USE OF AI
Tools used:
- Chat-based assistant (AI chat) to generate and refine code snippets and tests.
- VS Code (workspace editing) to apply files and run tests.
- Local terminal to run `python -m unittest discover -v`.

Model:
- I used GPT-5 mini (assistant) to help generate code, tests, and the report content.

How AI was used (summary):
- Drafted the Pydantic `User` model and mapper functions.
- Created unit tests to validate mappings and defaults.
- Reviewed the code and suggested minor improvements (e.g., awareness of Pydantic v2 deprecations).

Prompt summary (no full prompt/response transcripts):
- Initial Prompt: Implement Pydantic `User` model and a mapper to translate between user input dicts, Pydantic model objects, and pymongo documents, plus `unittest` tests.
- Iterations: Follow-ups requested package init files, tests, and verification runs; the code was adjusted to include `id` <-> `_id` mapping in the mapper and to include default role handling.

Note: Full prompt/response logs are omitted from this report per instructions; they can be exported to the repository separately if desired.

## CODE CHANGE SUMMARY
- `src/class_demo/user_service/models.py`: Defines `User` Pydantic model with fields `id: Optional[str]`, `email: EmailStr`, `username: str`, `password: str`, `role: Literal["admin","user"]` with default `"user"`.
- `src/class_demo/user_service/mapper.py`: Implements four functions:
  - `dict_to_model(data)` -> `User` (validates input)
  - `model_to_dict(user)` -> plain dict for controller use
  - `model_to_db(user)` -> pymongo document mapping `id` -> `_id`
  - `db_to_model(doc)` -> `User` mapping `_id` -> `id`
- `tests/user_service/test_mapper.py`: Unit tests covering validation, `id` <-> `_id` mapping, and default `role` behavior.
- `src/class_demo/user_service/__init__.py` and `src/class_demo/__init__.py` added for package importability.

Files added (paths):
- `src/class_demo/user_service/models.py`
- `src/class_demo/user_service/mapper.py`
- `src/class_demo/user_service/__init__.py`
- `src/class_demo/__init__.py`
- `tests/user_service/test_mapper.py`

## VERIFICATION / TESTING
Command used to run tests:
```bash
python -m unittest discover -v
```

Captured test output (run on local workspace):
```
C:\Users\Mjsav\cs-518-group> python -m unittest discover -v
C:\Users\Mjsav\AppData\Local\Programs\Python\Python312\Lib\site-packages\pydantic\_internal\_config.py:341: UserWarning: Valid config keys have changed in V2:
* 'orm_mode' has been renamed to 'from_attributes'
  warnings.warn(message, UserWarning)
test_default_role (tests.user_service.test_mapper.TestMapper.test_default_role) ... ok
test_dict_to_model_valid (tests.user_service.test_mapper.TestMapper.test_dict_to_model_valid) ... ok
test_model_to_db_and_back (tests.user_service.test_mapper.TestMapper.test_model_to_db_and_back) ... 
C:\Users\Mjsav\AppData\Local\Programs\Python\Python312\Lib\site-packages\pydantic\main.py:1114: PydanticDeprecatedSince20: The `dict` method is deprecated; use `model_dump` instead.
  warnings.warn('The `dict` method is deprecated; use `model_dump` instead.', category=PydanticDeprecatedSince20)
ok

----------------------------------------------------------------------
Ran 3 tests in 0.005s

OK
```

Summary of test coverage:
- Tested:
  - `dict_to_model` input validation and mapping of required fields.
  - `model_to_db` mapping of `id` -> `_id` and `db_to_model` mapping back.
  - Default `role` behavior when not provided.
- Not tested (areas left for further work):
  - Repository layer using `pymongo` (no DB calls present).
  - Service/controller behavior and integration tests.
  - Security considerations such as password hashing or secure storage.

## CODE REVIEW & DISCUSSION
Design choices and rationale:
- Pydantic `User` model uses `EmailStr` to validate email format and `Literal` for role to limit values to `admin` or `user`.
- Mapper keeps model-layer semantics separate from DB representation by converting between `id` and `_id`.

What additional research was done:
- Checked Pydantic v2 migration notes and warnings (noted deprecations: `orm_mode` → `from_attributes`, `dict()` → `model_dump()`).

Discussion summary / reflections:
- The core lab goals were met: models, mapper, and unit tests were implemented.
- Next logical improvements: add a repository module implementing `pymongo` interactions and a service layer to encapsulate business logic; add password hashing and tests for repository integration (could use a test MongoDB instance or mocks).
- The tests are small and focused on unit-level behavior; broaden test coverage if integrating with DB or external services.

## PROMPT LOG
- Initial prompt (summary): Create Pydantic models and a mapper between dicts, Pydantic models, and pymongo documents; include `unittest` tests. The instruction file is `docs/prompts/02_2-models_mapper.md`.
- Iterations (summary): Follow-up prompts requested packaging (`__init__.py`), running unit tests, and producing a consolidated report. AI was also used to refine code for `id`/_id mapping and to note Pydantic deprecations.