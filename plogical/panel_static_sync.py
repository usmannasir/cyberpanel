# -*- coding: utf-8 -*-
"""
Keep CyberPanel panel static files in sync with LiteSpeed.

The OpenLiteSpeed / LSWS CyberPanel vhost serves URL /static/ from
/usr/local/CyberCP/public/static/ (type static). Django's STATIC_ROOT is
/usr/local/CyberCP/static/. Any collectstatic that does not end with moving
the whole tree into public/ leaves new files only under STATIC_ROOT, so
/static/webmail/*.js returns 404 + text/html and the Angular webmail UI breaks.

Call ensure_litespeed_panel_static_complete() after:
  manage.py collectstatic
whenever the result must be visible on the panel (port 2087 / reverse proxy).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

_CYBERCP = "/usr/local/CyberCP"
_STATIC_ROOT = os.path.join(_CYBERCP, "static")
_PUBLIC_STATIC = os.path.join(_CYBERCP, "public", "static")
_WEBMAIL_SRC = os.path.join(_CYBERCP, "webmail", "static", "webmail")
_WEBMAIL_DST = os.path.join(_PUBLIC_STATIC, "webmail")
_WEBMAIL_JS = os.path.join(_WEBMAIL_DST, "webmail.js")


def _merge_copy_tree(src: str, dst: str) -> None:
    """Copy every file/dir from src into dst, merging into existing dirs."""
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s_path = os.path.join(src, name)
        d_path = os.path.join(dst, name)
        if os.path.isdir(s_path):
            shutil.copytree(s_path, d_path, dirs_exist_ok=True)
        else:
            shutil.copy2(s_path, d_path)


def _chown_public_static() -> None:
    """Best-effort ownership for files LiteSpeed serves directly."""
    if not os.path.isdir(_PUBLIC_STATIC):
        return
    try:
        if subprocess.call(["getent", "passwd", "lscpd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            return
    except OSError:
        return
    try:
        subprocess.call(
            ["chown", "-R", "lscpd:lscpd", _PUBLIC_STATIC],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def sync_static_root_to_public() -> None:
    """Merge Django STATIC_ROOT into public/static (if STATIC_ROOT exists)."""
    _merge_copy_tree(_STATIC_ROOT, _PUBLIC_STATIC)


def ensure_webmail_static_under_public() -> None:
    """Guarantee public/static/webmail/{webmail.js,webmail.css} exist."""
    if os.path.isfile(_WEBMAIL_JS):
        return
    os.makedirs(_WEBMAIL_DST, exist_ok=True)
    if os.path.isdir(_WEBMAIL_SRC):
        _merge_copy_tree(_WEBMAIL_SRC, _WEBMAIL_DST)
        return
    alt = os.path.join(_STATIC_ROOT, "webmail")
    if os.path.isdir(alt):
        _merge_copy_tree(alt, _WEBMAIL_DST)


def ensure_litespeed_panel_static_complete() -> bool:
    """
    Idempotent: merge STATIC_ROOT -> public/static, then ensure webmail assets.
    Returns True if public/static/webmail/webmail.js exists afterward.
    """
    try:
        sync_static_root_to_public()
        ensure_webmail_static_under_public()
        _chown_public_static()
        return os.path.isfile(_WEBMAIL_JS)
    except OSError as exc:
        print("panel_static_sync: %s" % (exc,), file=sys.stderr)
        return os.path.isfile(_WEBMAIL_JS)


def ensure_from_cli() -> int:
    """Entry point: python3 -m plogical.panel_static_sync"""
    ok = ensure_litespeed_panel_static_complete()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(ensure_from_cli())
