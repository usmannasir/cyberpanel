import io
import os
import shlex
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from plogical.archiveExtractionJobs import (
    build_archive_extraction_command,
    create_archive_extraction_job,
    get_archive_extraction_status,
    run_archive_extraction_job,
)


class ArchiveExtractionJobTests(unittest.TestCase):

    def test_file_manager_polls_background_extraction_status(self):
        project_root = Path(__file__).parent.parent
        paths = [
            Path(__file__).parent / 'static' / 'filemanager' / 'js' / 'fileManager.js',
        ]
        optional_deployed_paths = (
            project_root / 'static' / 'filemanager' / 'js' / 'fileManager.js',
            project_root / 'public' / 'static' / 'filemanager' / 'js' / 'fileManager.js',
        )
        paths.extend(path for path in optional_deployed_paths if path.exists())
        for javascript_path in paths:
            with self.subTest(javascript_path=javascript_path):
                source = javascript_path.read_text(encoding='utf-8')
                self.assertIn(
                    "fileManager.controller('fileManagerCtrl', function ($scope, $http, FileUploader, $window, $timeout)",
                    source,
                )
                self.assertIn("method: 'extractStatus'", source)
                self.assertIn('$timeout(poll, 2000)', source)
                self.assertIn("return 'tar.gz'", source)
                self.assertIn("return 'tar'", source)
                self.assertIn("return 'tgz'", source)

    def test_systemd_command_keeps_paths_as_single_arguments(self):
        destination = '/home/example.com/public_html; touch /tmp/not-run'
        command = build_archive_extraction_command(
            token='a' * 43,
            status_path='/home/cyberpanel/.file-extractions/' + ('a' * 43),
            allowed_root='/home/example.com',
            archive_path='/home/example.com/site backup.tar',
            destination=destination,
            archive_type='tar',
            run_as='example_user',
        )

        arguments = shlex.split(command)
        self.assertEqual(destination, arguments[arguments.index('--destination') + 1])
        self.assertNotIn('touch', arguments)

    def test_status_is_bound_to_panel_user_and_domain(self):
        with tempfile.TemporaryDirectory() as status_directory:
            token, unused_path = create_archive_extraction_job(
                17,
                'example.com',
                directory=status_directory,
                owner_user=None,
            )

            status = get_archive_extraction_status(
                token, 17, 'example.com', directory=status_directory
            )
            self.assertEqual('queued', status['state'])

            with self.assertRaises(PermissionError):
                get_archive_extraction_status(
                    token, 18, 'example.com', directory=status_directory
                )
            with self.assertRaises(PermissionError):
                get_archive_extraction_status(
                    token, 17, 'other.example.com', directory=status_directory
                )

    def test_worker_extracts_archive_and_records_success(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as status_directory:
            destination = os.path.join(root, 'public_html')
            os.mkdir(destination)
            archive_path = os.path.join(root, 'site.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as archive:
                content = b'large archive extraction'
                info = tarfile.TarInfo('site/index.txt')
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

            token, status_path = create_archive_extraction_job(
                17,
                'example.com',
                directory=status_directory,
                owner_user=None,
            )
            result = run_archive_extraction_job(
                token=token,
                status_path=status_path,
                allowed_root=root,
                archive_path=archive_path,
                destination=destination,
                archive_type='tar.gz',
                run_as=None,
                python_path=sys.executable,
            )

            self.assertTrue(result)
            with open(os.path.join(destination, 'site', 'index.txt'), encoding='utf-8') as extracted:
                self.assertEqual('large archive extraction', extracted.read())
            status = get_archive_extraction_status(
                token, 17, 'example.com', directory=status_directory
            )
            self.assertEqual('completed', status['state'])

    def test_worker_records_a_safe_failure_for_rejected_archive(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as status_directory:
            destination = os.path.join(root, 'public_html')
            os.mkdir(destination)
            archive_path = os.path.join(root, 'unsafe.tar')
            with tarfile.open(archive_path, 'w') as archive:
                content = b'escape'
                info = tarfile.TarInfo('../outside.txt')
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

            token, status_path = create_archive_extraction_job(
                17,
                'example.com',
                directory=status_directory,
                owner_user=None,
            )
            result = run_archive_extraction_job(
                token=token,
                status_path=status_path,
                allowed_root=root,
                archive_path=archive_path,
                destination=destination,
                archive_type='tar',
                run_as=None,
                python_path=sys.executable,
            )

            self.assertFalse(result)
            self.assertFalse(os.path.exists(os.path.join(root, 'outside.txt')))
            status = get_archive_extraction_status(
                token, 17, 'example.com', directory=status_directory
            )
            self.assertEqual('failed', status['state'])
            self.assertIn('rejected or failed', status['message'])


if __name__ == '__main__':
    unittest.main()
