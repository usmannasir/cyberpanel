import importlib
import os
import pathlib
import stat
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from jose import JWTError, jwt

from plogical.securityUtils import (
    TERMINAL_JWT_AUDIENCE,
    TERMINAL_JWT_ISSUER,
    TERMINAL_JWT_SECRET_ENV,
    TERMINAL_JWT_SECRET_FILE_ENV,
    get_terminal_jwt_secret,
)


class TerminalSecretTests(unittest.TestCase):
    def test_terminal_errors_use_the_available_log_writer(self):
        source = (
            pathlib.Path(__file__).parents[1]
            / "websiteFunctions/website.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("CyberCPLogFileWriter.writeLog(", source)

    def test_permission_repairs_preserve_terminal_secret_access(self):
        root = pathlib.Path(__file__).parents[1]
        for script_path in (root / "plogical/acl.py", root / "plogical/upgrade.py"):
            source = script_path.read_text(encoding="utf-8")
            self.assertIn(
                'terminalSecretPath = '
                "'/usr/local/CyberCP/terminal_jwt_secret'",
                source,
            )
            self.assertIn(
                'command = "chown cyberpanel:cyberpanel %s" % '
                'terminalSecretPath',
                source,
            )
            self.assertIn(
                'command = "chmod 600 %s" % terminalSecretPath',
                source,
            )

    def test_secret_is_created_once_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_path = os.path.join(temp_dir, "terminal-secret")
            environment = {
                TERMINAL_JWT_SECRET_ENV: "",
                TERMINAL_JWT_SECRET_FILE_ENV: secret_path,
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                first = get_terminal_jwt_secret(create_if_missing=True)
                second = get_terminal_jwt_secret(create_if_missing=True)

            self.assertEqual(first, second)
            self.assertGreaterEqual(len(first), 32)
            self.assertEqual(stat.S_IMODE(os.stat(secret_path).st_mode), 0o600)

    def test_existing_secret_permissions_are_repaired(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_path = os.path.join(temp_dir, "terminal-secret")
            with open(secret_path, "w") as secret_file:
                secret_file.write("p" * 64)
            os.chmod(secret_path, 0o644)
            environment = {
                TERMINAL_JWT_SECRET_ENV: "",
                TERMINAL_JWT_SECRET_FILE_ENV: secret_path,
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                self.assertEqual(get_terminal_jwt_secret(), "p" * 64)

            self.assertEqual(stat.S_IMODE(os.stat(secret_path).st_mode), 0o600)

    def test_missing_secret_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_path = os.path.join(temp_dir, "missing-secret")
            environment = {
                TERMINAL_JWT_SECRET_ENV: "",
                TERMINAL_JWT_SECRET_FILE_ENV: secret_path,
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(RuntimeError):
                    get_terminal_jwt_secret(create_if_missing=False)

    def test_short_environment_secret_is_rejected(self):
        environment = {
            TERMINAL_JWT_SECRET_ENV: "too-short",
            TERMINAL_JWT_SECRET_FILE_ENV: "",
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            with self.assertRaises(RuntimeError):
                get_terminal_jwt_secret(create_if_missing=True)

    def test_unwritable_secret_path_fails_closed(self):
        with tempfile.NamedTemporaryFile() as parent_file:
            secret_path = os.path.join(parent_file.name, "terminal-secret")
            environment = {
                TERMINAL_JWT_SECRET_ENV: "",
                TERMINAL_JWT_SECRET_FILE_ENV: secret_path,
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(RuntimeError):
                    get_terminal_jwt_secret(create_if_missing=True)


class TerminalTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.secret = "s" * 64
        cls.environment = mock.patch.dict(
            os.environ,
            {
                TERMINAL_JWT_SECRET_ENV: cls.secret,
                TERMINAL_JWT_SECRET_FILE_ENV: "",
            },
            clear=False,
        )
        cls.environment.start()
        sys.modules.pop("fastapi_ssh_server", None)
        cls.server = importlib.import_module("fastapi_ssh_server")

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("fastapi_ssh_server", None)
        cls.environment.stop()

    def make_token(self, **overrides):
        now = int(time.time())
        payload = {
            "iss": TERMINAL_JWT_ISSUER,
            "aud": TERMINAL_JWT_AUDIENCE,
            "iat": now,
            "nbf": now,
            "exp": now + 600,
            "sub": "1",
            "ssh_user": "example",
        }
        payload.update(overrides)
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def test_valid_panel_token_is_accepted(self):
        payload = self.server.decode_terminal_token(self.make_token())
        self.assertEqual(payload["ssh_user"], "example")

    def test_wrong_signing_secret_is_rejected(self):
        token = jwt.encode(
            {
                "iss": TERMINAL_JWT_ISSUER,
                "aud": TERMINAL_JWT_AUDIENCE,
                "iat": int(time.time()),
                "nbf": int(time.time()),
                "exp": int(time.time()) + 600,
                "ssh_user": "root",
            },
            "w" * 64,
            algorithm="HS256",
        )
        with self.assertRaises(JWTError):
            self.server.decode_terminal_token(token)

    def test_missing_issuer_is_rejected(self):
        token = self.make_token(iss=None)
        with self.assertRaises(JWTError):
            self.server.decode_terminal_token(token)

    def test_excessive_token_lifetime_is_rejected(self):
        now = int(time.time())
        token = self.make_token(iat=now, nbf=now, exp=now + 3600)
        with self.assertRaises(JWTError):
            self.server.decode_terminal_token(token)

    def make_account(self, home):
        return SimpleNamespace(
            pw_dir=str(home),
            pw_uid=os.getuid(),
            pw_gid=os.getgid(),
        )

    def test_authorized_keys_updates_preserve_other_terminal_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = pathlib.Path(temp_dir) / "site.example"
            home.mkdir()
            descriptor = self.server.open_authorized_keys(
                self.make_account(home),
                allowed_home_root=temp_dir,
            )
            try:
                self.server.add_ephemeral_key(descriptor, "ssh-rsa first", "webterm-first")
                self.server.add_ephemeral_key(descriptor, "ssh-rsa second", "webterm-second")
                self.server.remove_ephemeral_key(descriptor, "webterm-first")
            finally:
                os.close(descriptor)

            authorized_keys = home / ".ssh" / "authorized_keys"
            content = authorized_keys.read_text(encoding="utf-8")
            self.assertNotIn("webterm-first", content)
            self.assertIn("webterm-second", content)
            self.assertEqual(stat.S_IMODE(authorized_keys.stat().st_mode), 0o600)

    def test_ssh_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            home = root / "site.example"
            target = root / "target"
            home.mkdir()
            target.mkdir()
            victim = target / "authorized_keys"
            victim.write_text("preserve\n", encoding="utf-8")
            (home / ".ssh").symlink_to(target)

            with self.assertRaises(OSError):
                self.server.open_authorized_keys(
                    self.make_account(home),
                    allowed_home_root=temp_dir,
                )
            self.assertEqual(victim.read_text(encoding="utf-8"), "preserve\n")

    def test_authorized_keys_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            home = root / "site.example"
            ssh_dir = home / ".ssh"
            home.mkdir()
            ssh_dir.mkdir()
            victim = root / "victim"
            victim.write_text("preserve\n", encoding="utf-8")
            (ssh_dir / "authorized_keys").symlink_to(victim)

            with self.assertRaises(OSError):
                self.server.open_authorized_keys(
                    self.make_account(home),
                    allowed_home_root=temp_dir,
                )
            self.assertEqual(victim.read_text(encoding="utf-8"), "preserve\n")

    def test_authorized_keys_hard_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            home = root / "site.example"
            ssh_dir = home / ".ssh"
            home.mkdir()
            ssh_dir.mkdir()
            victim = root / "victim"
            victim.write_text("preserve\n", encoding="utf-8")
            os.link(victim, ssh_dir / "authorized_keys")

            with self.assertRaises(PermissionError):
                self.server.open_authorized_keys(
                    self.make_account(home),
                    allowed_home_root=temp_dir,
                )
            self.assertEqual(victim.read_text(encoding="utf-8"), "preserve\n")


if __name__ == "__main__":
    unittest.main()
