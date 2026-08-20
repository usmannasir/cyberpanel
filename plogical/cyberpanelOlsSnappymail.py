# -*- coding: utf-8 -*-
"""SnappyMail public tree helpers for OLS restrained CyberPanel vhRoot."""
from __future__ import print_function

import os
import re
import subprocess

SNAPPY_PUBLIC = '/usr/local/CyberCP/public/snappymail'
SNAPPY_LSCP = '/usr/local/lscp/cyberpanel/snappymail'
SNAPPY_DATA = '/usr/local/lscp/cyberpanel/snappymail/data/'


def _log(msg):
    try:
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        CyberCPLogFileWriter.writeToFile('[cyberpanelOlsSnappymail] ' + str(msg))
    except Exception:
        pass
    print('[cyberpanelOlsSnappymail] ' + str(msg))


def _copy_snappy_app_tree(src, dst):
    """Copy SnappyMail app files into dst; skip data/ (kept under lscp)."""
    import shutil
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name == 'data':
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            if os.path.isdir(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


def _ensure_snappy_data_path(include_path):
    """Point include.php APP_DATA_FOLDER_PATH at the shared lscp data dir."""
    if not os.path.isfile(include_path):
        return
    try:
        text = open(include_path, 'r').read()
    except Exception:
        return
    needle = "define('APP_DATA_FOLDER_PATH', '%s');" % SNAPPY_DATA
    if needle in text:
        return
    if "APP_DATA_FOLDER_PATH" in text:
        text = re.sub(
            r"define\(\s*'APP_DATA_FOLDER_PATH'\s*,\s*'[^']*'\s*\)\s*;",
            needle,
            text,
            count=1,
        )
    else:
        text = text.replace('<?php', "<?php\n" + needle, 1)
    try:
        open(include_path, 'w').write(text)
    except Exception as e:
        _log('WARNING: could not update %s: %s' % (include_path, e))


def ensure_snappymail_public_tree():
    """Keep SnappyMail under CyberCP vhRoot (restrained=1 blocks /usr/local/lscp symlinks)."""
    import shutil
    public = SNAPPY_PUBLIC
    lscp = SNAPPY_LSCP
    index_public = os.path.join(public, 'index.php')
    index_lscp = os.path.join(lscp, 'index.php')

    try:
        if os.path.islink(public):
            target = os.path.realpath(public)
            _log('Replacing public/snappymail symlink with real tree (was -> %s)' % target)
            os.unlink(public)
            src = target if os.path.isfile(os.path.join(target, 'index.php')) else lscp
            if not os.path.isfile(os.path.join(src, 'index.php')):
                _log('WARNING: no SnappyMail source after removing symlink')
                return False
            _copy_snappy_app_tree(src, public)
        elif not os.path.isfile(index_public):
            if os.path.isfile(index_lscp):
                _log('Restoring public/snappymail from %s' % lscp)
                if os.path.isdir(public):
                    shutil.rmtree(public)
                _copy_snappy_app_tree(lscp, public)
            else:
                _log('WARNING: SnappyMail index.php missing under public and lscp')
                return False

        _ensure_snappy_data_path(os.path.join(public, 'include.php'))
        os.makedirs(SNAPPY_DATA, exist_ok=True)
        try:
            subprocess.run(
                ['chown', '-R', 'lscpd:lscpd', public, SNAPPY_DATA.rstrip('/')],
                capture_output=True, timeout=120,
            )
        except Exception:
            pass
        return os.path.isfile(index_public) and not os.path.islink(public)
    except Exception as e:
        _log('ERROR ensure_snappymail_public_tree: %s' % e)
        return False
