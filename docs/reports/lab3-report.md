# Lab 3 — Models and Mapper

**Objective**: Implement Pydantic user models and a `Mapper` to convert between dicts, Pydantic models, and DB documents. Keep implementations and tests simple and focused on mapping correctness.

**Files (created/updated)**
- **Models:** [src/class_demo/user_service/models.py](src/class_demo/user_service/models.py)
- **Mapper:** [src/class_demo/user_service/mapper.py](src/class_demo/user_service/mapper.py)
- **Tests:** [tests/user_service/test_mapper.py](tests/user_service/test_mapper.py)
- **Prompt used:** [docs/prompts/02_2-models_mapper.md](docs/prompts/02_2-models_mapper.md)

**Models (summary)**
- **UserBase:** fields `email`, `username`, `role` (str, "admin" or "user").
- **UserCreate:** extends `UserBase` and adds `password` (write-only).
- **UserInDB:** extends `UserBase` and adds `id` and `hashed_password` (internal DB representation).
- **UserRead:** public-facing model (no password) with `id`, `email`, `username`, `role`.

All models use Pydantic.

**Mapper (summary)**
- `Mapper.to_create_model(data: dict) -> UserCreate`: validate incoming dict into a `UserCreate`.
- `Mapper.to_read_model(db_doc: dict) -> UserRead`: convert a DB document (with `_id` and `hashed_password`) into a `UserRead`.
- `Mapper.to_db_document(user_create: UserCreate) -> dict`: prepare a DB document (e.g., hash password -> `hashed_password`, remove plain `password`).

Implementation notes: keep mapping logic deterministic and testable. Password hashing is stubbed or isolated so tests can assert mapping behavior without requiring specific hash algorithms.

**Tests (summary)**
- `test_map_dict_to_create_model`: asserts that valid input dict becomes a `UserCreate` with expected fields.
- `test_map_create_model_to_db_doc`: asserts that `to_db_document` removes `password` and adds `hashed_password` key.
- `test_map_db_doc_to_read_model`: asserts that DB document with `_id` maps to `UserRead` and omits `hashed_password`.

**Tests**
Tests are implemented in [tests/user_service/test_mapper.py](tests/user_service/test_mapper.py).

**Prompt log / workflow**
- Prompt file used: [docs/prompts/02_2-models_mapper.md](docs/prompts/02_2-models_mapper.md)
- Work performed: created Pydantic models, implemented a small `Mapper`, and added focused unit tests for mapping behavior.

**Verification**
- Tests cover the three mapping directions described above. If any tests fail, adjust model field names or mapping logic accordingly and re-run `pytest`.

**Notes / Next steps**
- Optionally replace password-hashing stub with a real hasher and add integration tests against the repository layer.
- Push changes to your branch and create a merge request per course workflow.
