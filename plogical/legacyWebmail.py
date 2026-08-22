import os


LEGACY_DATA_PATHS = (
    '/usr/local/lscp/cyberpanel/snappymail/data',
    '/usr/local/lscp/cyberpanel/rainloop/data',
)


def legacy_data_permission_commands():
    """Return hardening commands only for legacy data already on disk."""
    for data_path in LEGACY_DATA_PATHS:
        if not os.path.isdir(data_path):
            continue
        yield 'chown -R lscpd:lscpd %s' % data_path
        yield 'find %s -type d -exec chmod 700 {} \\;' % data_path
        yield 'find %s -type f -exec chmod 600 {} \\;' % data_path
