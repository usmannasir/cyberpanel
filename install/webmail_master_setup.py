#!/usr/bin/env python
"""
Dovecot webmail master user setup (SSO). Kept separate from installCyberPanel.py so
install.py can configure webmail without importing MySQLdb at module load time.
"""
from __future__ import print_function

import json
import os
import secrets
import string
import subprocess

import installLog as logging


def configure_webmail_master_user():
    """Set up Dovecot master user and /etc/cyberpanel/webmail.conf. Returns 1 on success, 0 on skip/fail."""
    try:
        dovecot_ready = (
            os.path.exists('/etc/dovecot/dovecot.conf')
            or (
                os.path.isdir('/etc/dovecot')
                and os.path.isfile('/usr/sbin/doveadm')
            )
        )
        if not dovecot_ready:
            print('Dovecot not installed, skipping webmail setup.')
            logging.InstallLog.writeToFile('Dovecot not installed, skipping webmail setup.')
            return 0

        if os.path.exists('/etc/cyberpanel/webmail.conf') and os.path.exists('/etc/dovecot/master-users'):
            print('Webmail master user already configured.')
            return 1

        print('Setting up webmail master user for SSO...')
        chars = string.ascii_letters + string.digits
        master_password = ''.join(secrets.choice(chars) for _ in range(32))

        result = subprocess.run(
            ['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', master_password],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logging.InstallLog.writeToFile(
                '[WARNING] doveadm pw failed (webmail SSO skipped): %s' % (result.stderr or '')
            )
            return 0

        password_hash = result.stdout.strip()

        with open('/etc/dovecot/master-users', 'w') as f:
            f.write('cyberpanel_master:' + password_hash + '\n')
        os.chmod('/etc/dovecot/master-users', 0o600)
        subprocess.call(['chown', 'dovecot:dovecot', '/etc/dovecot/master-users'], stderr=subprocess.DEVNULL)

        os.makedirs('/etc/cyberpanel', exist_ok=True)
        webmail_conf = {
            'master_user': 'cyberpanel_master',
            'master_password': master_password,
        }
        with open('/etc/cyberpanel/webmail.conf', 'w') as f:
            json.dump(webmail_conf, f)
        os.chmod('/etc/cyberpanel/webmail.conf', 0o600)
        subprocess.call(['chown', 'cyberpanel:cyberpanel', '/etc/cyberpanel/webmail.conf'], stderr=subprocess.DEVNULL)

        dovecot_conf_path = '/etc/dovecot/dovecot.conf'
        if os.path.isfile(dovecot_conf_path):
            with open(dovecot_conf_path, 'r') as f:
                dovecot_content = f.read()
            if 'auth_master_user_separator' not in dovecot_content:
                master_block = """auth_master_user_separator = *

passdb {
    driver = passwd-file
    master = yes
    args = /etc/dovecot/master-users
    result_success = continue
}

"""
                dovecot_content = dovecot_content.replace(
                    'passdb {',
                    master_block + 'passdb {',
                    1,
                )
                with open(dovecot_conf_path, 'w') as f:
                    f.write(dovecot_content)

        subprocess.call(
            ['systemctl', 'restart', 'dovecot'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print('Webmail master user setup complete!')
        logging.InstallLog.writeToFile('Webmail master user setup complete!')
        return 1

    except BaseException as msg:
        logging.InstallLog.writeToFile('[WARNING] webmail setup failed (non-fatal): %s' % msg)
        return 0
