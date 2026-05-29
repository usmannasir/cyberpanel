# -*- coding: utf-8 -*-
"""
Ensure phpMyAdmin single-sign-on bridge files exist under public/phpmyadmin/.
Fixes 404 on /phpmyadmin/phpmyadminsignin.php when the file was lost after a partial install or manual change.
"""
from __future__ import annotations

import os
import shutil

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

PMA_DIR = '/usr/local/CyberCP/public/phpmyadmin'
SIGNIN_SRC = '/usr/local/CyberCP/plogical/phpmyadminsignin.php'
SIGNIN_NAME = 'phpmyadminsignin.php'
LPMA_SRC = '/usr/local/CyberCP/plogical/lpma_policy_read.inc.php'
LPMA_NAME = 'lpma_policy_read.inc.php'


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
        tmp_dir = os.path.join(PMA_DIR, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            from plogical.processUtilities import ProcessUtilities
            ProcessUtilities.executioner('chown -R lscpd:lscpd ' + PMA_DIR)
        except Exception as ch_ex:
            logging.writeToFile('phpmyadmin_utils: chown skipped or failed (non-fatal): ' + str(ch_ex))
        return os.path.isfile(dst)
    except Exception as ex:
        logging.writeToFile('phpmyadmin_utils: ensure_phpmyadmin_signin_bridge failed: ' + str(ex))
        return os.path.isfile(dst)
