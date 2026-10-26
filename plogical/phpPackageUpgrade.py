"""Upgrade existing optional PHP packages without reinstalling removed branches."""
import os
import re
import shutil
import subprocess


_PACKAGE = re.compile(r'^lsphp[0-9]{2}(?:-[A-Za-z0-9+_.-]+)?$')


def installed_php_upgrade_command(manager=None):
    """Build an exact installed-package transaction; do not expand branch globs."""
    manager = manager or ('apt-get' if shutil.which('apt-get') else
                          'dnf' if shutil.which('dnf') else
                          'yum' if shutil.which('yum') else None)
    if manager == 'apt-get':
        output = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Package}\t${db:Status-Status}\n'],
            universal_newlines=True)
        packages = [fields[0] for line in output.splitlines()
                    for fields in [line.split('\t')]
                    if len(fields) == 2 and fields[1] == 'installed' and _PACKAGE.fullmatch(fields[0])]
        prefix = ['apt-get', '-y', '--no-remove', '--only-upgrade', 'install']
    elif manager in ('dnf', 'yum'):
        output = subprocess.check_output(['rpm', '-qa', '--qf', '%{NAME}\n'],
                                         universal_newlines=True)
        packages = [name for name in output.splitlines() if _PACKAGE.fullmatch(name)]
        prefix = [manager, '-y', 'update']
    else:
        raise RuntimeError('No supported package manager found for installed PHP updates.')
    # A leftover extension/development package must not pull a removed runtime
    # back in through a newly introduced package dependency.
    bases = {name for name in packages if re.fullmatch(r'lsphp[0-9]{2}', name)}
    packages = sorted({name for name in packages if name.split('-', 1)[0] in bases})
    return prefix + packages if packages else []


def upgrade_installed_php():
    command = installed_php_upgrade_command()
    if command:
        environment = os.environ.copy()
        environment['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.run(command, check=True, env=environment)
    return command
