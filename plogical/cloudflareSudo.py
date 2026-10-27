"""Root-only provisioning for the bounded Cloudflare credential helper."""
from pathlib import Path
from plogical.gdriveSudo import provision_fixed

PYTHON = Path('/usr/local/CyberPanel/bin/python')
HELPER = Path('/usr/local/CyberCP/plogical/cloudflareCredentials.py')
TARGET = Path('/etc/sudoers.d/cyberpanel-cloudflare')
MARKER = '# Managed by CyberPanel: isolated Cloudflare credential management.\n'


def policy():
    command = '%s -I -S %s' % (PYTHON, HELPER)
    return (MARKER + 'Cmnd_Alias CYBERPANEL_CLOUDFLARE = ' + command + ' metadata, ' + command + ' save\n'
            'Defaults!CYBERPANEL_CLOUDFLARE env_reset, !setenv, '
            'secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
            'lscpd ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_CLOUDFLARE\n'
            'cyberpanel ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_CLOUDFLARE\n')


def provision():
    return provision_fixed(PYTHON, HELPER, TARGET, policy())
