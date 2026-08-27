# -*- coding: utf-8 -*-
"""Build and maintain CyberPanel's Imunify generic-panel integration."""

from __future__ import print_function

import os
import pwd
import grp
import shlex
import stat
import subprocess
import tempfile


INTEGRATION_CONF = '/etc/sysconfig/imunify360/integration.conf'
IMUNIFY_AV_UI = '/usr/local/CyberCP/public/imunifyav'
IMUNIFY_360_UI = '/usr/local/CyberCP/public/imunify'
CLSCRIPT_DIR = '/usr/local/CyberCP/CLScript'
DEPLOY_TMP = '/tmp/cyberpanel-imunify-deploy'
INSTALL_STATUS_PATH = '/home/cyberpanel/switchLSWSStatus'
PANEL_PYTHON = '/usr/local/CyberCP/bin/python'
CAGEFS_MANAGER = '/usr/local/CyberCP/CLManager/CageFS.py'

CLSCRIPT_OPTIONS = (
    ('panel_info', 'panel_info.py'),
    ('users', 'CloudLinuxUsers.py'),
    ('domains', 'CloudLinuxDomains.py'),
    ('packages', 'CloudLinuxPackages.py'),
    ('resellers', 'CloudLinuxResellers.py'),
    ('admins', 'CloudLinuxAdmins.py'),
    ('db_info', 'CloudLinuxDB.py'),
)


def _integration_scripts_block():
    lines = ['[integration_scripts]']
    for option, filename in CLSCRIPT_OPTIONS:
        lines.append('%s = %s/%s' % (option, CLSCRIPT_DIR, filename))
    return '\n'.join(lines) + '\n\n'


def _common_integration_blocks():
    return (
        '[pam]\n'
        'service_name = system-auth\n\n'
        '%s'
        '[malware]\n'
        'basedir = /home\n'
        'pattern_to_watch = ^/home/.+?/(public_html|public_ftp|private_html)(/.*)?$\n\n'
        '[web_server]\n'
        'server_type = litespeed\n'
        'graceful_restart_script = /usr/local/lsws/bin/lswsctrl restart\n'
        'modsec_audit_log = /usr/local/lsws/logs/auditmodsec.log\n'
        'modsec_audit_logdir = /usr/local/lsws/logs/\n'
    ) % _integration_scripts_block()


def _build_integration_conf(ui_path):
    return (
        '[paths]\n'
        'ui_path = %s\n'
        'ui_path_owner = lscpd:lscpd\n\n'
        '%s'
    ) % (ui_path, _common_integration_blocks())


def build_imunifyav_integration_conf():
    return _build_integration_conf(IMUNIFY_AV_UI)


def build_imunify360_integration_conf():
    return _build_integration_conf(IMUNIFY_360_UI)


def detect_imunify_product(config_content):
    """Return ``av``, ``360``, or ``None`` from an integration.conf body."""
    for raw_line in config_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(('#', ';')):
            continue
        option, separator, value = line.partition('=')
        if not separator or option.strip().lower() != 'ui_path':
            continue
        ui_path = value.strip().rstrip('/')
        if ui_path == IMUNIFY_AV_UI:
            return 'av'
        if ui_path == IMUNIFY_360_UI:
            return '360'
    return None


def _read_config(config_path):
    try:
        with open(config_path, 'r') as handle:
            return handle.read()
    except OSError:
        return None


def write_integration_conf(content, config_path=INTEGRATION_CONF):
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)

    temporary = tempfile.NamedTemporaryFile(
        mode='w',
        dir=config_dir or '.',
        prefix='.integration.conf.',
        delete=False,
    )
    try:
        with temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary.name, 0o644)
        os.replace(temporary.name, config_path)
    except BaseException:
        try:
            os.unlink(temporary.name)
        except OSError:
            pass
        raise


def integration_conf_needs_repair(config_path=INTEGRATION_CONF):
    body = _read_config(config_path)
    if body is None or detect_imunify_product(body) is None:
        return True
    if '[integration_scripts]' not in body:
        return True
    return any(
        '%s/%s' % (CLSCRIPT_DIR, filename) not in body
        for _option, filename in CLSCRIPT_OPTIONS
    )


def repair_integration_conf(config_path=INTEGRATION_CONF):
    body = _read_config(config_path)
    if body is None:
        return None

    product = detect_imunify_product(body)
    if product == 'av':
        content = build_imunifyav_integration_conf()
    elif product == '360':
        content = build_imunify360_integration_conf()
    else:
        return None

    write_integration_conf(content, config_path)
    return product


def ensure_clscripts_executable(script_dir=CLSCRIPT_DIR):
    if not os.path.isdir(script_dir):
        return
    for _option, filename in CLSCRIPT_OPTIONS:
        path = os.path.join(script_dir, filename)
        if not os.path.isfile(path):
            continue
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def chmod_imunify_execute_files(ui_root):
    if not ui_root or not os.path.isdir(ui_root):
        return
    for directory, _subdirectories, filenames in os.walk(ui_root):
        if 'execute.py' in filenames:
            os.chmod(os.path.join(directory, 'execute.py'), 0o755)


def ensure_install_status_file(
    status_path=INSTALL_STATUS_PATH,
    owner=('cyberpanel', 'cyberpanel'),
    reset=False,
):
    status_dir = os.path.dirname(status_path)
    status_dir_created = False
    if status_dir:
        status_dir_created = not os.path.isdir(status_dir)
        os.makedirs(status_dir, exist_ok=True)
    with open(status_path, 'w' if reset else 'a'):
        pass
    os.chmod(status_path, 0o644)

    if owner is not None:
        try:
            uid = pwd.getpwnam(owner[0]).pw_uid
            gid = grp.getgrnam(owner[1]).gr_gid
            if status_dir_created:
                os.chown(status_dir, uid, gid)
            os.chown(status_path, uid, gid)
        except (KeyError, OSError):
            pass


def read_install_status(status_path=INSTALL_STATUS_PATH):
    try:
        with open(status_path, 'r') as status_file:
            return status_file.read()
    except FileNotFoundError:
        return None


def build_deploy_commands(product, key=None, deploy_tmp=DEPLOY_TMP):
    if product == 'av':
        filename = 'imav-deploy.sh'
        url = 'https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh'
    elif product == '360':
        if key is None or not str(key).strip():
            raise ValueError('An Imunify360 license key is required.')
        filename = 'i360deploy.sh'
        url = 'https://repo.imunify360.cloudlinux.com/defence360/i360deploy.sh'
    else:
        raise ValueError('Unsupported Imunify product.')

    script_path = os.path.join(deploy_tmp, filename)
    commands = [
        ['mkdir', '-p', deploy_tmp],
        ['pkill', '-f', '[%s]%s' % (filename[0], filename[1:])],
        [
            'wget', '--tries=3', '--timeout=30', '-O', script_path, url,
        ],
    ]
    if product == '360':
        commands.append(['bash', script_path, '--key', str(key), '--yes'])
    else:
        commands.append(['bash', script_path, '--yes'])
    return commands


def build_install_worker_command(product, key=None):
    arguments = [PANEL_PYTHON, CAGEFS_MANAGER, '--function']
    if product == '360':
        if key is None or not str(key).strip():
            raise ValueError('An Imunify360 license key is required.')
        arguments.extend(('submitinstallImunify', '--key', str(key)))
    elif product == 'av':
        arguments.append('submitinstallImunifyAV')
    else:
        raise ValueError('Unsupported Imunify product.')
    return ' '.join(shlex.quote(argument) for argument in arguments)


def run_deploy_commands(commands, status_file):
    failure_messages = (
        'Could not create the Imunify deployment directory.',
        'Could not stop an existing Imunify installer.',
        'Imunify installer download failed.',
        'Imunify installation failed.',
    )
    for index, command in enumerate(commands):
        return_code = subprocess.call(
            command,
            stdout=status_file,
            stderr=status_file,
        )
        if return_code != 0 and index != 1:
            raise RuntimeError(
                '%s (exit code %s)' % (failure_messages[index], return_code)
            )
        if index == 2:
            script_path = command[-2]
            if (not os.path.isfile(script_path) or
                    os.path.getsize(script_path) < 1024):
                raise RuntimeError(
                    'Imunify installer download was empty or incomplete.'
                )
