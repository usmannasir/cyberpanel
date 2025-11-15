#!/usr/bin/env python3
"""
Lightweight regression test for the /imunifyav route.

Authenticates by injecting a valid CyberPanel session (using the first Administrator record),
requests both /imunifyav and /ImunifyAV, and records the HTTP status alongside the
imunify-antivirus service state.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

import django  # noqa: E402
django.setup()

from django.test import Client  # noqa: E402
from loginSystem.models import Administrator  # noqa: E402

LOG_PATH = ROOT_DIR / "test_logs" / "imunifyav_route.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_service_state():
    try:
        output = subprocess.check_output(
            ["systemctl", "is-active", "imunify-antivirus"],
            stderr=subprocess.STDOUT,
            timeout=10,
            text=True,
        ).strip()
        return output
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def perform_request(client, path):
    try:
        response = client.get(path, follow=True)
        return response.status_code, None
    except Exception as exc:  # pragma: no cover - diagnostic logging
        return None, str(exc)


def build_client():
    admin = Administrator.objects.first()
    if not admin:
        return None, "No administrator records available to seed the session."

    client = Client()
    session = client.session
    session["userID"] = admin.pk
    session.save()
    return client, None


def log_result(entry):
    entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    client, client_error = build_client()
    service_state = get_service_state()
    results = {
        "module": "imunifyav_route_check",
        "service_state": service_state,
        "retry": 0,
        "errors": [],
        "responses": {},
    }

    if client is None:
        results["errors"].append(client_error or "Unable to initialize Django test client.")
        log_result(results)
        print(json.dumps(results, indent=2))
        sys.exit(1)

    for path in ("/imunifyav/", "/ImunifyAV/"):
        status_code, error = perform_request(client, path)
        results["responses"][path] = status_code
        if error:
            results["errors"].append(f"{path}: {error}")

    log_result(results)
    print(json.dumps(results, indent=2))

    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

