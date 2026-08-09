import contextlib
import fcntl
import os
import posixpath
import stat
import tarfile
import zipfile

from plogical.securityUtils import (
    FILE_DOWNLOAD_DIRECTORY,
    create_private_token_file,
    remove_stale_private_token_files,
)


MAX_ARCHIVE_MEMBERS = 200000
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024 * 1024
FICLONE = 0x40049409


def _path_parts_under(root, path):
    if not isinstance(path, str) or "\x00" in path:
        raise ValueError("Invalid path")
    root = os.path.abspath(root)
    path = os.path.abspath(path)
    if os.path.commonpath([root, path]) != root:
        raise ValueError("Path is outside the allowed root")
    relative = os.path.relpath(path, root)
    if relative == ".":
        return []
    parts = relative.split(os.sep)
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid path component")
    return parts


def _directory_flags():
    return os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW


def _open_directory_under(root, path):
    parts = _path_parts_under(root, path)
    descriptor = os.open(os.path.abspath(root), _directory_flags())
    try:
        for part in parts:
            next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextlib.contextmanager
def _open_regular_file_under(root, path):
    parts = _path_parts_under(root, path)
    if not parts:
        raise ValueError("A regular file is required")
    parent = os.path.dirname(os.path.abspath(path))
    parent_fd = _open_directory_under(root, parent)
    try:
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise OSError("A regular file is required")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            yield handle
    finally:
        os.close(descriptor)


def read_text_file_under(root, path, max_bytes=16 * 1024 * 1024):
    with _open_regular_file_under(root, path) as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError("File is too large to edit")
    return content.decode("utf-8", errors="replace")


def _copy_file_descriptors(source_fd, destination_fd):
    try:
        fcntl.ioctl(destination_fd, FICLONE, source_fd)
        return
    except OSError:
        os.ftruncate(destination_fd, 0)
        os.lseek(source_fd, 0, os.SEEK_SET)
        os.lseek(destination_fd, 0, os.SEEK_SET)

    while True:
        chunk = os.read(source_fd, 1024 * 1024)
        if not chunk:
            break
        view = memoryview(chunk)
        while view:
            written = os.write(destination_fd, view)
            view = view[written:]


def stage_file_for_download(
        allowed_root,
        source_path,
        staging_directory=FILE_DOWNLOAD_DIRECTORY,
        owner_user="cyberpanel"):
    remove_stale_private_token_files(staging_directory, 3600)
    token, staged_path = create_private_token_file(
        staging_directory,
        owner_user=owner_user,
    )
    try:
        with _open_regular_file_under(allowed_root, source_path) as source:
            destination_fd = os.open(
                staged_path,
                os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            )
            try:
                destination_status = os.fstat(destination_fd)
                if (not stat.S_ISREG(destination_status.st_mode)
                        or destination_status.st_nlink != 1):
                    raise OSError("Invalid staged download file")
                _copy_file_descriptors(source.fileno(), destination_fd)
                os.fchmod(destination_fd, 0o600)
            finally:
                os.close(destination_fd)
        return staged_path
    except BaseException:
        try:
            os.unlink(staged_path)
        except FileNotFoundError:
            pass
        raise


def _archive_member_parts(name):
    if not isinstance(name, str) or "\x00" in name:
        raise ValueError("Invalid archive member")
    name = name.replace("\\", "/")
    if name.startswith("/") or name.startswith("//"):
        raise ValueError("Absolute archive paths are not allowed")
    raw_parts = name.split("/")
    if any(part == ".." for part in raw_parts):
        raise ValueError("Archive path traversal is not allowed")
    normalized = posixpath.normpath(name)
    if normalized in ("", "."):
        return []
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid archive path")
    if ":" in parts[0]:
        raise ValueError("Archive drive paths are not allowed")
    return parts


def _safe_file_mode(mode):
    return 0o644 | (mode & 0o111)


def _ensure_directories(root_fd, parts):
    descriptor = os.dup(root_fd)
    try:
        for part in parts:
            created = False
            try:
                os.mkdir(part, 0o755, dir_fd=descriptor)
                created = True
            except FileExistsError:
                pass
            next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            if created:
                os.fchmod(next_descriptor, 0o755)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _write_member(root_fd, parts, source, mode):
    if not parts:
        raise ValueError("Invalid archive file path")
    parent_fd = _ensure_directories(root_fd, parts[:-1])
    try:
        created = False
        try:
            descriptor = os.open(
                parts[-1],
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                _safe_file_mode(mode),
                dir_fd=parent_fd,
            )
            created = True
        except FileExistsError:
            descriptor = os.open(
                parts[-1],
                os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
        try:
            file_status = os.fstat(descriptor)
            if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
                raise OSError("Archive destination is not a private regular file")
            destination_mode = (
                _safe_file_mode(mode)
                if created
                else stat.S_IMODE(file_status.st_mode)
            )
            os.ftruncate(descriptor, 0)
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                view = memoryview(chunk)
                while view:
                    written = os.write(descriptor, view)
                    view = view[written:]
            os.fchmod(descriptor, destination_mode)
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_fd)


def _validate_archive_limits(members, size_getter):
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ValueError("Archive contains too many entries")
    total_size = 0
    for member in members:
        size = size_getter(member)
        if size < 0:
            raise ValueError("Archive entry has an invalid size")
        total_size += size
        if total_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Archive is too large to extract")


def _extract_zip(source, destination_fd):
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        _validate_archive_limits(members, lambda member: member.file_size)
        validated = []
        for member in members:
            parts = _archive_member_parts(member.filename)
            mode = member.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if file_type == stat.S_IFLNK:
                raise ValueError("Archive links are not allowed")
            if not member.is_dir() and file_type not in (0, stat.S_IFREG):
                raise ValueError("Special archive entries are not allowed")
            validated.append((member, parts, mode))

        for member, parts, mode in validated:
            if not parts:
                continue
            if member.is_dir():
                directory_fd = _ensure_directories(destination_fd, parts)
                os.close(directory_fd)
                continue
            with archive.open(member, "r") as member_source:
                _write_member(destination_fd, parts, member_source, mode)


def _extract_tar(source, destination_fd):
    with tarfile.open(fileobj=source, mode="r:*") as archive:
        members = archive.getmembers()
        _validate_archive_limits(members, lambda member: member.size)
        validated = []
        for member in members:
            parts = _archive_member_parts(member.name)
            if not member.isdir() and not member.isfile():
                raise ValueError("Archive links and special entries are not allowed")
            validated.append((member, parts))

        for member, parts in validated:
            if not parts:
                continue
            if member.isdir():
                directory_fd = _ensure_directories(destination_fd, parts)
                os.close(directory_fd)
                continue
            member_source = archive.extractfile(member)
            if member_source is None:
                raise ValueError("Unable to read archive entry")
            with member_source:
                _write_member(destination_fd, parts, member_source, member.mode)


def safe_extract_archive(allowed_root, archive_path, destination, archive_type):
    destination_fd = _open_directory_under(allowed_root, destination)
    try:
        with _open_regular_file_under(allowed_root, archive_path) as source:
            if archive_type == "zip":
                _extract_zip(source, destination_fd)
            elif archive_type in ("tar", "tar.gz", "tgz"):
                _extract_tar(source, destination_fd)
            else:
                raise ValueError("Unsupported archive type")
    finally:
        os.close(destination_fd)
