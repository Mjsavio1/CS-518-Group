import unittest
import requests

BASE_URL = "https://user-api.calmocean-2a1fa5da.eastus2.azurecontainerapps.io"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "change_this_password"

class RemoteUserApiTest(unittest.TestCase):
    def test_full_user_lifecycle(self):
        # Admin login
        r = requests.post(f"{BASE_URL}/api/v1/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.assertEqual(r.status_code, 200)
        admin_token = r.json().get("access_token")
        self.assertTrue(admin_token)

        # Use the test user you seeded manually
        test_email = "testuser_ci@example.com"
        test_password = "TestPass123!"

        # Login as the new Test User (verify seeded credentials)
        r = requests.post(f"{BASE_URL}/api/v1/login", json={
            "email": test_email,
            "password": test_password
        })
        self.assertEqual(r.status_code, 200)
        user_token = r.json().get("access_token")
        self.assertTrue(user_token)

        # Read the Test User via GET /users/{email} using ADMIN token (required for this endpoint)
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{BASE_URL}/api/v1/users/{test_email}", headers=headers)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue("email" in body or "username" in body)

if __name__ == '__main__':
    unittest.main()