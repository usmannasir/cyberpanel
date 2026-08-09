import json
import os
import tempfile
import unittest
from unittest import mock

from cloudAPI.cloudManager import CloudManager
from mailServer.mailserverManager import MailServerManager
from plogical.securityUtils import create_private_token_file


class CloudReportSecurityTests(unittest.TestCase):
    def test_mail_check_worker_and_reader_share_private_report(self):
        with tempfile.TemporaryDirectory() as directory:
            token, report_path = create_private_token_file(directory)
            status_path = os.path.join(directory, "status")
            worker = MailServerManager(
                None,
                "RunServerLevelEmailChecks",
                {"tempStatusPath": status_path, "reportFile": report_path},
            )
            with mock.patch.object(worker, "checkIfMailServerSSLIssued", return_value=1):
                worker.RunServerLevelEmailChecks()
            with mock.patch("cloudAPI.cloudManager.EMAIL_REPORT_DIRECTORY", directory):
                response = CloudManager({"reportFile": token}).ReadReport()

            result = json.loads(response.content)
            self.assertEqual(1, result["status"])
            self.assertEqual({"MailSSL": 1}, json.loads(result["reportContent"]))
            self.assertFalse(os.path.exists(report_path))

    def test_report_reader_accepts_only_private_report_token(self):
        with tempfile.TemporaryDirectory() as directory:
            token, path = create_private_token_file(directory, '{"MailSSL": 1}')
            with mock.patch("cloudAPI.cloudManager.EMAIL_REPORT_DIRECTORY", directory):
                response = CloudManager({"reportFile": token}).ReadReport()
                result = json.loads(response.content)
                self.assertEqual(1, result["status"])
                self.assertEqual('{"MailSSL": 1}', result["reportContent"])

                response = CloudManager({"reportFile": path}).ReadReport()
                self.assertEqual(0, json.loads(response.content)["status"])

    def test_check_returns_opaque_report_token(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch("cloudAPI.cloudManager.EMAIL_REPORT_DIRECTORY", directory), \
                mock.patch("cloudAPI.cloudManager.MailServerManager") as manager:
            response = CloudManager().RunServerLevelEmailChecks()
            result = json.loads(response.content)

            self.assertEqual(1, result["status"])
            self.assertNotIn("/", result["reportFile"])
            report_path = manager.call_args.args[2]["reportFile"]
            self.assertEqual(os.path.join(directory, result["reportFile"]), report_path)


if __name__ == "__main__":
    unittest.main()
