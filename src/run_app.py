import os
from nicegui import ui
from pymongo import MongoClient
from class_demo.user_service.service import UserService
from class_demo.user_service.repository import UserRepository
from class_demo.user_app.app_logic import AppLogic
from class_demo.user_app.pages import init_pages

# Initialize DB connection
mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise RuntimeError(
        "MONGODB_URI is not set. Set it to your MongoDB connection string (e.g. Atlas) "
        "before running the container."
    )

client = MongoClient(mongo_uri)
db = client[os.getenv("MONGODB_DB_NAME", "class_demo_db")]

# Layer initialization
repo = UserRepository(db["users"])
service = UserService(repo)
logic = AppLogic(service)

# Seed Admin
logic.seed_admin()

# Init UI
init_pages(logic)


def run_ui() -> None:
    ui.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        title="User Auth Lab",
        storage_secret=os.getenv("STORAGE_SECRET", os.urandom(24).hex()),
        show=False,
    )


# ONLY run the UI if this file is executed directly (not when imported by tests)
if __name__ in {"__main__", "fastapi"}:
    run_ui()