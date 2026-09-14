"""Preflight guard for upgrades that cannot preserve a CSF installation."""

import os
import sys


CSF_UPGRADE_MESSAGE = (
    "Upgrade stopped: CSF files were detected. The upgrade cannot safely preserve its "
    "firewall policy and panel integration during replacement. Complete a "
    "reviewed manual firewall migration, verify SSH/panel access and replacement "
    "rules, then retry. CSF has not been removed."
)


def requireCSFMigration():
    if os.path.lexists('/etc/csf'):
        print(CSF_UPGRADE_MESSAGE, file=sys.stderr)
        raise SystemExit(1)
