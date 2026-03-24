#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Idempotent schema repair: add custom_quota_enabled and custom_quota_size to the
Django ftp.Users table (Meta.db_table = 'users') if missing.

Fixes MySQL 1054: Unknown column 'custom_quota_enabled' in 'INSERT INTO'
when creating FTP accounts after upgrading CyberPanel without a matching migration.

Usage:
  CP_DIR=/usr/local/CyberCP python3 ensure_ftp_users_quota_columns.py
  python3 ensure_ftp_users_quota_columns.py /usr/local/CyberCP
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        if len(sys.argv) > 1 and sys.argv[1].strip():
            cp_dir = os.path.abspath(sys.argv[1].strip())
        else:
            cp_dir = os.path.abspath(os.environ.get("CP_DIR", "/usr/local/CyberCP"))

        if not os.path.isdir(cp_dir):
            sys.stderr.write("ensure_ftp_users_quota_columns: CP directory not found: %s\n" % cp_dir)
            return 1

        sys.path.insert(0, cp_dir)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

        import django

        django.setup()

        from django.db import connection

        table = "users"
        alters = (
            ("custom_quota_enabled", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("custom_quota_size", "INT NOT NULL DEFAULT 0"),
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            row = cursor.fetchone()
            dbname = row[0] if row else None
            if not dbname:
                sys.stderr.write(
                    "ensure_ftp_users_quota_columns: could not resolve current database name.\n"
                )
                return 1

            for col, definition in alters:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                    """,
                    [dbname, table, col],
                )
                exists = cursor.fetchone()[0] > 0
                if exists:
                    print("ensure_ftp_users_quota_columns: column %s already on %s; skipped." % (col, table))
                    continue
                # identifiers are fixed literals; definition is controlled (no user input)
                cursor.execute(
                    "ALTER TABLE `%s` ADD COLUMN `%s` %s" % (table, col, definition)
                )
                print("ensure_ftp_users_quota_columns: added column %s to %s." % (col, table))

        print("ensure_ftp_users_quota_columns: done.")
        return 0
    except Exception as exc:
        sys.stderr.write("ensure_ftp_users_quota_columns: error: %s\n" % (exc,))
        return 1


if __name__ == "__main__":
    sys.exit(main())
