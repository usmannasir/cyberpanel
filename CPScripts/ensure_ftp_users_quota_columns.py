#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Idempotent schema repair: add custom_quota_enabled and custom_quota_size to the
Django ftp.Users table (Meta.db_table = 'users') if missing.

Fixes MySQL 1054: Unknown column 'custom_quota_enabled' in 'INSERT INTO'
when creating FTP accounts after upgrading CyberPanel without a matching migration.

When Django is unavailable (broken venv), applies the same changes via mariadb CLI.

Usage:
  CP_DIR=/usr/local/CyberCP python3 ensure_ftp_users_quota_columns.py
  python3 ensure_ftp_users_quota_columns.py /usr/local/CyberCP
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys


TABLE = "users"
ALTERS = (
    ("custom_quota_enabled", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("custom_quota_size", "INT NOT NULL DEFAULT 0"),
)


def _read_mysql_root_password() -> str:
    path = "/etc/cyberpanel/mysqlPassword"
    if not os.path.isfile(path):
        return ""
    try:
        raw = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    if '"mysqlpassword"' in raw:
        try:
            data = json.loads(raw)
            return str(data.get("mysqlpassword") or "").strip()
        except (json.JSONDecodeError, TypeError, ValueError):
            return ""
    return raw.split("\n", 1)[0].strip()


def _infer_db_name(cp_dir: str) -> str:
    settings_path = os.path.join(cp_dir, "CyberCP", "settings.py")
    if not os.path.isfile(settings_path):
        return "cyberpanel"
    try:
        content = open(settings_path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return "cyberpanel"
    m = re.search(r"['\"]NAME['\"]\s*:\s*['\"]([^'\"]+)['\"]", content)
    if m:
        return m.group(1).strip()
    return "cyberpanel"


def _apply_via_django(cp_dir: str) -> int:
    sys.path.insert(0, cp_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

    import django

    django.setup()

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        row = cursor.fetchone()
        dbname = row[0] if row else None
        if not dbname:
            sys.stderr.write(
                "ensure_ftp_users_quota_columns: could not resolve current database name.\n"
            )
            return 1

        for col, definition in ALTERS:
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                """,
                [dbname, TABLE, col],
            )
            exists = cursor.fetchone()[0] > 0
            if exists:
                print(
                    "ensure_ftp_users_quota_columns: column %s already on %s; skipped."
                    % (col, TABLE)
                )
                continue
            cursor.execute(
                "ALTER TABLE `%s` ADD COLUMN `%s` %s" % (TABLE, col, definition)
            )
            print("ensure_ftp_users_quota_columns: added column %s to %s." % (col, TABLE))

    print("ensure_ftp_users_quota_columns: done.")
    return 0


def _apply_via_mariadb_cli(cp_dir: str) -> int:
    password = _read_mysql_root_password()
    if not password:
        sys.stderr.write(
            "ensure_ftp_users_quota_columns: cannot read /etc/cyberpanel/mysqlPassword for SQL fallback.\n"
        )
        return 1
    dbname = _infer_db_name(cp_dir)
    if not re.match(r"^[A-Za-z0-9_]+$", dbname):
        sys.stderr.write("ensure_ftp_users_quota_columns: unsafe database name for SQL fallback.\n")
        return 1
    mariadb = shutil.which("mariadb") or shutil.which("mysql")
    if not mariadb:
        sys.stderr.write(
            "ensure_ftp_users_quota_columns: mariadb/mysql client not found for SQL fallback.\n"
        )
        return 1

    env = os.environ.copy()
    env["MYSQL_PWD"] = password

    def run_sql(sql: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [mariadb, "-u", "root", "-N", "-B", "-e", sql],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    for col, definition in ALTERS:
        if not re.match(r"^[A-Za-z0-9_]+$", col):
            sys.stderr.write("ensure_ftp_users_quota_columns: invalid column name.\n")
            return 1
        chk = (
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE "
            "TABLE_SCHEMA='%s' AND TABLE_NAME='%s' AND COLUMN_NAME='%s'"
            % (dbname, TABLE, col)
        )
        r = run_sql(chk)
        if r.returncode != 0:
            sys.stderr.write(
                "ensure_ftp_users_quota_columns: SQL check failed: %s\n"
                % ((r.stderr or r.stdout or "").strip(),)
            )
            return 1
        cnt = (r.stdout or "").strip()
        if cnt != "0":
            print(
                "ensure_ftp_users_quota_columns: column %s already on %s; skipped (SQL)."
                % (col, TABLE)
            )
            continue
        alter_sql = "ALTER TABLE `%s`.`%s` ADD COLUMN `%s` %s" % (
            dbname,
            TABLE,
            col,
            definition,
        )
        r2 = run_sql(alter_sql)
        if r2.returncode != 0:
            sys.stderr.write(
                "ensure_ftp_users_quota_columns: ALTER failed for %s: %s\n"
                % (col, (r2.stderr or r2.stdout or "").strip())
            )
            return 1
        print("ensure_ftp_users_quota_columns: added column %s to %s (SQL)." % (col, TABLE))

    print("ensure_ftp_users_quota_columns: done (SQL fallback).")
    return 0


def main() -> int:
    try:
        if len(sys.argv) > 1 and sys.argv[1].strip():
            cp_dir = os.path.abspath(sys.argv[1].strip())
        else:
            cp_dir = os.path.abspath(os.environ.get("CP_DIR", "/usr/local/CyberCP"))

        if not os.path.isdir(cp_dir):
            sys.stderr.write(
                "ensure_ftp_users_quota_columns: CP directory not found: %s\n" % cp_dir
            )
            return 1

        django_ok = False
        try:
            sys.path.insert(0, cp_dir)
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            import django

            django.setup()
            django_ok = True
        except Exception as exc:
            sys.stderr.write(
                "ensure_ftp_users_quota_columns: Django unavailable (%s); using mariadb CLI fallback.\n"
                % (exc,)
            )

        if django_ok:
            try:
                return _apply_via_django(cp_dir)
            except Exception as exc:
                sys.stderr.write(
                    "ensure_ftp_users_quota_columns: Django path error (%s); trying SQL fallback.\n"
                    % (exc,)
                )
                return _apply_via_mariadb_cli(cp_dir)

        return _apply_via_mariadb_cli(cp_dir)
    except Exception as exc:
        sys.stderr.write("ensure_ftp_users_quota_columns: error: %s\n" % (exc,))
        return 1


if __name__ == "__main__":
    sys.exit(main())
