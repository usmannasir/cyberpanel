import os
import tempfile

from django.test import SimpleTestCase

from plogical.securityUtils import (
    LEGACY_TERMINAL_JWT_SECRET,
    api_token_matches,
    get_terminal_jwt_secret,
    is_safe_sql_identifier,
    is_safe_numeric_id,
    is_safe_port,
    is_safe_remote_host,
)


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
