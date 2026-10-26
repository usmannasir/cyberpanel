"""Validate a new-site restore destination before its worker starts."""
import os
import re


def validate_restore_path(root, relative):
    if not isinstance(relative, str) or len(relative) > 200:
        raise ValueError('Invalid restore path.')
    if relative.startswith('/') or '\\' in relative or '..' in relative:
        raise ValueError('Restore path must stay inside the new website document root.')
    relative = relative.rstrip('/')
    if relative:
        parts = relative.split('/')
        if any(part in ('', '.') or not re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in parts):
            raise ValueError('Use only letters, numbers, dots, hyphens and underscores in restore path segments.')
    canonical_root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, relative))
    if (canonical_root != os.path.abspath(root) or
            os.path.commonpath((canonical_root, target)) != canonical_root):
        raise ValueError('Restore path must stay inside the new website document root.')
    return relative, '0' if relative else '1'
