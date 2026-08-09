import json
import os
import pwd
import subprocess
import sys
import tempfile
import unittest

from plogical.securityUtils import (
    consume_backup_request,
    create_backup_request,
    create_private_token_file,
    read_private_token_file,
    remove_stale_private_token_files,
)


class PrivateTokenFileTests(unittest.TestCase):
    def test_stale_cleanup_removes_only_regular_token_files(self):
        with tempfile.TemporaryDirectory() as directory:
            token, path = create_private_token_file(directory, "stale")
            os.utime(path, (0, 0))
            victim = os.path.join(directory, "victim")
            with open(victim, "w", encoding="utf-8") as handle:
                handle.write("preserve")
            link_token = "b" * 43
            os.symlink(victim, os.path.join(directory, link_token))

            self.assertEqual(1, remove_stale_private_token_files(directory, 1))
            self.assertFalse(os.path.exists(path))
            self.assertTrue(os.path.islink(os.path.join(directory, link_token)))
            with open(victim, encoding="utf-8") as handle:
                self.assertEqual("preserve", handle.read())

    def test_token_file_round_trip_does_not_expose_path(self):
        with tempfile.TemporaryDirectory() as directory:
            token, path = create_private_token_file(directory, "report")

            self.assertNotIn("/", token)
            self.assertEqual(os.path.join(directory, token), path)
            self.assertEqual("report", read_private_token_file(token, directory))

    def test_arbitrary_path_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            victim = os.path.join(directory, "victim")
            with open(victim, "w", encoding="utf-8") as handle:
                handle.write("private")

            self.assertRaises(ValueError, read_private_token_file, victim, directory)

            token = "a" * 43
            os.symlink(victim, os.path.join(directory, token))
            self.assertRaises(OSError, read_private_token_file, token, directory)


class BackupRequestTests(unittest.TestCase):
    @unittest.skipUnless(
        os.geteuid() == 0 and os.path.exists("/usr/bin/sudo"),
        "requires service-account switching",
    )
    def test_root_scheduler_request_can_be_consumed_by_panel_service(self):
        try:
            pwd.getpwnam("cyberpanel")
        except KeyError:
            self.skipTest("CyberPanel service account is unavailable")

        with tempfile.TemporaryDirectory() as directory:
            token = create_backup_request("example.com", directory)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            code = (
                "from plogical.securityUtils import consume_backup_request; "
                "raise SystemExit(not consume_backup_request("
                "__import__('sys').argv[1], 'example.com', __import__('sys').argv[2]))"
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = project_root
            subprocess.run(
                [
                    "/usr/bin/sudo", "-u", "cyberpanel", "--preserve-env=PYTHONPATH",
                    sys.executable, "-c", code, token, directory,
                ],
                cwd="/",
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_request_is_bound_to_domain_and_consumed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            token = create_backup_request("example.com", directory)

            self.assertFalse(consume_backup_request(token, "other.example", directory))
            self.assertFalse(consume_backup_request(token, "example.com", directory))

            token = create_backup_request("example.com", directory)
            self.assertTrue(consume_backup_request(token, "example.com", directory))
            self.assertFalse(consume_backup_request(token, "example.com", directory))

    def test_tampered_request_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            token, path = create_private_token_file(
                directory,
                json.dumps({"domain": "example.com", "issued": 0}),
            )
            os.chmod(path, 0o600)

            self.assertFalse(consume_backup_request(token, "example.com", directory))


if __name__ == "__main__":
    unittest.main()
