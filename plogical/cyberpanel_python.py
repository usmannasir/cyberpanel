# -*- coding: utf-8 -*-
"""
Resolve the Python interpreter for CyberPanel CLI and cron jobs.

Some installs omit /usr/local/CyberCP/bin/python (no venv). We symlink that path
to a working interpreter when missing so existing crontab lines keep working.
"""
from __future__ import annotations

import os

_CANDIDATES = (
    "/usr/local/CyberPanel/bin/python",
    "/usr/local/CyberCP/bin/python",
    "/usr/bin/python3",
    "/usr/local/bin/python3",
)


def resolve_cyberpanel_python() -> str:
    """Return first existing executable candidate, else /usr/bin/python3."""
    for path in _CANDIDATES:
        if path == "/usr/local/CyberCP/bin/python":
            continue
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return "/usr/bin/python3"


def ensure_cyberpanel_bin_python_shim() -> None:
    """
    If /usr/local/CyberCP/bin/python is missing or a broken symlink, replace with
    symlink to resolve_cyberpanel_python(). Non-destructive for a real venv file.
    """
    bin_dir = "/usr/local/CyberCP/bin"
    legacy = os.path.join(bin_dir, "python")
    try:
        os.makedirs(bin_dir, exist_ok=True)
    except OSError:
        return

    if os.path.isfile(legacy) and os.access(legacy, os.X_OK) and not os.path.islink(legacy):
        return

    if os.path.islink(legacy):
        real = os.path.realpath(legacy)
        if os.path.isfile(real) and os.access(real, os.X_OK):
            return
        try:
            os.unlink(legacy)
        except OSError:
            return

    if os.path.lexists(legacy):
        try:
            os.remove(legacy)
        except OSError:
            try:
                os.unlink(legacy)
            except OSError:
                return

    target = resolve_cyberpanel_python()
    try:
        os.symlink(target, legacy)
    except OSError:
        pass
