SITE_BACKUP_DIRECTORIES = (
    'logs',
    'backup',
    'incbackup',
    'incrementalbackups',
)

# These rsync patterns have no slash or wildcard: they exclude matching file or
# directory basenames at every depth, including .wp-cli and lscache.
SITE_BACKUP_EXCLUDED_NAMES = ('.wp-cli',) + SITE_BACKUP_DIRECTORIES + ('lscache',)


def rsync_exclude_arguments():
    return ' '.join('--exclude=%s' % name for name in SITE_BACKUP_EXCLUDED_NAMES)
