import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from plogical.securityUtils import (
    LEGACY_TERMINAL_JWT_SECRET,
    api_token_matches,
    get_remote_transfer_dir_path,
    get_remote_transfer_log_path,
    get_remote_transfer_pid_path,
    get_terminal_jwt_secret,
    is_safe_sql_identifier,
    is_safe_numeric_id,
    is_safe_port,
    is_safe_remote_host,
)
from api.views import can_change_api_account_password, can_change_api_website_package


class SecurityUtilsTests(SimpleTestCase):
    def test_api_token_matches_legacy_basic_and_bearer_forms(self):
        self.assertTrue(api_token_matches("Bearer abc123", "Basic abc123"))
        self.assertTrue(api_token_matches("abc123", "Basic abc123"))
        self.assertTrue(api_token_matches("abc123", "Basic abc123="))
        self.assertFalse(api_token_matches("Bearer abc123", "Basic different"))

    def test_terminal_secret_prefers_secret_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as secret_file:
            secret_file.write("file-secret\n")
            secret_path = secret_file.name

        old_path = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET_FILE")
        old_secret = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET")
        try:
            os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = secret_path
            os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET", None)
            self.assertEqual(get_terminal_jwt_secret(), "file-secret")
        finally:
            if old_path is None:
                os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET_FILE", None)
            else:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = old_path

            if old_secret is not None:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET"] = old_secret

            os.unlink(secret_path)

    def test_terminal_secret_has_legacy_fallback_for_compatibility(self):
        old_path = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET_FILE")
        old_secret = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET")
        os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = "/path/that/does/not/exist"
        os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET", None)

        try:
            self.assertEqual(get_terminal_jwt_secret(), LEGACY_TERMINAL_JWT_SECRET)
        finally:
            if old_path is None:
                os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET_FILE", None)
            else:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = old_path

            if old_secret is not None:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET"] = old_secret

    def test_sql_identifier_validation(self):
        self.assertTrue(is_safe_sql_identifier("user_db_1"))
        self.assertFalse(is_safe_sql_identifier("user-db"))
        self.assertFalse(is_safe_sql_identifier("db;DROP_TABLE"))
        self.assertFalse(is_safe_sql_identifier(""))

    def test_remote_transfer_validation_helpers(self):
        self.assertTrue(is_safe_numeric_id("1234"))
        self.assertFalse(is_safe_numeric_id("../1234"))
        self.assertTrue(is_safe_port("22"))
        self.assertFalse(is_safe_port("70000"))
        self.assertTrue(is_safe_remote_host("host.example.com"))
        self.assertFalse(is_safe_remote_host("host;rm"))

    def test_remote_transfer_log_path_accepts_numeric_ids_only(self):
        with tempfile.TemporaryDirectory() as base_path:
            expected_path = os.path.realpath(os.path.join(base_path, "transfer-1234", "backup_log"))

            self.assertEqual(get_remote_transfer_log_path("1234", base_path), expected_path)
            self.assertEqual(get_remote_transfer_log_path("../1234", base_path), "")
            self.assertEqual(get_remote_transfer_log_path("/etc/passwd", base_path), "")
            self.assertEqual(get_remote_transfer_log_path("1234;id", base_path), "")
            self.assertEqual(get_remote_transfer_log_path("1234\nid", base_path), "")
            self.assertEqual(get_remote_transfer_log_path("$(id)", base_path), "")
            self.assertEqual(get_remote_transfer_log_path("`id`", base_path), "")

    def test_remote_transfer_log_path_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as base_path, tempfile.TemporaryDirectory() as outside_path:
            transfer_path = os.path.join(base_path, "transfer-1234")
            os.symlink(outside_path, transfer_path)

            self.assertEqual(get_remote_transfer_log_path("1234", base_path), "")

    def test_remote_transfer_cancel_paths_share_same_validation(self):
        with tempfile.TemporaryDirectory() as base_path:
            expected_dir = os.path.realpath(os.path.join(base_path, "transfer-1234"))
            expected_pid = os.path.realpath(os.path.join(expected_dir, "pid"))

            self.assertEqual(get_remote_transfer_dir_path("1234", base_path), expected_dir)
            self.assertEqual(get_remote_transfer_pid_path("1234", base_path), expected_pid)
            self.assertEqual(get_remote_transfer_dir_path("../1234", base_path), "")
            self.assertEqual(get_remote_transfer_pid_path("1234;id", base_path), "")

    def test_api_password_change_allows_self_service(self):
        admin = SimpleNamespace(pk=10)
        self.assertTrue(can_change_api_account_password(admin, admin))

    def test_api_password_change_blocks_non_admin_cross_account(self):
        caller = SimpleNamespace(pk=10)
        target = SimpleNamespace(pk=1)

        with patch("api.views.ACLManager.loadedACL", return_value={"admin": 0}):
            self.assertFalse(can_change_api_account_password(caller, target))

    def test_api_password_change_allows_super_admin_cross_account(self):
        caller = SimpleNamespace(pk=1)
        target = SimpleNamespace(pk=10)

        with patch("api.views.ACLManager.loadedACL", return_value={"admin": 1}):
            self.assertTrue(can_change_api_account_password(caller, target))

    def test_api_change_package_requires_permission_ownership_and_package_access(self):
        admin = SimpleNamespace(pk=10)
        website = SimpleNamespace(domain="example.com")
        package = SimpleNamespace(packageName="reseller_package")

        with patch("api.views.ACLManager.loadedACL", return_value={"admin": 0}), \
                patch("api.views.ACLManager.currentContextPermission", return_value=1), \
                patch("api.views.ACLManager.checkOwnership", return_value=1), \
                patch("api.views.ACLManager.CheckPackageOwnership", return_value=1):
            self.assertTrue(can_change_api_website_package(admin, website, package))

        with patch("api.views.ACLManager.loadedACL", return_value={"admin": 0}), \
                patch("api.views.ACLManager.currentContextPermission", return_value=1), \
                patch("api.views.ACLManager.checkOwnership", return_value=0), \
                patch("api.views.ACLManager.CheckPackageOwnership", return_value=1):
            self.assertFalse(can_change_api_website_package(admin, website, package))
