# -*- coding: utf-8 -*-
"""Build and repair Imunify360/ImunifyAV integration.conf for CyberPanel.

Imunify's generic-panel mode requires integration.conf with ui_path plus
integration_scripts (users, domains, panel_info, etc.) pointing at CyberPanel
CLScript helpers. Without integration_scripts the UI loads but shows no users
(GitHub issue #1825).
"""
from __future__ import print_function

import os
import stat

INTEGRATION_CONF = '/etc/sysconfig/imunify360/integration.conf'
IMUNIFY_AV_UI = '/usr/local/CyberCP/public/imunifyav'
IMUNIFY_360_UI = '/usr/local/CyberCP/public/imunify'
CLSCRIPT_DIR = '/usr/local/CyberCP/CLScript'
DEPLOY_TMP = '/tmp/cyberpanel-imunify-deploy'

CLSCRIPT_NAMES = (
    'panel_info.py',
    'CloudLinuxUsers.py',
    'CloudLinuxDomains.py',
    'CloudLinuxPackages.py',
    'CloudLinuxResellers.py',
    'CloudLinuxAdmins.py',
    'CloudLinuxDB.py',
)


def _integration_scripts_block():
    lines = ['[integration_scripts]', '']
    key_map = {
        'panel_info.py': 'panel_info',
        'CloudLinuxUsers.py': 'users',
        'CloudLinuxDomains.py': 'domains',
        'CloudLinuxPackages.py': 'packages',
        'CloudLinuxResellers.py': 'resellers',
        'CloudLinuxAdmins.py': 'admins',
        'CloudLinuxDB.py': 'db_info',
    }
    for filename, key in key_map.items():
        lines.append('%s = %s/%s' % (key, CLSCRIPT_DIR, filename))
    lines.append('')
    return '\n'.join(lines)


def _malware_block():
    return """[malware]
basedir = /home
pattern_to_watch = ^/home/.+?/(public_html|public_ftp|private_html)(/.*)?$

"""


def _web_server_block():
    return """[web_server]
server_type = litespeed
graceful_restart_script = /usr/local/lsws/bin/lswsctrl restart
modsec_audit_log = /usr/local/lsws/logs/auditmodsec.log
modsec_audit_logdir = /usr/local/lsws/logs/

"""


def build_imunifyav_integration_conf():
    """Full integration.conf for ImunifyAV on CyberPanel."""
    return (
        '[paths]\n'
        'ui_path = %s\n'
        'ui_path_owner = lscpd:lscpd\n'
        '\n'
        '%s'
        '%s'
        '%s'
    ) % (IMUNIFY_AV_UI, _integration_scripts_block(), _malware_block(), _web_server_block())


def build_imunify360_integration_conf():
    """Full integration.conf for Imunify360 on CyberPanel."""
    return (
        '[paths]\n'
        'ui_path =%s\n'
        '\n'
        '%s'
        '%s'
        '%s'
    ) % (IMUNIFY_360_UI, _integration_scripts_block(), _malware_block(), _web_server_block())


def write_integration_conf(content):
    os.makedirs(os.path.dirname(INTEGRATION_CONF), exist_ok=True)
    with open(INTEGRATION_CONF, 'w') as handle:
        handle.write(content)
    try:
        os.chmod(INTEGRATION_CONF, 0o644)
    except OSError:
        pass


def ensure_clscripts_executable():
    """Imunify runs CLScript helpers directly; they must be executable."""
    if not os.path.isdir(CLSCRIPT_DIR):
        return
    for name in CLSCRIPT_NAMES:
        path = os.path.join(CLSCRIPT_DIR, name)
        if os.path.isfile(path):
            try:
                mode = os.stat(path).st_mode
                os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass


def chmod_imunify_execute_files(ui_root):
    """chmod +x any execute.py shipped under the Imunify UI directory."""
    if not ui_root or not os.path.isdir(ui_root):
        return
    for dirpath, _dirnames, filenames in os.walk(ui_root):
        if 'execute.py' in filenames:
            path = os.path.join(dirpath, 'execute.py')
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass


def integration_conf_needs_repair():
    """True when integration.conf is missing integration_scripts (empty user list)."""
    if not os.path.isfile(INTEGRATION_CONF):
        return True
    try:
        with open(INTEGRATION_CONF, 'r') as handle:
            body = handle.read()
    except OSError:
        return True
    if '[integration_scripts]' not in body:
        return True
    if 'CloudLinuxUsers.py' not in body:
        return True
    return False


def detect_imunify_product_from_conf():
    """Return 'av', '360', or None based on existing integration.conf ui_path."""
    if not os.path.isfile(INTEGRATION_CONF):
        return None
    try:
        with open(INTEGRATION_CONF, 'r') as handle:
            body = handle.read()
    except OSError:
        return None
    if 'imunifyav' in body:
        return 'av'
    if '/public/imunify' in body and 'imunifyav' not in body:
        return '360'
    return None


def repair_integration_conf():
    """Rewrite integration.conf with CLScript hooks when incomplete."""
    product = detect_imunify_product_from_conf()
    if product == 'av':
        write_integration_conf(build_imunifyav_integration_conf())
    elif product == '360':
        write_integration_conf(build_imunify360_integration_conf())
    ensure_clscripts_executable()


def ensure_install_status_file():
    """Create /home/cyberpanel/switchLSWSStatus so install progress polling works."""
    try:
        from plogical.mailUtilities import mailUtilities
        mailUtilities.checkHome()
    except BaseException:
        pass
    status_path = '/home/cyberpanel/switchLSWSStatus'
    try:
        if not os.path.exists(status_path):
            open(status_path, 'a').close()
        try:
            import pwd
            import grp
            uid = pwd.getpwnam('cyberpanel').pw_uid
            gid = grp.getgrnam('cyberpanel').gr_gid
            os.chown(status_path, uid, gid)
        except (KeyError, OSError):
            pass
        os.chmod(status_path, 0o644)
    except OSError:
        pass
