"""Install the terminal unit without overriding an operator's service policy."""
import os
import shutil
import subprocess


def configure_terminal_service(*, fresh_install=False,
                               source='/usr/local/CyberCP/fastapi_ssh_server.service',
                               target='/etc/systemd/system/fastapi_ssh_server.service'):
    service = 'fastapi_ssh_server.service'
    load = subprocess.run(['systemctl', 'show', '--property=LoadState', '--value', service],
                          capture_output=True, text=True, check=True).stdout.strip()
    if load == 'masked' or (os.path.islink(target) and os.path.realpath(target) == '/dev/null'):
        return 'masked'
    if load not in ('loaded', 'not-found'):
        raise RuntimeError('Cannot determine Web Terminal service state: ' + load)
    present = load == 'loaded' or os.path.lexists(target)
    if not present and not fresh_install:
        return 'absent'
    active = subprocess.run(['systemctl', 'is-active', '--quiet', service],
                            capture_output=True, text=True).returncode == 0
    shutil.copy2(source, target)
    subprocess.run(['systemctl', 'daemon-reload'], check=True, capture_output=True, text=True)
    if not present and fresh_install:
        subprocess.run(['systemctl', 'enable', '--now', service],
                       check=True, capture_output=True, text=True)
        return 'enabled'
    if active:
        subprocess.run(['systemctl', 'restart', service],
                       check=True, capture_output=True, text=True)
        return 'restarted'
    return 'inactive'
