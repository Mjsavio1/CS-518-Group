import unittest

from src.class_demo.user_service import mapper, models


class TestMapper(unittest.TestCase):
    def test_dict_to_model_valid(self):
        data = {"email": "a@example.com", "username": "alice", "password": "pass", "role": "admin"}
        user = mapper.dict_to_model(data)
        self.assertEqual(user.email, "a@example.com")
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.role, "admin")

    def test_model_to_db_and_back(self):
        user = models.User(id="123", email="b@b.com", username="bob", password="pw", role="user")
        doc = mapper.model_to_db(user)
        self.assertIn("_id", doc)
        self.assertEqual(doc["_id"], "123")
        new_user = mapper.db_to_model(doc)
        self.assertEqual(new_user.id, "123")
        self.assertEqual(new_user.username, "bob")

    def test_default_role(self):
        data = {"email": "c@c.com", "username": "carol", "password": "pw"}
        user = mapper.dict_to_model(data)
        self.assertEqual(user.role, "user")


if __name__ == "__main__":
    unittest.main()
