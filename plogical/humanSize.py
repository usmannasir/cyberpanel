# -*- coding: utf-8 -*-
"""Human-readable size labels from megabyte values (panel stats)."""

from __future__ import annotations

import json

VALID_SIZE_MODES = ("auto", "MB", "GB")
SIZE_DISPLAY_UNIT_KEY = "sizeDisplayUnit"


def normalize_size_mode(mode):
    if mode is None:
        return "auto"
    m = str(mode).strip()
    if m.lower() == "auto":
        return "auto"
    if m.upper() == "MB":
        return "MB"
    if m.upper() == "GB":
        return "GB"
    return "auto"


def group_int(n):
    """Space-grouped integer digits, e.g. 47914 -> '47 914'."""
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        return "0"
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    parts = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return sign + " ".join(reversed(parts))


def _to_mb_float(value):
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_mb(value, mode="auto"):
    """
    Format a size that is measured in megabytes.

    mode:
      auto - pick KB/MB/GB/TB
      MB   - always megabytes with thousands grouping
      GB   - always gigabytes
    """
    mode = normalize_size_mode(mode)
    mb = _to_mb_float(value)
    if mb < 0:
        mb = 0.0

    if mode == "MB":
        return "%s MB" % group_int(mb)

    if mode == "GB":
        gb = mb / 1024.0
        if abs(gb - round(gb)) < 0.005 and abs(gb) >= 10:
            return "%s GB" % group_int(round(gb))
        return "%.2f GB" % gb

    # auto
    bytes_val = mb * 1024.0 * 1024.0
    if bytes_val >= 1024.0 ** 4:
        return "%.2f TB" % (bytes_val / (1024.0 ** 4))
    if bytes_val >= 1024.0 ** 3:
        return "%.2f GB" % (bytes_val / (1024.0 ** 3))
    if bytes_val >= 1024.0 ** 2:
        # Whole MB often for small-ish values; group if large
        if mb >= 1000:
            return "%s MB" % group_int(mb)
        if abs(mb - round(mb)) < 0.005:
            return "%s MB" % group_int(round(mb))
        return "%.2f MB" % mb
    if bytes_val >= 1024.0:
        return "%.1f KB" % (bytes_val / 1024.0)
    return "%s B" % group_int(bytes_val)


def format_quota_mb(value, mode="auto"):
    """Quota in MB; 0 / empty means Unlimited."""
    if value is None:
        return "Unlimited"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "Unlimited"
    if v <= 0:
        return "Unlimited"
    return format_mb(v, mode)


def get_admin_size_mode(admin):
    """Read sizeDisplayUnit from Administrator.config JSON."""
    if admin is None:
        return "auto"
    raw = getattr(admin, "config", None) or ""
    if not raw or raw in ("None", "{}"):
        return "auto"
    try:
        cfg = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(cfg, dict):
            return "auto"
        return normalize_size_mode(cfg.get(SIZE_DISPLAY_UNIT_KEY, "auto"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return "auto"


def set_admin_size_mode(admin, mode, save=True):
    """Write sizeDisplayUnit into Administrator.config. Returns normalized mode."""
    mode = normalize_size_mode(mode)
    raw = getattr(admin, "config", None) or ""
    cfg = {}
    if raw and raw not in ("None",):
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                cfg = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            cfg = {}
    cfg[SIZE_DISPLAY_UNIT_KEY] = mode
    admin.config = json.dumps(cfg)
    if save:
        admin.save()
    return mode


def size_mode_for_request(request):
    """Session viewing admin's size preference."""
    try:
        from loginSystem.models import Administrator
        user_id = request.session.get("userID")
        if not user_id:
            return "auto"
        admin = Administrator.objects.get(pk=user_id)
        return get_admin_size_mode(admin)
    except Exception:
        return "auto"
