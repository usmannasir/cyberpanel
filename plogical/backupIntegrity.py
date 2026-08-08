import os
import tarfile
import time


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
