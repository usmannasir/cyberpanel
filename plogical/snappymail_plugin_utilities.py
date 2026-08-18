# -*- coding: utf-8 -*-
"""
Bundle and enable the SnappyMail list-unsubscribe-header plugin (CyberPanel).

Data may live under snappymail/ or legacy rainloop/ until migration completes.
Upstream plugin: https://github.com/master3395/snappymail-list-unsubscribe-header
"""

import os
import re
import shutil
import subprocess

PLUGIN_ID_LIST_UNSUBSCRIBE = 'list-unsubscribe-header'
BUNDLE_REL = 'install/snappymail/plugins/list-unsubscribe-header/index.php'
CYBERCP_ROOT = '/usr/local/CyberCP'

DATA_ROOT_CANDIDATES = (
    '/usr/local/lscp/cyberpanel/snappymail/data',
    '/usr/local/lscp/cyberpanel/rainloop/data',
)


def bundled_list_unsubscribe_src():
    return os.path.join(CYBERCP_ROOT, BUNDLE_REL)


def _merge_enabled_list_line(line, plugin_id):
    """Merge plugin_id into SnappyMail enabled_list = \"...\" line."""
    m = re.match(r'^(\s*enabled_list\s*=\s*")([^"]*)("\s*)\r?$', line)
    if not m:
        return line
    inner = m.group(2)
    parts = [p.strip() for p in inner.split(',') if p.strip()]
    if plugin_id not in parts:
        parts.append(plugin_id)
    inner_new = ','.join(parts)
    return m.group(1) + inner_new + m.group(3) + ('\n' if line.endswith('\n') else '')


def _force_plugins_enable_on_line(line):
    """Under [plugins], ensure enable = On."""
    if not re.match(r'^\s*enable\s*=', line):
        return line
    if re.search(r'(?i)=\s*On\b', line):
        return line
    return re.sub(r'(?i)=\s*\S+', '= On', line, count=1)


def merge_plugin_into_application_ini(application_ini_path, plugin_id):
    """
    Merge plugin_id into [plugins] enabled_list; set enable = On when that key is present.
    """
    if not os.path.isfile(application_ini_path):
        return False
    with open(application_ini_path, 'r') as f:
        lines = f.readlines()
    out = []
    in_plugins = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('[plugins]'):
            in_plugins = True
            out.append(line)
            continue
        if in_plugins and stripped.startswith('[') and not stripped.startswith('[plugins]'):
            in_plugins = False
        if in_plugins and re.match(r'^\s*enabled_list\s*=', line):
            out.append(_merge_enabled_list_line(line, plugin_id))
            continue
        if in_plugins and re.match(r'^\s*enable\s*=', line):
            out.append(_force_plugins_enable_on_line(line))
            continue
        out.append(line)
    with open(application_ini_path, 'w') as f:
        f.writelines(out)
    return True


def _chown_lscpd(path):
    try:
        subprocess.check_call(['chown', 'lscpd:lscpd', path], stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        pass


def _copy_bundled_plugin_to_data_root(data_root):
    """Copy bundled index.php into .../plugins/list-unsubscribe-header/."""
    src = bundled_list_unsubscribe_src()
    if not os.path.isfile(src):
        return False
    dest_dir = os.path.join(
        data_root, '_data_', '_default_', 'plugins', PLUGIN_ID_LIST_UNSUBSCRIBE
    )
    try:
        os.makedirs(dest_dir, mode=0o700, exist_ok=True)
    except OSError:
        return False
    dest_file = os.path.join(dest_dir, 'index.php')
    try:
        shutil.copy2(src, dest_file)
    except (OSError, IOError):
        return False
    try:
        os.chmod(dest_file, 0o644)
    except OSError:
        pass
    _chown_lscpd(dest_file)
    _chown_lscpd(dest_dir)
    return True


def install_and_enable_list_unsubscribe_header_plugin():
    """
    Copy bundled plugin into each existing SnappyMail data root and merge into enabled_list.
    Idempotent. Returns 1 if at least one data root was updated, else 0.
    """
    if not os.path.isfile(bundled_list_unsubscribe_src()):
        return 0
    ok = 0
    for root in DATA_ROOT_CANDIDATES:
        default_path = os.path.join(root, '_data_', '_default_')
        if not os.path.isdir(default_path):
            continue
        if not _copy_bundled_plugin_to_data_root(root):
            continue
        app_ini = os.path.join(default_path, 'configs', 'application.ini')
        if os.path.isfile(app_ini):
            merge_plugin_into_application_ini(app_ini, PLUGIN_ID_LIST_UNSUBSCRIBE)
            try:
                os.chmod(app_ini, 0o600)
            except OSError:
                pass
            _chown_lscpd(app_ini)
        ok = 1
    return ok
