import os
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory

from filemanager.views import downloadFile
from plogical.securityUtils import FILE_DOWNLOAD_DIRECTORY


class FileDownloadSecurityTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def make_request(self):
        request = self.factory.get(
            "/filemanager/downloadFile",
            {
                "fileToDownload": "/home/example.com/public_html/file.txt",
                "domainName": "example.com",
            },
        )
        request.session = {"userID": 1}
        return request

    def common_patches(self):
        return (
            mock.patch(
                "filemanager.views.Administrator.objects.get",
                return_value=SimpleNamespace(pk=1),
            ),
            mock.patch("filemanager.views.ACLManager.loadedACL", return_value={"admin": 0}),
            mock.patch("filemanager.views.ACLManager.checkOwnership", return_value=1),
            mock.patch("filemanager.views.os.path.isfile", return_value=True),
        )

    def test_download_uses_private_staged_copy(self):
        staged = os.path.join(FILE_DOWNLOAD_DIRECTORY, "a" * 43)
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], patches[3], \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, staged),
                ) as executioner, \
                mock.patch("filemanager.views.threading.Timer") as timer:
            response = downloadFile(self.make_request())

        self.assertEqual(staged, response["X-LiteSpeed-Location"])
        self.assertNotEqual(
            "/home/example.com/public_html/file.txt",
            response["X-LiteSpeed-Location"],
        )
        self.assertIn("stageFileDownload.py", executioner.call_args.args[0])
        timer.return_value.start.assert_called_once_with()

    def test_download_fails_closed_when_staging_output_is_invalid(self):
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], patches[3], \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, "/home/example.com/public_html/file.txt"),
                ):
            response = downloadFile(self.make_request())

        self.assertNotIn("X-LiteSpeed-Location", response)
        self.assertIn(b"Unable to stage file securely", response.content)


if __name__ == "__main__":
    unittest.main()
