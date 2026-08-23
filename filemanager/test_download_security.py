import io
import os
import shlex
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory

from filemanager.views import RootDownloadFile, downloadFile
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
        )

    def test_download_uses_private_staged_copy(self):
        staged = os.path.join(FILE_DOWNLOAD_DIRECTORY, "a" * 43)
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, staged),
                ) as executioner, \
                mock.patch(
                    "filemanager.views._openStagedFile",
                    return_value=io.BytesIO(b"download"),
                ), \
                mock.patch("filemanager.views.threading.Timer") as timer:
            response = downloadFile(self.make_request())

        self.assertTrue(response.streaming)
        self.assertNotIn("X-LiteSpeed-Location", response)
        self.assertIn("file.txt", response["Content-Disposition"])
        self.assertIn("stageFileDownload.py", executioner.call_args.args[0])
        timer.return_value.start.assert_called_once_with()

    def test_download_fails_closed_when_staging_output_is_invalid(self):
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, "/home/example.com/public_html/file.txt"),
                ):
            response = downloadFile(self.make_request())

        self.assertNotIn("X-LiteSpeed-Location", response)
        self.assertIn(b"Unable to stage file securely", response.content)

    def test_download_does_not_require_wsgi_file_access(self):
        staged = os.path.join(FILE_DOWNLOAD_DIRECTORY, "b" * 43)
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], \
                mock.patch(
                    "filemanager.views.os.path.isfile",
                    side_effect=AssertionError("WSGI worker must not probe site files"),
                ), \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, staged),
                ), \
                mock.patch(
                    "filemanager.views._openStagedFile",
                    return_value=io.BytesIO(b"download"),
                ), \
                mock.patch("filemanager.views.threading.Timer"):
            response = downloadFile(self.make_request())

        self.assertTrue(response.streaming)


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

    def common_patches(self):
        return (
            mock.patch(
                "filemanager.views.Administrator.objects.get",
                return_value=SimpleNamespace(pk=1),
            ),
            mock.patch("filemanager.views.ACLManager.loadedACL", return_value={"admin": 0}),
            mock.patch("filemanager.views.ACLManager.checkOwnership", return_value=1),
        )

    class _Reached(Exception):
        """Raised once the path reaches the privileged staging boundary."""

    def _path_reaching_stager(self, file_path):
        """Return the path sent to the privileged stager, or None if refused."""
        seen = []

        def recorder(command, **unused_kwargs):
            arguments = shlex.split(command)
            seen.append(arguments[arguments.index("--file") + 1])
            raise self._Reached()

        patches = self.common_patches()
        for p in patches:
            p.start()
        try:
            with mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    side_effect=recorder):
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
        self.assertEqual(self._path_reaching_stager(path), path)

    def test_ampersand_in_filename_survives(self):
        path = "/home/example.com/public_html/tom&jerry.txt"
        self.assertEqual(self._path_reaching_stager(path), path)

    def test_plus_in_filename_survives(self):
        path = "/home/example.com/public_html/c++notes.txt"
        self.assertEqual(self._path_reaching_stager(path), path)

    def test_literal_percent_is_not_double_decoded(self):
        """The regression the extra unquote() caused: '100%20off.txt' became
        '100 off.txt', a file that does not exist."""
        path = "/home/example.com/public_html/100%20off.txt"
        self.assertEqual(self._path_reaching_stager(path), path)

    def test_literal_percent_is_preserved_in_download_name(self):
        staged = os.path.join(FILE_DOWNLOAD_DIRECTORY, "d" * 43)
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, staged),
                ), \
                mock.patch(
                    "filemanager.views._openStagedFile",
                    return_value=io.BytesIO(b"download"),
                ), \
                mock.patch("filemanager.views.threading.Timer"):
            response = downloadFile(self.make_request(
                "/home/example.com/public_html/100%20off.txt"))

        self.assertIn(
            "filename*=UTF-8''100%2520off.txt",
            response["Content-Disposition"],
        )

    def test_space_in_filename_survives(self):
        path = "/home/example.com/public_html/my report.txt"
        self.assertEqual(self._path_reaching_stager(path), path)

    def test_deployable_file_manager_encodes_download_query(self):
        script_path = (
            Path(__file__).resolve().parent
            / "static/filemanager/js/fileManager.js"
        )
        script = script_path.read_text(encoding="utf-8")
        self.assertIn("encodeURIComponent(domainName)", script)
        self.assertGreaterEqual(
            script.count("encodeURIComponent(downloadURL)"),
            2,
        )
        self.assertNotIn(
            "getElementsByTagName('td')[0].innerHTML",
            script,
        )
        self.assertIn(
            "getElementsByTagName('td')[0].textContent",
            script,
        )

    def test_traversal_is_still_refused(self):
        """The encoding fix must not weaken the traversal check."""
        response = None
        patches = self.common_patches()
        [p.start() for p in patches]
        try:
            response = downloadFile(
                self.make_request("/home/example.com/../../etc/shadow"))
        finally:
            for p in patches:
                p.stop()
        self.assertIn(b"Unauthorized access", response.content)

    def test_path_outside_home_is_refused(self):
        patches = self.common_patches()
        [p.start() for p in patches]
        try:
            response = downloadFile(self.make_request("/etc/shadow"))
        finally:
            for p in patches:
                p.stop()
        self.assertIn(b"Unauthorized access", response.content)


class RootFileDownloadSecurityTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def make_request(self, file_path):
        request = self.factory.get(
            "/filemanager/RootDownloadFile",
            {"fileToDownload": file_path},
        )
        request.session = {"userID": 1}
        return request

    def test_root_download_also_uses_private_staging(self):
        staged = os.path.join(FILE_DOWNLOAD_DIRECTORY, "c" * 43)
        with mock.patch(
                "filemanager.views.ACLManager.loadedACL",
                return_value={"admin": 1}), \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                    return_value=(1, staged),
                ) as executioner, \
                mock.patch(
                    "filemanager.views._openStagedFile",
                    return_value=io.BytesIO(b"download"),
                ), \
                mock.patch("filemanager.views.threading.Timer"):
            response = RootDownloadFile(self.make_request("/home/example.txt"))

        self.assertTrue(response.streaming)
        self.assertNotIn("X-LiteSpeed-Location", response)
        arguments = shlex.split(executioner.call_args.args[0])
        self.assertEqual(arguments[arguments.index("--allowed-root") + 1], "/")
        self.assertEqual(arguments[arguments.index("--file") + 1], "/home/example.txt")

    def test_root_download_keeps_sensitive_paths_blocked(self):
        with mock.patch(
                "filemanager.views.ACLManager.loadedACL",
                return_value={"admin": 1}), \
                mock.patch(
                    "filemanager.views.ProcessUtilities.outputExecutioner",
                ) as executioner:
            response = RootDownloadFile(self.make_request("/etc/shadow"))

        executioner.assert_not_called()
        self.assertIn(b"Access to system files denied", response.content)
