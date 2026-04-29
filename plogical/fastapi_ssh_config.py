"""
Runtime configuration and migration helpers for fastapi_ssh_server (Web Terminal).

Secrets are stored in /etc/cyberpanel/fastapi_ssh_server.conf (chmod 600), not in Python source.

Install and upgrade touchpoints (copy, enable, restart, firewall):
- install/install.py (configure_jwt_secret, firewalld rules without public 8888)
- install/venvsetup_modules/04_after_install.sh (restart fastapi_ssh_server when conf exists)
- plogical/upgrade.py (apply_security_migration before systemctl restart fastapi_ssh_server)
- websiteFunctions/website.py (ensure_web_terminal_runtime_for_panel, systemd unit, start service)
- websiteFunctions/views.py (get_terminal_jwt uses get_jwt_encode_settings)
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import subprocess
from typing import Dict, Optional, Tuple

_LOGGER = logging.getLogger("cyberpanel.fastapi_ssh_config")

CONF_PATH = "/etc/cyberpanel/fastapi_ssh_server.conf"
MARKER_PATH = "/etc/cyberpanel/fastapi_ssh_server_hardening_v1.done"
FASTAPI_PY = "/usr/local/CyberCP/fastapi_ssh_server.py"
SERVICE_SRC = "/usr/local/CyberCP/fastapi_ssh_server.service"
SERVICE_DST = "/etc/systemd/system/fastapi_ssh_server.service"

LEGACY_JWT_SECRETS = frozenset(
    {
        "DAsjK2gl50PE09d1N3uZPTQ6JdwwfiuhlyWKMVbUEpc",
        "YOUR_SECRET_KEY",
        "REPLACE_ME_WITH_INSTALLER",
    }
)

DEFAULT_ISS = "cyberpanel-web-terminal"
DEFAULT_AUD = "cyberpanel-fastapi-ssh"


def _parse_conf_text(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def read_conf_file_dict(path: str = CONF_PATH) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return _parse_conf_text(handle.read())
    except FileNotFoundError:
        return {}
    except OSError as exc:
        _LOGGER.warning("Could not read %s: %s", path, exc)
        return {}


def is_strong_secret(secret: Optional[str]) -> bool:
    if not secret or len(secret) < 32:
        return False
    if secret in LEGACY_JWT_SECRETS:
        return False
    return True


def generate_secret() -> str:
    return secrets.token_urlsafe(48)


def write_runtime_conf(
    jwt_secret: str,
    iss: str = DEFAULT_ISS,
    aud: str = DEFAULT_AUD,
    allowed_origins: str = "",
) -> None:
    os.makedirs(os.path.dirname(CONF_PATH), exist_ok=True)
    lines = [
        "# CyberPanel Web Terminal (fastapi_ssh_server) runtime configuration",
        "# Keep permissions at chmod 600 and root ownership.",
        f'JWT_SECRET="{jwt_secret}"',
        f'JWT_ISS="{iss}"',
        f'JWT_AUD="{aud}"',
    ]
    if allowed_origins.strip():
        lines.append(f'ALLOWED_ORIGINS="{allowed_origins.strip()}"')
    content = "\n".join(lines) + "\n"
    with open(CONF_PATH, "w", encoding="utf-8") as handle:
        handle.write(content)
    try:
        os.chmod(CONF_PATH, 0o600)
    except OSError as exc:
        _LOGGER.warning("Could not chmod %s: %s", CONF_PATH, exc)


def _extract_jwt_from_py(content: str) -> Optional[str]:
    for line in content.splitlines():
        match = re.match(r"^\s*JWT_SECRET\s*=\s*[\"']([^\"']+)[\"']", line)
        if match:
            return match.group(1)
    return None


def migrate_secret_from_legacy_py() -> Optional[str]:
    """
    Read JWT_SECRET from the deployed Python file if present (one-time migration).
    Does not log secret material.
    """
    try:
        with open(FASTAPI_PY, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except OSError:
        return None
    return _extract_jwt_from_py(content)


def ensure_web_terminal_runtime_for_panel() -> None:
    """
    Panel-side: ensure runtime conf exists and refresh systemd unit if an old 0.0.0.0 bind is present.
    """
    ensure_runtime_files_on_install()
    try:
        if os.path.isfile(SERVICE_DST):
            with open(SERVICE_DST, "r", encoding="utf-8", errors="replace") as handle:
                body = handle.read()
            if "0.0.0.0" in body and os.path.isfile(SERVICE_SRC):
                subprocess.run(
                    ["cp", "-f", SERVICE_SRC, SERVICE_DST],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["systemctl", "daemon-reload"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        elif os.path.isfile(SERVICE_SRC):
            subprocess.run(
                ["cp", "-f", SERVICE_SRC, SERVICE_DST],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["systemctl", "daemon-reload"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except OSError as exc:
        _LOGGER.debug("ensure_web_terminal_runtime_for_panel unit check: %s", exc)


def ensure_runtime_files_on_install() -> None:
    """
    Fresh install: ensure /etc/cyberpanel/fastapi_ssh_server.conf exists with a strong secret.
    """
    try:
        data = read_conf_file_dict()
        cur = (os.environ.get("JWT_SECRET") or data.get("JWT_SECRET", "")).strip()
        if is_strong_secret(cur):
            print("Web Terminal JWT already configured at %s" % CONF_PATH)
            return
        secret = generate_secret()
        iss = data.get("JWT_ISS") or DEFAULT_ISS
        aud = data.get("JWT_AUD") or DEFAULT_AUD
        origins = (data.get("ALLOWED_ORIGINS") or "").strip()
        write_runtime_conf(secret, iss=iss, aud=aud, allowed_origins=origins)
        print("Configured Web Terminal JWT in %s" % CONF_PATH)
    except Exception as exc:
        _LOGGER.error("ensure_runtime_files_on_install failed: %s", exc)
        print("[WARNING] Web Terminal runtime config could not be written: %s" % exc)


def get_jwt_encode_settings() -> Tuple[str, str, str]:
    """
    Panel-side token creation: return (secret, iss, aud).
    """
    data = read_conf_file_dict()
    secret = (os.environ.get("JWT_SECRET") or data.get("JWT_SECRET", "")).strip()
    if not is_strong_secret(secret):
        raise ValueError(
            "Web Terminal JWT is not configured securely. Check %s" % CONF_PATH
        )
    iss = data.get("JWT_ISS") or DEFAULT_ISS
    aud = data.get("JWT_AUD") or DEFAULT_AUD
    return secret, iss, aud


def _try_remove_public_8888_ports() -> None:
    """
    Remove simple firewalld port openings for 8888/tcp if present (legacy exposure).
    """
    for cmd in (
        "firewall-cmd --permanent --zone=public --remove-port=8888/tcp",
        "firewall-cmd --reload",
    ):
        try:
            subprocess.run(
                cmd,
                shell=True,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            _LOGGER.debug("firewall cmd skipped: %s", exc)


def apply_security_migration() -> None:
    """
    Idempotent upgrade migration: strong secret on disk, refresh systemd unit, marker file.
    """
    data = read_conf_file_dict()
    secret = (os.environ.get("JWT_SECRET") or data.get("JWT_SECRET", "")).strip()
    need_conf_write = False

    if not is_strong_secret(secret):
        py_secret = migrate_secret_from_legacy_py()
        if is_strong_secret(py_secret):
            secret = py_secret
        else:
            secret = generate_secret()
        need_conf_write = True
    elif not os.path.isfile(CONF_PATH):
        secret = generate_secret()
        need_conf_write = True

    if need_conf_write:
        write_runtime_conf(
            secret,
            iss=data.get("JWT_ISS") or DEFAULT_ISS,
            aud=data.get("JWT_AUD") or DEFAULT_AUD,
            allowed_origins=(data.get("ALLOWED_ORIGINS") or "").strip(),
        )

    try:
        if os.path.isfile(SERVICE_SRC):
            subprocess.run(
                ["cp", "-f", SERVICE_SRC, SERVICE_DST],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["systemctl", "daemon-reload"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except OSError as exc:
        _LOGGER.warning("apply_security_migration unit refresh: %s", exc)

    _try_remove_public_8888_ports()

    try:
        with open(MARKER_PATH, "w", encoding="utf-8") as marker:
            marker.write("fastapi_ssh_server hardening migration v1 applied\n")
        os.chmod(MARKER_PATH, 0o600)
    except OSError as exc:
        _LOGGER.warning("Could not write marker %s: %s", MARKER_PATH, exc)
