import os
from nicegui import ui
from pymongo import MongoClient
from dotenv import load_dotenv
from class_demo.user_service.service import UserService
from class_demo.user_service.repository import UserRepository
from class_demo.user_app.main import init_pages
from class_demo.user_app.logic import AppLogic

load_dotenv()

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

# Enforce a dark visual system with green accents across the app.
ui.colors(
        primary="#22c55e",
        secondary="#16a34a",
        accent="#15803d",
        positive="#22c55e",
        negative="#ef4444",
        warning="#f59e0b",
        info="#4ade80",
)
ui.add_head_html(
        """
        <style>
            :root {
                color-scheme: dark;
            }

            body,
            .q-layout,
            .q-page-container,
            .q-page {
                background: #000000 !important;
                color: #dcfce7 !important;
            }
        </style>
        """
)

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
# Include __mp_main__ for environments that spawn subprocesses.
if __name__ in {"__main__", "__mp_main__", "fastapi"}:
    run_ui()