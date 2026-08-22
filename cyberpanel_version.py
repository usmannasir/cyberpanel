VERSION = '3.0'
BUILD = 4
FULL_VERSION = '%s.%s' % (VERSION, BUILD)


def _version_tuple(version, build):
    version_parts = str(version).split('.')
    if len(version_parts) < 2:
        raise ValueError('Version must contain major and minor components.')
    return int(version_parts[0]), int(version_parts[1]), int(build)


def version_at_least(version, build, minimum_version, minimum_build=0):
    try:
        return _version_tuple(version, build) >= _version_tuple(
            minimum_version, minimum_build
        )
    except (TypeError, ValueError):
        return False


def backup_uses_database_users_schema(version, build):
    """Return whether a backup uses the multi-user database metadata schema."""
    try:
        major, minor, build_number = _version_tuple(version, build)
    except (TypeError, ValueError):
        return False

    major_minor = (major, minor)
    if major_minor >= (2, 4):
        return True

    return major_minor in ((2, 1), (2, 3)) and build_number >= 1


def backup_uses_full_directory_layout(version, build):
    try:
        major, minor, build_number = _version_tuple(version, build)
    except (TypeError, ValueError):
        return False
    return (major, minor) > (2, 0) or build_number > 0
