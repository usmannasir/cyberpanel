import json
import unittest
from unittest import mock

from django.test import RequestFactory

from backup.views import localInitiate


class InternalBackupRequestTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_invalid_token_does_not_start_backup(self):
        request = self.factory.post(
            "/backup/localInitiate",
            data=json.dumps({"randomFile": "invalid", "websiteToBeBacked": "example.com"}),
            content_type="application/json",
        )
        with mock.patch("backup.views.consume_backup_request", return_value=False), \
                mock.patch("backup.views.BackupManager") as manager:
            response = localInitiate(request)
            result = json.loads(response.content)

        self.assertEqual(0, result["status"])
        self.assertEqual(403, response.status_code)
        manager.assert_not_called()

    def test_valid_token_starts_bound_backup(self):
        body = {"randomFile": "a" * 43, "websiteToBeBacked": "example.com"}
        request = self.factory.post(
            "/backup/localInitiate",
            data=json.dumps(body),
            content_type="application/json",
        )
        expected = mock.Mock()
        with mock.patch("backup.views.consume_backup_request", return_value=True), \
                mock.patch("backup.views.BackupManager") as manager:
            manager.return_value.submitBackupCreation.return_value = expected
            response = localInitiate(request)

        self.assertIs(expected, response)
        manager.return_value.submitBackupCreation.assert_called_once_with(1, body)


if __name__ == "__main__":
    unittest.main()
