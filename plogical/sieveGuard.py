#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""
Ensure Dovecot sieve (pigeonhole) is usable when possible (#1733).

Policy for CyberPanel v2.5.5-dev:
  1. Keep sieve enabled when the module is present or can be installed.
  2. Try to install OS packages that provide sieve before stripping.
  3. Strip sieve/managesieve from dovecot.conf only if the module is still absent.
  4. Always verify Dovecot (and ideally Postfix) still run after changes.
"""
from __future__ import print_function

import os
import shutil

SIEVE_MODULE_DIRS = (
    '/usr/lib/dovecot/modules',
    '/usr/lib64/dovecot/modules',
    '/usr/lib/dovecot',
    '/usr/lib64/dovecot',
)

DOVECOT_CONF = '/etc/dovecot/dovecot.conf'


def _log(msg, writer=None):
    text = '[sieveGuard] %s' % (msg,)
    if writer is not None:
        try:
            writer(text)
            return
        except Exception:
            pass
    try:
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
        logging.writeToFile(text)
    except Exception:
        try:
            print(text)
        except Exception:
            pass


def sieve_module_available():
    """Return True if a sieve-related Dovecot module file is present."""
    for mod_dir in SIEVE_MODULE_DIRS:
        try:
            if not os.path.isdir(mod_dir):
                continue
            for fn in os.listdir(mod_dir):
                if 'sieve' in fn.lower():
                    return True
        except Exception:
            continue
    return False


def _decide_distro():
    try:
        from plogical.processUtilities import ProcessUtilities
        return ProcessUtilities.decideDistro()
    except Exception:
        pass
    if os.path.exists('/etc/os-release'):
        data = open('/etc/os-release', 'r').read().lower()
        if 'ubuntu' in data or 'debian' in data:
            return 'ubuntu'
    return 'centos'


def try_install_sieve_packages(writer=None):
    """
    Attempt to install pigeonhole/sieve packages for the current OS.
    Returns True if sieve becomes available after the attempt (or already was).
    """
    if sieve_module_available():
        return True

    try:
        from plogical.processUtilities import ProcessUtilities
    except Exception as msg:
        _log('Cannot import ProcessUtilities for package install: %s' % (msg,), writer)
        return False

    distro = _decide_distro()
    commands = []

    # Ubuntu/Debian package names
    if distro in (getattr(ProcessUtilities, 'ubuntu', 'ubuntu'),
                  getattr(ProcessUtilities, 'ubuntu20', 'ubuntu20'),
                  'ubuntu'):
        commands = [
            'DEBIAN_FRONTEND=noninteractive apt-get update -y',
            'DEBIAN_FRONTEND=noninteractive apt-get -y install dovecot-sieve dovecot-managesieved',
        ]
    else:
        # RHEL/Alma/Rocky/CloudLinux: try pigeonhole packages for dovecot / dovecot23
        commands = [
            'dnf -y install dovecot-pigeonhole 2>/dev/null || yum -y install dovecot-pigeonhole 2>/dev/null || '
            'dnf -y install dovecot23-pigeonhole 2>/dev/null || yum -y install dovecot23-pigeonhole 2>/dev/null || true',
        ]

    _log('Sieve module missing; attempting package install...', writer)
    for command in commands:
        try:
            ProcessUtilities.executioner(command)
        except Exception as msg:
            _log('Package install command failed: %s (%s)' % (command, msg), writer)

    available = sieve_module_available()
    if available:
        _log('Sieve module is available after install attempt.', writer)
    else:
        _log('Sieve module still unavailable after install attempt.', writer)
    return available


def strip_sieve_from_dovecot_conf(conf_path=DOVECOT_CONF, writer=None):
    """Remove sieve/managesieve tokens from protocols and mail_plugins lines."""
    if not os.path.exists(conf_path):
        return False
    try:
        with open(conf_path, 'r') as fh:
            conf_lines = fh.readlines()
        changed = False
        with open(conf_path, 'w') as fh:
            for conf_line in conf_lines:
                key = conf_line.split('=', 1)[0].strip()
                if key in ('protocols', 'mail_plugins') and 'sieve' in conf_line:
                    prefix, _, rhs = conf_line.partition('=')
                    tokens = [t for t in rhs.split() if t not in ('sieve', 'managesieve')]
                    conf_line = '%s= %s\n' % (prefix, ' '.join(tokens))
                    changed = True
                fh.write(conf_line)
        if changed:
            _log('Removed sieve/managesieve from %s so Dovecot can start.' % (conf_path,), writer)
        return changed
    except Exception as msg:
        _log('Could not strip sieve from %s: %s' % (conf_path, msg), writer)
        return False


def verify_mail_services(writer=None):
    """
    Enable and restart dovecot/postfix, then confirm dovecot is active.
    Returns True if dovecot appears active (or doveconf succeeds as a soft fallback).
    """
    try:
        from plogical.processUtilities import ProcessUtilities
    except Exception as msg:
        _log('Cannot verify mail services: %s' % (msg,), writer)
        return False

    for svc in ('dovecot', 'postfix'):
        try:
            ProcessUtilities.executioner('systemctl enable %s' % (svc,))
        except Exception:
            pass

    try:
        ProcessUtilities.executioner('systemctl restart dovecot')
    except Exception as msg:
        _log('dovecot restart failed: %s' % (msg,), writer)

    try:
        ProcessUtilities.executioner('systemctl restart postfix')
    except Exception as msg:
        _log('postfix restart failed: %s' % (msg,), writer)

    active = False
    try:
        out = ProcessUtilities.outputExecutioner('systemctl is-active dovecot')
        if isinstance(out, (list, tuple)):
            out = out[-1] if out else ''
        active = str(out).strip() == 'active'
    except Exception:
        active = False

    if not active:
        # Soft fallback: config parse
        try:
            if shutil.which('doveconf'):
                rc = ProcessUtilities.executioner('doveconf -n >/dev/null 2>&1')
                active = (rc == 1)  # ProcessUtilities often returns 1 on success
        except Exception:
            pass

    if active:
        _log('Mail verification: dovecot is active after sieve guard.', writer)
    else:
        _log('Mail verification WARNING: dovecot may not be active; check journalctl -u dovecot.', writer)
    return active


def ensure_sieve_or_strip(conf_path=DOVECOT_CONF, writer=None, verify=True):
    """
    Main entry: keep sieve when possible; install if missing; strip only on failure.
    Returns dict with keys: sieve_enabled (bool), installed_attempted (bool), stripped (bool), mail_ok (bool|None).
    """
    result = {
        'sieve_enabled': False,
        'install_attempted': False,
        'stripped': False,
        'mail_ok': None,
    }

    if sieve_module_available():
        result['sieve_enabled'] = True
        _log('Sieve module present; leaving dovecot sieve configuration enabled.', writer)
        if verify:
            result['mail_ok'] = verify_mail_services(writer=writer)
        return result

    result['install_attempted'] = True
    if try_install_sieve_packages(writer=writer):
        result['sieve_enabled'] = True
        if verify:
            result['mail_ok'] = verify_mail_services(writer=writer)
        return result

    # Install failed or unsupported: strip so Dovecot can start.
    result['stripped'] = strip_sieve_from_dovecot_conf(conf_path=conf_path, writer=writer)
    result['sieve_enabled'] = False
    if verify:
        result['mail_ok'] = verify_mail_services(writer=writer)
    return result
