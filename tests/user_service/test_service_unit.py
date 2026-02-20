import unittest
from unittest.mock import Mock, MagicMock

from src.class_demo.user_service.models import User, UserRole
from src.class_demo.user_service.service import UserService
from src.class_demo.user_service import service_exceptions as svc_exc
from src.class_demo.user_service import repository_exceptions as repo_exc


def make_user(**kwargs):
    # convenience factory with some defaults
    data = {
        "id": kwargs.get("id", "u1"),
        "username": kwargs.get("username", "user1"),
        "email": kwargs.get("email", "u1@example.com"),
        "password": kwargs.get("password", "pass"),
        "role": kwargs.get("role", UserRole.user),
    }
    return User(**data)


class TestUserServiceUnit(unittest.TestCase):
    def setUp(self):
        self.mock_repo = Mock()
        self.service = UserService(self.mock_repo)
        # make a simple admin and regular user
        self.admin = make_user(id="admin", username="admin", role=UserRole.admin)
        self.user = make_user()

    def test_hashing_happens_on_create(self):
        # password should be hashed before repository call
        created = make_user()
        self.mock_repo.create.return_value = created

        res = self.service.create_user(None, {"username": "user1", "email": "a@b.com", "password": "secret"})
        self.assertIsNotNone(res)
        # repo should receive hashed password not plain
        args = self.mock_repo.create.call_args[0][0]
        self.assertNotEqual(args.password, "secret")
        self.assertTrue("$" in args.password)

    def test_create_as_non_admin_self(self):
        # non-admin creating their own account is allowed
        self.mock_repo.create.return_value = self.user
        r = self.service.create_user(self.user, {"username": "user1", "email": "u1@e.com", "password": "p"})
        self.assertEqual(r.username, "user1")

    def test_create_as_non_admin_other_disallowed(self):
        with self.assertRaises(svc_exc.UnauthorizedRequestError):
            self.service.create_user(self.user, {"username": "someone", "email": "e@e.com", "password": "p"})

    def test_create_missing_password(self):
        with self.assertRaises(svc_exc.InvalidUserDataError):
            self.service.create_user(None, {"username": "u"})

    def test_repository_duplicate_translated(self):
        self.mock_repo.create.side_effect = repo_exc.DuplicateUsernameError("foo")
        with self.assertRaises(svc_exc.DuplicateUsernameError):
            self.service.create_user(None, {"username": "foo", "email": "a@b.com", "password": "p"})

    def test_authenticate_success_username(self):
        stored = make_user(password="hashed$abc")
        # patch verify function to always return True
        self.service._repo.read_by_username.return_value = stored
        # monkey patch module helper to bypass hashing
        import src.class_demo.user_service.service as svc_module
        svc_module._verify_password = lambda pw, h: True
        res = self.service.authenticate("user1", "whatever")
        self.assertEqual(res.username, "user1")

    def test_authenticate_fallback_to_email(self):
        stored = make_user(password="h$sh")
        self.service._repo.read_by_username.side_effect = repo_exc.UserNotFoundError()
        self.service._repo.read_by_email.return_value = stored
        import src.class_demo.user_service.service as svc_module
        svc_module._verify_password = lambda pw, h: True
        res = self.service.authenticate("u1@example.com", "pw")
        self.assertEqual(res.email, "u1@example.com")

    def test_authenticate_bad_credentials(self):
        self.service._repo.read_by_username.side_effect = repo_exc.UserNotFoundError()
        self.service._repo.read_by_email.side_effect = repo_exc.UserNotFoundError()
        with self.assertRaises(svc_exc.FailedAuthenticationError):
            self.service.authenticate("none", "pw")

    def test_authenticate_wrong_password(self):
        stored = make_user(password="something")
        self.service._repo.read_by_username.return_value = stored
        import src.class_demo.user_service.service as svc_module
        svc_module._verify_password = lambda pw, h: False
        with self.assertRaises(svc_exc.FailedAuthenticationError):
            self.service.authenticate("user1", "pw")

    def test_get_user_authorization(self):
        # admin allowed
        self.service._repo.read.return_value = self.user
        out = self.service.get_user(self.admin, "u1")
        self.assertEqual(out, self.user)
        # self allowed
        out = self.service.get_user(self.user, "u1")
        self.assertEqual(out, self.user)
        # other user not allowed
        with self.assertRaises(svc_exc.UnauthorizedRequestError):
            self.service.get_user(self.user, "someone_else")

    def test_get_user_not_found_translates(self):
        self.service._repo.read.side_effect = repo_exc.UserNotFoundError()
        with self.assertRaises(svc_exc.UserNotFoundError):
            self.service.get_user(self.admin, "nope")

    def test_update_user_hash_password(self):
        # ensure password hashing occurs and authorization
        existing = make_user()
        self.service._repo.read.return_value = existing
        self.service._repo.update.return_value = existing
        out = self.service.update_user(self.user, "u1", {"password": "new"})
        self.assertNotEqual(out.password, "new")

    def test_update_user_unauthorized(self):
        with self.assertRaises(svc_exc.UnauthorizedRequestError):
            self.service.update_user(self.user, "other", {"email": "x"})

    def test_delete_user_authorization(self):
        # admin can delete
        self.service.delete_user(self.admin, "u1")
        # self can delete
        self.service.delete_user(self.user, "u1")
        # others cannot
        with self.assertRaises(svc_exc.UnauthorizedRequestError):
            self.service.delete_user(self.user, "someone")

    def test_list_users_admin_only(self):
        self.service._repo.list_all.return_value = [self.user]
        self.service.list_users(self.admin)  # should not raise
        with self.assertRaises(svc_exc.UnauthorizedRequestError):
            self.service.list_users(self.user)

    def test_repository_errors_bubble(self):
        self.mock_repo.create.side_effect = repo_exc.RepositoryError("boom")
        with self.assertRaises(svc_exc.RepositoryError):
            self.service.create_user(None, {"username": "u", "email": "e@e.com", "password": "p"})


if __name__ == "__main__":
    unittest.main()
