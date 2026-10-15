"""Fail closed before optional Sieve setup can disrupt an existing mail service."""
import os
from pathlib import Path
import subprocess


def prepare_sieve_upgrade(log):
    """Install optional packages before editing configuration; never switch providers."""
    baseline = subprocess.run(['doveconf', '-n'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE)
    if baseline.returncode:
        log('Skipping Sieve setup: existing Dovecot configuration is invalid; '
            'repair it before enabling optional filtering.', 0)
        return False
    version = subprocess.run(['dovecot', '--version'], capture_output=True, text=True)
    if version.returncode or version.stdout.strip().startswith('2.4.'):
        log('Skipping legacy Sieve setup: this Dovecot runtime requires a '
            'version-specific configuration; existing configuration is unchanged.', 0)
        return False
    if os.path.exists('/etc/debian_version') or os.path.exists('/etc/lsb-release'):
        command = ['apt-get', 'install', '-y', 'dovecot-sieve', 'dovecot-managesieved']
    else:
        provider = subprocess.run(
            ['rpm', '-qf', '/usr/sbin/dovecot', '--qf', '%{NAME}\n%{RELEASE}\n%{VENDOR}\n'],
            capture_output=True, text=True)
        details = provider.stdout.strip().splitlines()
        vendors = ('almalinux', 'rocky', 'red hat', 'centos', 'oracle', 'cloudlinux', 'fedora')
        if (provider.returncode or len(details) != 3 or details[0] != 'dovecot'
                or '.gf.' in details[1].lower()
                or not any(v in details[2].lower() for v in vendors)):
            log('Skipping Sieve setup: third-party or unknown Dovecot package provider. '
                'Use matching Dovecot/Pigeonhole packages in a backed-up maintenance '
                'window; automatic provider migration is not attempted.', 0)
            return False
        command = ['dnf', 'install', '-y', 'dovecot-pigeonhole']
    # A deterministic file-ownership conflict must not be retried three times.
    result = subprocess.run(command)
    if result.returncode:
        log('Sieve package installation failed; configuration and service were not '
            'changed by Sieve setup. Check package compatibility before retrying.', 0)
        return False
    log('Install Sieve packages successful.', 0)
    return True


class SieveConfigCheckpoint:
    def __init__(self, paths):
        self.files = {}
        for path in paths:
            p = Path(path)
            self.files[p] = (p.read_bytes(), p.stat()) if p.exists() else None

    def restore(self):
        for path, previous in self.files.items():
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                data, metadata = previous
                path.write_bytes(data)
                os.chmod(path, metadata.st_mode & 0o7777)
                os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))


def activate_sieve_config(checkpoint, log):
    """Reject invalid candidate config without restarting a healthy service."""
    check = subprocess.run(['doveconf', '-n'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE)
    if check.returncode:
        checkpoint.restore()
        log('Sieve configuration validation failed; previous configuration restored '
            'without restarting Dovecot.', 0)
        return False
    was_active = subprocess.run(['systemctl', 'is-active', '--quiet', 'dovecot']).returncode == 0
    restart = subprocess.run(['systemctl', 'restart', 'dovecot'])
    if restart.returncode:
        checkpoint.restore()
        if was_active:
            recovery = subprocess.run(['systemctl', 'restart', 'dovecot'])
            if recovery.returncode:
                log('Dovecot recovery failed after restoring its configuration; '
                    'manual service inspection is required.', 0)
        log('Sieve activation failed; previous configuration restored.', 0)
        return False
    return True
