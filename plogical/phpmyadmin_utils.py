# -*- coding: utf-8 -*-
"""
Ensure phpMyAdmin single-sign-on files exist under public/phpmyadmin/.
Recreates config.inc.php when missing after upgrade/reinstall so auto-login keeps working.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

PMA_DIR = '/usr/local/CyberCP/public/phpmyadmin'
SIGNIN_SRC = '/usr/local/CyberCP/plogical/phpmyadminsignin.php'
SIGNIN_NAME = 'phpmyadminsignin.php'
LPMA_SRC = '/usr/local/CyberCP/plogical/lpma_policy_read.inc.php'
LPMA_NAME = 'lpma_policy_read.inc.php'
CONFIG_NAME = 'config.inc.php'
SAMPLE_NAME = 'config.sample.inc.php'

SIGNON_BLOCK = """
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'phpmyadminsignin.php';
$cfg['Servers'][$i]['LogoutURL'] = 'phpmyadminsignin.php?logout';
$cfg['Servers'][$i]['host'] = '127.0.0.1';
$cfg['Servers'][$i]['port'] = '3306';
"""


def _read_blowfish_secret(config_path: str) -> str:
    if not os.path.isfile(config_path):
        return secrets.token_hex(16)
    try:
        content = open(config_path, 'r').read()
        match = re.search(r"\$cfg\['blowfish_secret'\]\s*=\s*'([^']*)'", content)
        if match and match.group(1).strip():
            return match.group(1).strip()
    except Exception:
        pass
    return secrets.token_hex(16)


def _config_needs_signon(config_path: str) -> bool:
    if not os.path.isfile(config_path):
        return True
    if os.path.getsize(config_path) < 64:
        return True
    try:
        content = open(config_path, 'r').read()
    except Exception:
        return True
    if "'auth_type'] = 'signon'" not in content and '"auth_type"] = "signon"' not in content:
        return True
    if 'SignonSession' not in content or 'SignonURL' not in content:
        return True
    return False


def _write_config_from_sample(config_path: str, blowfish_secret: str) -> bool:
    sample_path = os.path.join(PMA_DIR, SAMPLE_NAME)
    if not os.path.isfile(sample_path):
        logging.writeToFile('phpmyadmin_utils: sample config missing at ' + sample_path)
        return False
    try:
        lines = open(sample_path, 'r').readlines()
        write_enabled = 1
        with open(config_path, 'w') as out:
            for item in lines:
                if 'blowfish_secret' in item:
                    out.write(
                        "$cfg['blowfish_secret'] = '%s'; "
                        "/* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n" % blowfish_secret
                    )
                elif '/* Authentication type */' in item:
                    out.write(item)
                    out.write(SIGNON_BLOCK)
                    write_enabled = 0
                elif "$cfg['Servers'][$i]['AllowNoPassword']" in item:
                    write_enabled = 1
                else:
                    if write_enabled:
                        out.write(item)
            out.write("$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")
        return True
    except Exception as ex:
        logging.writeToFile('phpmyadmin_utils: failed writing config.inc.php: ' + str(ex))
        return False


def _fix_phpmyadmin_ownership() -> None:
    try:
        from plogical.processUtilities import ProcessUtilities
        ProcessUtilities.executioner('chown -R lscpd:lscpd ' + PMA_DIR)
        config_path = os.path.join(PMA_DIR, CONFIG_NAME)
        if os.path.isfile(config_path):
            ProcessUtilities.executioner('chmod 640 ' + config_path)
    except Exception as ch_ex:
        logging.writeToFile('phpmyadmin_utils: chown skipped or failed (non-fatal): ' + str(ch_ex))


def ensure_phpmyadmin_config() -> bool:
    """
    Create or repair config.inc.php with CyberPanel sign-on settings.
    Returns True when config exists and uses signon auth afterward.
    """
    config_path = os.path.join(PMA_DIR, CONFIG_NAME)
    try:
        if not os.path.isdir(PMA_DIR):
            return False
        if not _config_needs_signon(config_path):
            return True
        blowfish_secret = _read_blowfish_secret(config_path)
        if not _write_config_from_sample(config_path, blowfish_secret):
            return os.path.isfile(config_path) and not _config_needs_signon(config_path)
        logging.writeToFile('phpmyadmin_utils: restored phpMyAdmin sign-on config.inc.php', 0)
        _fix_phpmyadmin_ownership()
        return os.path.isfile(config_path) and not _config_needs_signon(config_path)
    except Exception as ex:
        logging.writeToFile('phpmyadmin_utils: ensure_phpmyadmin_config failed: ' + str(ex))
        return os.path.isfile(config_path) and not _config_needs_signon(config_path)


def ensure_phpmyadmin_signin_bridge() -> bool:
    """
    Copy plogical/phpmyadminsignin.php into the public phpMyAdmin tree if missing,
    ensure tmp/ exists, and fix ownership for lscpd.
    Returns True if the sign-in file is present afterward.
    """
    dst = os.path.join(PMA_DIR, SIGNIN_NAME)
    try:
        if not os.path.isdir(PMA_DIR):
            return False
        if not os.path.isfile(SIGNIN_SRC):
            logging.writeToFile('phpmyadmin_utils: source signin missing at ' + SIGNIN_SRC)
            return os.path.isfile(dst)
        need_copy = (not os.path.isfile(dst)) or os.path.getsize(dst) < 32
        if need_copy:
            shutil.copy2(SIGNIN_SRC, dst)
        lpma_dst = os.path.join(PMA_DIR, LPMA_NAME)
        if os.path.isfile(LPMA_SRC) and (
            (not os.path.isfile(lpma_dst)) or os.path.getsize(lpma_dst) < 32
        ):
            shutil.copy2(LPMA_SRC, lpma_dst)
        os.makedirs(os.path.join(PMA_DIR, 'tmp'), exist_ok=True)
        _fix_phpmyadmin_ownership()
        return os.path.isfile(dst)
    except Exception as ex:
        logging.writeToFile('phpmyadmin_utils: ensure_phpmyadmin_signin_bridge failed: ' + str(ex))
        return os.path.isfile(dst)


def ensure_phpmyadmin_sso() -> bool:
    """Ensure sign-on bridge and config.inc.php are both present and valid."""
    bridge_ok = ensure_phpmyadmin_signin_bridge()
    config_ok = ensure_phpmyadmin_config()
    return bridge_ok and config_ok
