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


class FileDownloadSpecialCharacterTests(unittest.TestCase):
    """Issue #1902: downloads failed with "Unauthorized access" for any file
    whose name contained '#', '&', '+' or '%'.

    Two defects combined. The file manager built the URL by string
    concatenation with no encodeURIComponent, so '#' was cut off as a URL
    fragment and '&' started a new query parameter. And the view decoded
    request.GET a second time with unquote(), so a correctly-encoded '%' was
    decoded twice into something else. Either way the path reaching the
    filesystem was not the one the user clicked.

    These tests cover the server half: a properly encoded request must reach
    the view as the exact original path.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.seen = []

    def make_request(self, file_path, domain="example.com"):
        # RequestFactory encodes the query string the way a correct client
        # would, so this exercises the same path a browser produces.
        request = self.factory.get(
            "/filemanager/downloadFile",
            {"fileToDownload": file_path, "domainName": domain},
        )
        request.session = {"userID": 1}
        return request

    def common_patches(self, recorder):
        return (
            mock.patch(
                "filemanager.views.Administrator.objects.get",
                return_value=SimpleNamespace(pk=1),
            ),
            mock.patch("filemanager.views.ACLManager.loadedACL", return_value={"admin": 0}),
            mock.patch("filemanager.views.ACLManager.checkOwnership", return_value=1),
            mock.patch("filemanager.views.os.path.isfile", side_effect=recorder),
        )

    class _Reached(Exception):
        """Raised from the isfile probe to stop the view once the path is
        known, so the test does not have to mock the staging machinery."""

    def _path_reaching_filesystem(self, file_path):
        """Return the path the view actually resolved, or None if refused."""
        seen = []

        def recorder(path):
            seen.append(path)
            raise self._Reached()

        patches = self.common_patches(recorder)
        for p in patches:
            p.start()
        try:
            with mock.patch("filemanager.views.os.path.realpath",
                            side_effect=lambda p: p):
                try:
                    downloadFile(self.make_request(file_path))
                except Exception:
                    pass
        finally:
            for p in patches:
                p.stop()
        return seen[0] if seen else None

    def test_hash_in_filename_survives(self):
        path = "/home/example.com/public_html/report#1.txt"
        self.assertEqual(self._path_reaching_filesystem(path), path)

    def test_ampersand_in_filename_survives(self):
        path = "/home/example.com/public_html/tom&jerry.txt"
        self.assertEqual(self._path_reaching_filesystem(path), path)

    def test_plus_in_filename_survives(self):
        path = "/home/example.com/public_html/c++notes.txt"
        self.assertEqual(self._path_reaching_filesystem(path), path)

    def test_literal_percent_is_not_double_decoded(self):
        """The regression the extra unquote() caused: '100%20off.txt' became
        '100 off.txt', a file that does not exist."""
        path = "/home/example.com/public_html/100%20off.txt"
        self.assertEqual(self._path_reaching_filesystem(path), path)

    def test_space_in_filename_survives(self):
        path = "/home/example.com/public_html/my report.txt"
        self.assertEqual(self._path_reaching_filesystem(path), path)

    def test_traversal_is_still_refused(self):
        """The encoding fix must not weaken the traversal check."""
        response = None
        patches = self.common_patches(lambda p: True)
        [p.start() for p in patches]
        try:
            response = downloadFile(
                self.make_request("/home/example.com/../../etc/shadow"))
        finally:
            for p in patches:
                p.stop()
        self.assertIn(b"Unauthorized access", response.content)

    def test_path_outside_home_is_refused(self):
        patches = self.common_patches(lambda p: True)
        [p.start() for p in patches]
        try:
            response = downloadFile(self.make_request("/etc/shadow"))
        finally:
            for p in patches:
                p.stop()
        self.assertIn(b"Unauthorized access", response.content)
