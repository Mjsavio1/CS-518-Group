import os
from nicegui import ui
from pymongo import MongoClient
from class_demo.user_service.service import UserService
from class_demo.user_service.repository import UserRepository
from class_demo.user_app.app_logic import AppLogic
from class_demo.user_app.pages import init_pages

# Initialize DB connection
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGODB_DB_NAME", "class_demo_db")]

# Layer initialization
repo = UserRepository(db["users"])
service = UserService(repo)
logic = AppLogic(service)

# Seed Admin
logic.seed_admin()

# Init UI
init_pages(logic)

# ONLY run the UI if this file is executed directly (not when imported by tests)
if __name__ in {"__main__", "fastapi"}:
    ui.run(
        title="User Auth Lab", 
        storage_secret=os.urandom(24).hex(),
        show=False  # Recommended for development/testing
    )