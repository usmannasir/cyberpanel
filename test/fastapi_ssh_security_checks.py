#!/usr/bin/env python3
"""
Static checks for Web Terminal security changes (no live services required).
"""
from __future__ import annotations

import os
import re
import sys


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    py_path = os.path.join(root, "fastapi_ssh_server.py")
    svc_path = os.path.join(root, "fastapi_ssh_server.service")
    install_path = os.path.join(root, "install", "install.py")

    with open(py_path, "r", encoding="utf-8", errors="replace") as handle:
        py_src = handle.read()
    if "DAsjK2gl50PE09d1N3uZPTQ6JdwwfiuhlyWKMVbUEpc" in py_src:
        print("FAIL: legacy JWT constant leaked in fastapi_ssh_server.py", file=sys.stderr)
        return 1
    if re.search(r"^\s*JWT_SECRET\s*=", py_src, re.MULTILINE):
        print("FAIL: JWT_SECRET must not be assigned in fastapi_ssh_server.py", file=sys.stderr)
        return 1

    with open(svc_path, "r", encoding="utf-8", errors="replace") as handle:
        svc = handle.read()
    if "EnvironmentFile=-/etc/cyberpanel/fastapi_ssh_server.conf" not in svc:
        print("FAIL: service unit must include EnvironmentFile for runtime conf", file=sys.stderr)
        return 1

    with open(install_path, "r", encoding="utf-8", errors="replace") as handle:
        inst = handle.read()
    if 'FirewallUtilities.addRule("tcp", "8888")' in inst:
        print("FAIL: installer must not add public tcp 8888", file=sys.stderr)
        return 1

    print("OK: fastapi_ssh_security_checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
