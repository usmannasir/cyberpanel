#!/usr/bin/env python3
"""Regression markers for v2.4.9 gap backports into v2.5.5-dev."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8', errors='replace')


def main():
    errors = []

    bm = read('backup/backupManager.py')
    if 'checkOwnership(backupCancellationDomain' not in bm:
        errors.append('backupManager missing cancel ownership check')
    if 'website__domain=backupCancellationDomain' not in bm:
        errors.append('backupManager missing scoped Backups.get')

    inc = read('IncBackups/views.py')
    if 'website__domain=backup_domain' not in inc:
        errors.append('IncBackups missing website__domain scope')
    if 'JobSnapshots' not in inc:
        errors.append('IncBackups missing JobSnapshots import/use')

    fm = read('filemanager/filemanager.py')
    region = fm.split('def fixPermissions')[1].split('\n    def ')[0]
    if "public_html/*'" in region or 'public_html/*"' in region:
        errors.append('filemanager still uses public_html/* chown glob')
    if "chown -R -P %s:%s /home/%s/public_html'" not in region:
        errors.append('filemanager missing recursive public_html chown')

    ssl = read('plogical/sslUtilities.py')
    if 'lswsReloadCmd' not in ssl:
        errors.append('sslUtilities missing lswsReloadCmd')
    if '--reloadcmd' not in ssl:
        errors.append('sslUtilities missing --reloadcmd')
    # reloadcmd must not appear on --issue lines
    for i, line in enumerate(ssl.splitlines(), 1):
        if '--reloadcmd' in line and '--issue' in line:
            errors.append('sslUtilities --reloadcmd incorrectly on --issue line %d' % i)

    acl = read('plogical/acl.py')
    if 'except aliasDomains.DoesNotExist' not in acl:
        errors.append('acl AliasDomainCheck missing DoesNotExist handler')
    if 'PHP 8.5' not in acl:
        errors.append('acl getPHPString missing PHP 8.5')

    vhu = read('plogical/virtualHostUtilities.py')
    if 'Persist the alias in the DB as soon as' not in vhu:
        errors.append('virtualHostUtilities missing early alias save')
    if 'master__domain=masterDomain).delete()' not in vhu:
        errors.append('virtualHostUtilities missing scoped alias delete')

    bu = read('plogical/backupUtilities.py')
    if 'dumpResult = mysqlUtilities.mysqlUtilities.createDatabaseBackup' not in bu:
        errors.append('backupUtilities BackupDatabases missing dumpResult check')

    if errors:
        print('FAIL:')
        for e in errors:
            print(' -', e)
        return 1
    print('PASS: v2.4.9 gap backport markers present')
    return 0


if __name__ == '__main__':
    sys.exit(main())
