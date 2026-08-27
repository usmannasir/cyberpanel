BACKUP_ARCHIVE_SUFFIX = '.tar.gz'


def archive_path_without_suffix(path):
    if path.endswith(BACKUP_ARCHIVE_SUFFIX):
        return path[:-len(BACKUP_ARCHIVE_SUFFIX)]
    return path
