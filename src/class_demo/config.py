import os


class Config:
    """Configuration for integration tests and runtime.

    Values can be overridden via environment variables.
    """

    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "class_demo_db")
