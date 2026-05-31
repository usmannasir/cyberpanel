# -*- coding: utf-8 -*-
"""Human-readable byte sizes for CyberPanel UI (disk usage, quotas)."""


def format_size_from_mb(size_mb):
    """
    Format a size given in megabytes for display (Norwegian-friendly spacing).
    Examples: 512 B, 12.5 KB, 88186 MB, 86.12 GB, 1.20 TB
    """
    try:
        mb = float(size_mb)
    except (TypeError, ValueError):
        return '0 MB'

    if mb < 0:
        mb = 0.0

    bytes_total = mb * 1024.0 * 1024.0

    if bytes_total >= 1024.0 ** 4:
        return '%.2f TB' % (bytes_total / (1024.0 ** 4))
    if bytes_total >= 1024.0 ** 3:
        return '%.2f GB' % (bytes_total / (1024.0 ** 3))
    if bytes_total >= 1024.0 ** 2:
        return '%.2f MB' % (bytes_total / (1024.0 ** 2))
    if bytes_total >= 1024.0:
        return '%.1f KB' % (bytes_total / 1024.0)
    return '%d B' % int(bytes_total)
