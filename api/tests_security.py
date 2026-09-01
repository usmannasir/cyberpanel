import os
import tempfile
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from plogical.securityUtils import (
    api_token_matches,
    ensure_api_token,
    generate_api_token,
    get_remote_transfer_dir_path,
    get_remote_transfer_log_path,
    get_remote_transfer_pid_path,
    get_mysql_upgrade_status_path,
    get_terminal_jwt_secret,
    is_safe_hostname,
    is_safe_sql_identifier,
    is_safe_numeric_id,
    is_safe_port,
    is_safe_remote_host,
    is_safe_system_user,
)
from api.views import can_change_api_account_password, can_change_api_website_package, get_api_admin
from loginSystem.models import Administrator
from plogical.acl import ACLManager


class SecurityUtilsTests(SimpleTestCase):
    def test_api_token_matches_legacy_basic_and_bearer_forms(self):
        self.assertTrue(api_token_matches("Bearer abc123", "Basic abc123"))
        self.assertTrue(api_token_matches("abc123", "Basic abc123"))
        self.assertTrue(api_token_matches("abc123", "Basic abc123="))
        self.assertFalse(api_token_matches("Bearer abc123", "Basic different"))

    def test_api_token_matches_rejects_placeholder_values(self):
        for placeholder in ('None', 'none', 'NULL', 'undefined', 'Basic None', 'Bearer null', '='):
            with self.subTest(placeholder=placeholder):
                self.assertFalse(api_token_matches(placeholder, placeholder))

        self.assertFalse(api_token_matches('Bearer None', 'Basic None'))

    def test_generated_api_tokens_are_random_and_usable(self):
        first = generate_api_token()
        second = generate_api_token()

        self.assertTrue(first.startswith('Basic '))
        self.assertNotEqual(first, second)
        self.assertTrue(api_token_matches(first, first))

    def test_ensure_api_token_only_rotates_invalid_tokens(self):
        invalid_account = SimpleNamespace(token='None', save=mock.Mock())
        valid_account = SimpleNamespace(token='Basic existing-token', save=mock.Mock())

        self.assertTrue(ensure_api_token(invalid_account))
        self.assertTrue(api_token_matches(invalid_account.token, invalid_account.token))
        invalid_account.save.assert_called_once_with(update_fields=['token'])

        self.assertFalse(ensure_api_token(valid_account))
        self.assertEqual(valid_account.token, 'Basic existing-token')
        valid_account.save.assert_not_called()

    def test_administrator_model_has_no_placeholder_token_default(self):
        token_field = Administrator._meta.get_field('token')
        self.assertEqual(token_field.default, '')

    def test_admin_acl_detection_uses_the_effective_acl_config(self):
        custom_admin_acl = SimpleNamespace(
            adminStatus=0,
            config='{"adminStatus": 1}',
        )
        regular_acl = SimpleNamespace(
            adminStatus=0,
            config='{"adminStatus": 0}',
        )

        self.assertTrue(ACLManager.isAdminACL(custom_admin_acl))
        self.assertFalse(ACLManager.isAdminACL(regular_acl))

    @patch('api.views.Administrator.objects.get')
    def test_suspended_account_cannot_authenticate_to_api(self, get_admin):
        get_admin.return_value = SimpleNamespace(
            api=1,
            state='SUSPENDED',
            token='Basic valid-token',
            password='stored-password',
        )
        request = RequestFactory().post(
            '/api/listPackage',
            HTTP_AUTHORIZATION='Bearer valid-token',
        )

        admin, response = get_api_admin(
            request,
            {'adminUser': 'suspended-user'},
        )

        self.assertIsNone(admin)
        self.assertEqual(response.status_code, 401)

    def test_terminal_secret_prefers_secret_file(self):
        expected_secret = "file-secret-which-is-long-enough-for-hs256"
        with tempfile.NamedTemporaryFile("w", delete=False) as secret_file:
            secret_file.write(expected_secret + "\n")
            secret_path = secret_file.name

        old_path = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET_FILE")
        old_secret = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET")
        try:
            os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = secret_path
            os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET", None)
            self.assertEqual(get_terminal_jwt_secret(), expected_secret)
        finally:
            if old_path is None:
                os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET_FILE", None)
            else:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = old_path

            if old_secret is not None:
                os.environ["CYBERPANEL_TERMINAL_JWT_SECRET"] = old_secret

            os.unlink(secret_path)

    def test_terminal_secret_fails_when_not_configured(self):
        old_path = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET_FILE")
        old_secret = os.environ.get("CYBERPANEL_TERMINAL_JWT_SECRET")
        os.environ["CYBERPANEL_TERMINAL_JWT_SECRET_FILE"] = "/path/that/does/not/exist"
        os.environ.pop("CYBERPANEL_TERMINAL_JWT_SECRET", None)

        try:
            with self.assertRaises(RuntimeError):
                get_terminal_jwt_secret()
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

    def test_admin_command_parameters_use_strict_formats(self):
        self.assertTrue(is_safe_system_user('site_user-1'))
        self.assertFalse(is_safe_system_user('site;id'))
        self.assertTrue(is_safe_hostname('panel.example.com'))
        self.assertFalse(is_safe_hostname('panel.example.com;id'))
        self.assertFalse(is_safe_hostname('localhost'))

    def test_mysql_upgrade_status_path_is_private_and_confined(self):
        with tempfile.TemporaryDirectory() as base_path:
            status_path = os.path.join(base_path, 'mysql-upgrade-safe123')
            with open(status_path, 'w', encoding='utf-8') as status_file:
                status_file.write('Starting\n')
            os.chmod(status_path, 0o600)

            self.assertEqual(
                status_path,
                get_mysql_upgrade_status_path(status_path, base_path),
            )
            self.assertEqual(
                '',
                get_mysql_upgrade_status_path('/etc/passwd', base_path),
            )

            os.chmod(status_path, 0o644)
            self.assertEqual(
                '',
                get_mysql_upgrade_status_path(status_path, base_path),
            )

    def test_mysql_upgrade_status_path_rejects_symlinks_and_hard_links(self):
        with tempfile.TemporaryDirectory() as base_path:
            target = os.path.join(base_path, 'mysql-upgrade-target')
            symlink = os.path.join(base_path, 'mysql-upgrade-symlink')
            hard_link = os.path.join(base_path, 'mysql-upgrade-hardlink')
            with open(target, 'w', encoding='utf-8') as status_file:
                status_file.write('Starting\n')
            os.chmod(target, 0o600)
            os.symlink(target, symlink)
            os.link(target, hard_link)

            self.assertEqual(
                '',
                get_mysql_upgrade_status_path(symlink, base_path),
            )
            self.assertEqual(
                '',
                get_mysql_upgrade_status_path(hard_link, base_path),
            )

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
