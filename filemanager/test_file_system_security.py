import io
import os
import pwd
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

from plogical.fileSystemSecurity import (
    read_text_file_under,
    safe_extract_archive,
    stage_file_for_download,
)


def cyberpanel_account_available():
    try:
        pwd.getpwnam("cyberpanel")
        return os.geteuid() == 0 and os.path.exists("/usr/bin/sudo")
    except KeyError:
        return False


class SafeFileReadTests(unittest.TestCase):
    def test_staged_download_is_an_immutable_regular_copy(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            source = os.path.join(root, "download.txt")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("first")

            staged = stage_file_for_download(root, source, staging, owner_user=None)
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("second")

            self.assertEqual(os.path.abspath(staging), os.path.dirname(staged))
            self.assertFalse(os.path.islink(staged))
            with open(staged, encoding="utf-8") as handle:
                self.assertEqual("first", handle.read())

    def test_staging_rejects_symlink_source(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            outside = os.path.join(staging, "outside")
            with open(outside, "w", encoding="utf-8") as handle:
                handle.write("private")
            source = os.path.join(root, "link")
            os.symlink(outside, source)

            with self.assertRaises(OSError):
                stage_file_for_download(root, source, staging, owner_user=None)

    def test_read_command_runs_outside_project_directory(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "index.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("hello")
            script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "plogical",
                "safeFileRead.py",
            )

            result = subprocess.run(
                [sys.executable, script, "--allowed-root", root, "--file", path],
                cwd="/",
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual("hello", result.stdout)

    def test_regular_file_can_be_read(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "public_html", "index.txt")
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("hello")

            self.assertEqual("hello", read_text_file_under(root, path))

    def test_final_symlink_and_parent_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            victim = os.path.join(outside, "secret")
            with open(victim, "w", encoding="utf-8") as handle:
                handle.write("secret")

            final_link = os.path.join(root, "final-link")
            os.symlink(victim, final_link)
            with self.assertRaises(OSError):
                read_text_file_under(root, final_link)

            parent_link = os.path.join(root, "parent-link")
            os.symlink(outside, parent_link)
            with self.assertRaises(OSError):
                read_text_file_under(root, os.path.join(parent_link, "secret"))


class SafeArchiveTests(unittest.TestCase):
    @unittest.skipUnless(cyberpanel_account_available(), "requires the CyberPanel service account")
    def test_read_and_extract_run_as_cyberpanel_service_account(self):
        account = pwd.getpwnam("cyberpanel")
        with tempfile.TemporaryDirectory() as directory:
            root = os.path.join(directory, "root")
            destination = os.path.join(root, "public_html")
            os.makedirs(destination)
            source = os.path.join(root, "source.txt")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("service-account-content")
            archive_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.write(source, "source.txt")

            for current_root, directories, files in os.walk(directory):
                os.chown(current_root, account.pw_uid, account.pw_gid)
                os.chmod(current_root, 0o755)
                for name in directories + files:
                    path = os.path.join(current_root, name)
                    os.chown(path, account.pw_uid, account.pw_gid)
            read_script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "plogical",
                "safeFileRead.py",
            )
            extract_script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "plogical",
                "safeArchiveExtraction.py",
            )

            read_result = subprocess.run(
                [
                    "/usr/bin/sudo", "-u", "cyberpanel", sys.executable,
                    read_script, "--allowed-root", root, "--file", source,
                ],
                cwd="/",
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [
                    "/usr/bin/sudo", "-u", "cyberpanel", sys.executable,
                    extract_script, "--allowed-root", root,
                    "--archive", archive_path,
                    "--destination", destination,
                    "--type", "zip",
                ],
                cwd="/",
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual("service-account-content", read_result.stdout)
            with open(os.path.join(destination, "source.txt"), encoding="utf-8") as handle:
                self.assertEqual("service-account-content", handle.read())

    def test_extraction_command_runs_outside_project_directory(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, "public_html")
            os.mkdir(destination)
            archive_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("index.txt", "content")
            script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "plogical",
                "safeArchiveExtraction.py",
            )

            subprocess.run(
                [
                    sys.executable,
                    script,
                    "--allowed-root", root,
                    "--archive", archive_path,
                    "--destination", destination,
                    "--type", "zip",
                ],
                cwd="/",
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            with open(os.path.join(destination, "index.txt"), encoding="utf-8") as handle:
                self.assertEqual("content", handle.read())

    def test_regular_zip_and_tar_files_are_extracted(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, "public_html")
            os.mkdir(destination)

            zip_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("zip-dir/index.txt", "zip-content")
            safe_extract_archive(root, zip_path, destination, "zip")

            tar_path = os.path.join(root, "site.tar.gz")
            with tarfile.open(tar_path, "w:gz") as archive:
                info = tarfile.TarInfo("tar-dir/index.txt")
                content = b"tar-content"
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            safe_extract_archive(root, tar_path, destination, "tar")

            with open(os.path.join(destination, "zip-dir", "index.txt"), encoding="utf-8") as handle:
                self.assertEqual("zip-content", handle.read())
            with open(os.path.join(destination, "tar-dir", "index.txt"), encoding="utf-8") as handle:
                self.assertEqual("tar-content", handle.read())

    def test_zip_symlink_is_rejected_without_writing_target(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, "public_html")
            os.mkdir(destination)
            archive_path = os.path.join(root, "link.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                link = zipfile.ZipInfo("link")
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, "/etc/passwd")

            with self.assertRaises(ValueError):
                safe_extract_archive(root, archive_path, destination, "zip")
            self.assertFalse(os.path.lexists(os.path.join(destination, "link")))

    def test_tar_links_and_path_traversal_are_rejected(self):
        for member_name, member_type in (("link", tarfile.SYMTYPE), ("../escape", tarfile.REGTYPE)):
            with self.subTest(member_name=member_name, member_type=member_type):
                with tempfile.TemporaryDirectory() as root:
                    destination = os.path.join(root, "public_html")
                    os.mkdir(destination)
                    archive_path = os.path.join(root, "bad.tar")
                    with tarfile.open(archive_path, "w") as archive:
                        info = tarfile.TarInfo(member_name)
                        info.type = member_type
                        if member_type == tarfile.SYMTYPE:
                            info.linkname = "/etc/passwd"
                        archive.addfile(info, io.BytesIO(b"") if member_type == tarfile.REGTYPE else None)

                    with self.assertRaises(ValueError):
                        safe_extract_archive(root, archive_path, destination, "tar")

    def test_existing_destination_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            destination = os.path.join(root, "public_html")
            os.mkdir(destination)
            victim = os.path.join(outside, "victim")
            with open(victim, "w", encoding="utf-8") as handle:
                handle.write("preserve")
            os.symlink(outside, os.path.join(destination, "nested"))

            archive_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("nested/victim", "replace")

            with self.assertRaises(OSError):
                safe_extract_archive(root, archive_path, destination, "zip")
            with open(victim, encoding="utf-8") as handle:
                self.assertEqual("preserve", handle.read())

    def test_existing_directory_permissions_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, "public_html")
            private_directory = os.path.join(destination, "private")
            os.makedirs(private_directory, mode=0o700)
            archive_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("private/index.txt", "content")

            safe_extract_archive(root, archive_path, destination, "zip")

            self.assertEqual(0o700, stat.S_IMODE(os.stat(private_directory).st_mode))

    def test_existing_file_permissions_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, "public_html")
            os.mkdir(destination)
            existing = os.path.join(destination, "config.txt")
            with open(existing, "w", encoding="utf-8") as handle:
                handle.write("old")
            os.chmod(existing, 0o600)
            archive_path = os.path.join(root, "site.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("config.txt", "new")

            safe_extract_archive(root, archive_path, destination, "zip")

            self.assertEqual(0o600, stat.S_IMODE(os.stat(existing).st_mode))


if __name__ == "__main__":
    unittest.main()
