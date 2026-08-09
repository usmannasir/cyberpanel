SITE_BACKUP_DIRECTORIES = (
    'logs',
    'backup',
    'incbackup',
    'incrementalbackups',
)


def rsync_exclude_arguments():
    directories = ('.wp-cli',) + SITE_BACKUP_DIRECTORIES + ('lscache',)
    return ' '.join('--exclude=%s' % directory for directory in directories)
