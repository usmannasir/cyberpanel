import copy
import os
import sys
import tarfile
import time


class UnsafeArchiveError(tarfile.TarError):
    """Raised when an archive member could escape its extraction directory."""


def _path_is_within(parent, candidate):
    try:
        return os.path.commonpath((parent, candidate)) == parent
    except ValueError:
        return False


def _resolved_archive_path(destination, member_name):
    if not member_name or os.path.isabs(member_name):
        raise UnsafeArchiveError('Archive contains an unsafe path: %s' % member_name)

    member_path = os.path.realpath(os.path.join(destination, member_name))
    if not _path_is_within(destination, member_path):
        raise UnsafeArchiveError('Archive path escapes the restore directory: %s' % member_name)
    return member_path


def _validate_archive_member(destination, member):
    member_path = _resolved_archive_path(destination, member.name)

    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
        raise UnsafeArchiveError('Archive contains an unsupported entry: %s' % member.name)

    if member.issym():
        if not member.linkname or os.path.isabs(member.linkname):
            raise UnsafeArchiveError('Archive contains an unsafe link: %s' % member.name)
        link_path = os.path.realpath(os.path.join(os.path.dirname(member_path), member.linkname))
        if not _path_is_within(destination, link_path):
            raise UnsafeArchiveError('Archive link escapes the restore directory: %s' % member.name)
    elif member.islnk():
        if not member.linkname or os.path.isabs(member.linkname):
            raise UnsafeArchiveError('Archive contains an unsafe link: %s' % member.name)
        link_path = os.path.realpath(os.path.join(destination, member.linkname))
        if not _path_is_within(destination, link_path):
            raise UnsafeArchiveError('Archive link escapes the restore directory: %s' % member.name)


def _portable_data_members(members):
    """Apply the ownership and mode protections used by Python's data filter."""
    safe_members = []
    for member in members:
        safe_member = copy.copy(member)
        safe_member.uid = None
        safe_member.gid = None
        safe_member.uname = None
        safe_member.gname = None
        safe_member.mode &= 0o777
        safe_members.append(safe_member)
    return safe_members


def safe_extract(archive, destination):
    """Extract a backup without allowing archive members to escape destination."""
    os.makedirs(destination, exist_ok=True)
    destination = os.path.realpath(destination)
    members = archive.getmembers()

    for member in members:
        _validate_archive_member(destination, member)

    if sys.version_info >= (3, 12):
        try:
            archive.extractall(destination, members=members, filter='data')
        except tarfile.FilterError as error:
            raise UnsafeArchiveError(str(error))
    else:
        archive.extractall(destination, members=_portable_data_members(members))


def archive_is_valid(archive_path):
    """Read every archive header so truncated or malformed backups fail."""
    try:
        with tarfile.open(archive_path, mode='r:*') as archive:
            for _member in archive:
                pass
        return True
    except (OSError, EOFError, tarfile.TarError):
        return False


def archive_is_ready(archive_path, settle_seconds=10, max_wait_seconds=300, stable_checks=3):
    """Wait for a non-empty archive whose size has stopped changing."""
    if not archive_path or stable_checks < 1 or settle_seconds <= 0:
        return False

    checks = max(1, int(max_wait_seconds / settle_seconds) + 1)
    previous_size = None
    stable_count = 0

    for check_number in range(checks):
        try:
            current_size = os.path.getsize(archive_path) if os.path.exists(archive_path) else 0
        except OSError:
            current_size = 0

        if current_size > 0 and current_size == previous_size:
            stable_count += 1
        elif current_size > 0:
            stable_count = 1
        else:
            stable_count = 0

        if stable_count >= stable_checks:
            return archive_is_valid(archive_path)

        previous_size = current_size
        if check_number + 1 < checks:
            time.sleep(settle_seconds)

    return False


def resolve_archive_path(virtual_host, temp_storage_path, file_name):
    candidates = []
    if temp_storage_path:
        candidates.append(temp_storage_path + '.tar.gz')
    if file_name and file_name != 'Fetching..':
        archive_name = str(file_name).strip()
        if not archive_name.endswith('.tar.gz'):
            archive_name += '.tar.gz'
        if os.path.basename(archive_name) == archive_name:
            candidates.append(os.path.join('/home', virtual_host, 'backup', archive_name))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0] if candidates else None
