import unittest
import requests


API_BASE_URL = "https://user-api.whitebay-c606c597.eastus.azurecontainerapps.io"


class TestApiRemoteE2E(unittest.TestCase):
    def create_user(self, payload, headers=None):
        return requests.post(f"{API_BASE_URL}/users", json=payload, headers=headers, timeout=30)

    def login(self, username, password):
        return requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
            timeout=30,
        )

    def test_remote_e2e_flow(self):
        admin_username = "remote_admin"
        admin_payload = {
            "username": admin_username,
            "email": "remote_admin@example.com",
            "password": "pw",
            "role": "admin",
        }

        # Create admin if missing; reuse if already present.
        create_admin = self.create_user(admin_payload)
        self.assertIn(create_admin.status_code, [200, 409])

        admin_login = self.login(admin_username, "pw")
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        user_username = "remote_bob"
        user_payload = {
            "username": user_username,
            "email": "remote_bob@example.com",
            "password": "pw",
        }

        create_user = self.create_user(user_payload, headers=admin_headers)
        self.assertIn(create_user.status_code, [200, 409])

        list_users = requests.get(f"{API_BASE_URL}/users", headers=admin_headers, timeout=30)
        self.assertEqual(list_users.status_code, 200)
        users = list_users.json()
        bob_matches = [u for u in users if u.get("username") == user_username]
        self.assertTrue(len(bob_matches) >= 1)
        bob_id = bob_matches[0]["id"]

        user_login = self.login(user_username, "pw")
        self.assertEqual(user_login.status_code, 200)
        user_token = user_login.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        get_self = requests.get(f"{API_BASE_URL}/users/{bob_id}", headers=user_headers, timeout=30)
        self.assertEqual(get_self.status_code, 200)
        self.assertEqual(get_self.json()["username"], user_username)

        forbidden_list = requests.get(f"{API_BASE_URL}/users", headers=user_headers, timeout=30)
        self.assertEqual(forbidden_list.status_code, 403)

        update_user = requests.put(
            f"{API_BASE_URL}/users/{bob_id}",
            json={"email": "remote_bob_changed@example.com"},
            headers=admin_headers,
            timeout=30,
        )
        self.assertEqual(update_user.status_code, 200)

        delete_user = requests.delete(f"{API_BASE_URL}/users/{bob_id}", headers=admin_headers, timeout=30)
        self.assertEqual(delete_user.status_code, 204)

        get_deleted = requests.get(f"{API_BASE_URL}/users/{bob_id}", headers=admin_headers, timeout=30)
        self.assertEqual(get_deleted.status_code, 404)


if __name__ == "__main__":
    unittest.main()
