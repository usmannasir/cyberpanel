#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge DATABASES from a backup settings.py into the branch checkout (in-place).

Used after git sync so production DB credentials survive without replacing INSTALLED_APPS
from the branch (e.g. webmail, emailDelivery). See upgrade_modules/09_sync.sh."""
from __future__ import annotations

import sys


def _extract_assign_block(text: str, name: str) -> tuple[str | None, int | None, int | None]:
    """Return (full_assignment, start, end_exclusive) for NAME = { ... } or None."""
    prefix = name + ' = '
    start = text.find(prefix)
    if start == -1:
        return None, None, None
    brace = text.find('{', start)
    if brace == -1:
        return None, None, None
    depth = 0
    for j in range(brace, len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                end = j + 1
                # Include trailing comma/newline if present (keep style)
                while end < len(text) and text[end] in ' \t':
                    end += 1
                if end < len(text) and text[end] == ',':
                    end += 1
                return text[start:end], start, end
    return None, None, None


def merge_settings(old_path: str, branch_path: str) -> int:
    try:
        with open(old_path, 'r', encoding='utf-8', errors='replace') as f:
            old_text = f.read()
        with open(branch_path, 'r', encoding='utf-8', errors='replace') as f:
            branch_text = f.read()
    except OSError as e:
        print('merge_production_settings: read error: %s' % e, file=sys.stderr)
        return 2

    old_db, _, _ = _extract_assign_block(old_text, 'DATABASES')
    if not old_db:
        print('merge_production_settings: no DATABASES in backup, leaving branch file', file=sys.stderr)
        return 1

    br_db, br_start, br_end = _extract_assign_block(branch_text, 'DATABASES')
    if not br_db or br_start is None or br_end is None:
        print('merge_production_settings: no DATABASES in branch settings', file=sys.stderr)
        return 3

    merged = branch_text[:br_start] + old_db + branch_text[br_end:]
    try:
        with open(branch_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(merged)
    except OSError as e:
        print('merge_production_settings: write error: %s' % e, file=sys.stderr)
        return 4

    print('merge_production_settings: replaced DATABASES from backup into %s' % branch_path)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: merge_production_settings.py /path/to/backup_settings.py /path/to/CyberCP/settings.py', file=sys.stderr)
        sys.exit(9)
    sys.exit(merge_settings(sys.argv[1], sys.argv[2]))
