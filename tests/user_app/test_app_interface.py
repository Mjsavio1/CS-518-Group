import pytest
from nicegui import ui
from nicegui.testing import Screen
from pymongo import MongoClient
import os
from selenium.webdriver.common.by import By

os.environ["MONGODB_DB_NAME"] = "test_ui_db"
pytestmark = pytest.mark.nicegui_main_file('src/run_app.py')
from class_demo.user_service.service import UserService
from class_demo.user_service.repository import UserRepository
from class_demo.user_app.app_logic import AppLogic
from class_demo.user_app.pages import init_pages

@pytest.fixture
def logic():
    """Setup logic layer with a clean test database."""
    # Ensure this matches the name set in the environment variable above
    db_name = "test_ui_db" 
    client = MongoClient("mongodb://localhost:27017")
    db = client[db_name]
    
    # Clear and Setup
    db.users.delete_many({}) 
    repo = UserRepository(db["users"])
    service = UserService(repo)
    app_logic = AppLogic(service)
    
    # Pre-create test admin
    app_logic.service.create_user(None, {
        "username": "ui_tester",
        "email": "ui@test.com",
        "password": "password123",
        "role": "admin"
    })
    
    yield app_logic
    
    # Cleanup
    client.drop_database(db_name)
    client.close()

def test_login_flow(screen: Screen, logic: AppLogic):
    init_pages(logic)
    screen.open('/login')
    screen.wait(1.0)
    
    screen.selenium.find_element(By.CSS_SELECTOR, 'input[aria-label="Username/Email"]').send_keys('ui_tester')
    screen.selenium.find_element(By.CSS_SELECTOR, 'input[aria-label="Password"]').send_keys('password123')
    
    screen.click('Login')
    
    # CHANGE 1: Increase wait time slightly or use a wait_until 
    # to account for network/DB latency during login
    screen.wait(2.0) 
    
    # CHANGE 2: Use a more direct check if should_contain is being finicky
    assert "Welcome, ui_tester" in screen.selenium.page_source

def test_unauthorized_access(screen: Screen, logic: AppLogic):
    """Test that non-admins cannot see the Admin Panel."""
    logic.service.create_user(None, {
        "username": "joe", "email": "joe@test.com", "password": "p", "role": "user"
    })
    
    init_pages(logic)
    screen.open('/login')
    screen.wait(1.0)
    
    screen.selenium.find_element(By.CSS_SELECTOR, 'input[aria-label="Username/Email"]').send_keys('joe')
    screen.selenium.find_element(By.CSS_SELECTOR, 'input[aria-label="Password"]').send_keys('p')
    
    screen.click('Login')
    screen.wait(1.0)
    
    screen.should_contain('Welcome, joe')
    screen.should_not_contain('Admin Panel')