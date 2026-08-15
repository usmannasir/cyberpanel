import json
import subprocess

from plogical.securityUtils import (
    SYSTEM_PASSWORD_REQUEST_DIRECTORY,
    create_private_token_file,
    is_safe_system_user,
    read_private_token_file,
    remove_stale_private_token_files,
)


MAX_SYSTEM_PASSWORD_LENGTH = 1024
SYSTEM_PASSWORD_REQUEST_MAX_AGE = 5 * 60


def _validate_password_request(username, password):
    if not is_safe_system_user(username):
        raise ValueError("Invalid system user")
    if not isinstance(password, str) or not password:
        raise ValueError("Invalid password")
    if len(password) > MAX_SYSTEM_PASSWORD_LENGTH:
        raise ValueError("Invalid password")
    if "\x00" in password or "\r" in password or "\n" in password:
        raise ValueError("Invalid password")


def create_system_password_request(
        username,
        password,
        directory=SYSTEM_PASSWORD_REQUEST_DIRECTORY):
    _validate_password_request(username, password)
    remove_stale_private_token_files(
        directory,
        SYSTEM_PASSWORD_REQUEST_MAX_AGE,
    )
    token, unused_path = create_private_token_file(
        directory,
        json.dumps({"username": username, "password": password}),
    )
    return token


def consume_system_password_request(
        token,
        directory=SYSTEM_PASSWORD_REQUEST_DIRECTORY):
    serialized = read_private_token_file(
        token,
        directory,
        consume=True,
        max_age=SYSTEM_PASSWORD_REQUEST_MAX_AGE,
        max_bytes=4096,
    )
    try:
        payload = json.loads(serialized)
    except (TypeError, ValueError):
        raise ValueError("Invalid password request")
    if not isinstance(payload, dict) or set(payload) != {"username", "password"}:
        raise ValueError("Invalid password request")
    _validate_password_request(payload["username"], payload["password"])
    return payload


def apply_system_password(username, password):
    _validate_password_request(username, password)
    result = subprocess.run(
        ["/usr/sbin/chpasswd"],
        input="%s:%s\n" % (username, password),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("Unable to change system password")
