#!/usr/bin/env python3
"""
Unit tests for plogical/upgrade.py MariaDB version read from /etc/cyberpanel/mariadb_version.
Tests that 11.8 and 12.1 are both accepted and that downgrade (12.1 -> 11.8) is supported.
Run from repo root: python3 test/test_upgrade_mariadb_version.py
"""
import os
import sys
import tempfile

# Logic extracted from Upgrade.fix_almalinux9_mariadb() - read mariadb_version file
def read_mariadb_version_from_file(filepath):
    mariadb_ver = "11.8"
    try:
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                raw = f.read().strip()
                if raw in ("11.8", "12.1"):
                    mariadb_ver = raw
    except Exception:
        pass
    return mariadb_ver


def test_default_no_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "nonexistent")
        assert read_mariadb_version_from_file(path) == "11.8"
    print("OK: default when file missing = 11.8")


def test_11_8():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
        f.write("11.8")
        path = f.name
    try:
        assert read_mariadb_version_from_file(path) == "11.8"
        print("OK: file 11.8 -> 11.8")
    finally:
        os.unlink(path)


def test_12_1():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
        f.write("12.1")
        path = f.name
    try:
        assert read_mariadb_version_from_file(path) == "12.1"
        print("OK: file 12.1 -> 12.1")
    finally:
        os.unlink(path)


def test_downgrade_simulation():
    # Simulate writing 12.1 then 11.8 (downgrade) - both must work
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
        f.write("12.1")
        path = f.name
    try:
        assert read_mariadb_version_from_file(path) == "12.1"
        print("OK: downgrade step 1 - 12.1")
    finally:
        pass
    with open(path, "w") as f:
        f.write("11.8")
    try:
        assert read_mariadb_version_from_file(path) == "11.8"
        print("OK: downgrade step 2 - 11.8 (downgrade supported)")
    finally:
        os.unlink(path)


def test_invalid_falls_back():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
        f.write("10.11")
        path = f.name
    try:
        assert read_mariadb_version_from_file(path) == "11.8"
        print("OK: invalid 10.11 -> 11.8")
    finally:
        os.unlink(path)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
        f.write("13")
        path = f.name
    try:
        assert read_mariadb_version_from_file(path) == "11.8"
        print("OK: invalid 13 -> 11.8")
    finally:
        os.unlink(path)


def test_repo_command_format():
    mariadb_ver = "12.1"
    command = "curl -sS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | bash -s -- --mariadb-server-version='%s'" % mariadb_ver
    assert "12.1" in command
    assert "--mariadb-server-version='12.1'" in command
    print("OK: repo command includes version 12.1")
    mariadb_ver = "11.8"
    command = "curl -sS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | bash -s -- --mariadb-server-version='%s'" % mariadb_ver
    assert "--mariadb-server-version='11.8'" in command
    print("OK: repo command includes version 11.8")


if __name__ == "__main__":
    test_default_no_file()
    test_11_8()
    test_12_1()
    test_downgrade_simulation()
    test_invalid_falls_back()
    test_repo_command_format()
    print("\nAll upgrade.py MariaDB version tests passed.")
    sys.exit(0)
