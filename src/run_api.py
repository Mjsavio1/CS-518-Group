"""Entry point for the user service API.

Can be executed directly or via ``uvicorn src.run_api:app``.  The
``app`` object is imported from :mod:`class_demo.user_api` so that tooling
and tests can access it without running the server.
"""

from class_demo.user_api import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
