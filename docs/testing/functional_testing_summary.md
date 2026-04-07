# Functional Testing Summary (Group)

## Standalone remote API e2e test
- File: tests/e2e/test_api_remote_standalone.py
- Imports: unittest, requests
- Hardcoded and now deployed API URL is used.
- Ran directly with:

```python
if __name__ == "__main__":
    unittest.main()
```

## e2e and integration tests in this project
- tests/e2e/test_api_e2e.py
- tests/e2e/test_api_remote_standalone.py
- tests/user_api/test_api_int.py
- tests/user_service/test_service_int.py
- tests/user_app/test_app_logic_int.py
- tests/class_demo/integration/test_repository_integration.py
- tests/test_repository_integration.py

## How to run

### Remote standalone e2e test
```powershell
C:/Users/Mjsav/AppData/Local/Programs/Python/Python312/python.exe -m unittest tests/e2e/test_api_remote_standalone.py -v
```

### Local integration tests
```powershell
$env:RUN_INTEGRATION_TESTS='1'
C:/Users/Mjsav/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/user_api/test_api_int.py tests/user_service/test_service_int.py tests/user_app/test_app_logic_int.py -q -rs
```

## Verification result (remote standalone)
- Date: 2026-04-01
- Result: PASS
- Output summary: Ran 1 test, OK
