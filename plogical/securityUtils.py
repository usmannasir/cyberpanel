import hmac
import os
import re
import secrets


TERMINAL_JWT_SECRET_ENV = "CYBERPANEL_TERMINAL_JWT_SECRET"
TERMINAL_JWT_SECRET_FILE_ENV = "CYBERPANEL_TERMINAL_JWT_SECRET_FILE"
DEFAULT_TERMINAL_JWT_SECRET_FILE = "/usr/local/CyberCP/terminal_jwt_secret"
TERMINAL_JWT_ISSUER = "cyberpanel-web-terminal"
TERMINAL_JWT_AUDIENCE = "cyberpanel-fastapi-ssh"
MINIMUM_TERMINAL_JWT_SECRET_LENGTH = 32
SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
NUMERIC_ID_RE = re.compile(r"^[0-9]{1,12}$")
REMOTE_HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")
PORT_RE = re.compile(r"^[0-9]{1,5}$")


def constant_time_equal(left, right):
    if left is None or right is None:
        return False
    return hmac.compare_digest(str(left), str(right))


def normalize_api_token(token):
    if not token:
        return ""
    token = str(token).strip()
    if token.startswith("Bearer "):
        return token[7:].strip()
    if token.startswith("Basic "):
        return token[6:].strip()
    return token


def api_token_matches(provided, stored):
    provided_token = normalize_api_token(provided)
    stored_token = normalize_api_token(stored)
    if not provided_token or not stored_token:
        return False
    if constant_time_equal(provided_token, stored_token):
        return True
    return constant_time_equal(provided_token.rstrip("="), stored_token.rstrip("="))


def _read_secret_file(path):
    try:
        os.chmod(path, 0o600)
        with open(path, "r") as secret_file:
            return secret_file.read().strip()
    except OSError:
        return ""


def _create_secret_file(path):
    secret = secrets.token_urlsafe(48)
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, mode=0o700, exist_ok=True)

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w") as secret_file:
            secret_file.write(secret)
            secret_file.write("\n")
        return secret
    except FileExistsError:
        existing_secret = _read_secret_file(path)
        if existing_secret:
            return existing_secret
        raise RuntimeError("Web Terminal secret file is empty: %s" % path)
    except OSError as error:
        raise RuntimeError(
            "Unable to create Web Terminal secret file %s: %s" % (path, error)
        )


def _validate_terminal_jwt_secret(secret, source):
    if not secret:
        return ""
    if len(secret) < MINIMUM_TERMINAL_JWT_SECRET_LENGTH:
        raise RuntimeError("Web Terminal secret in %s is too short" % source)
    return secret


def get_terminal_jwt_secret(create_if_missing=False):
    env_secret = os.environ.get(TERMINAL_JWT_SECRET_ENV, "").strip()
    if env_secret:
        return _validate_terminal_jwt_secret(env_secret, TERMINAL_JWT_SECRET_ENV)

    secret_path = os.environ.get(TERMINAL_JWT_SECRET_FILE_ENV, DEFAULT_TERMINAL_JWT_SECRET_FILE)
    file_secret = _read_secret_file(secret_path)
    if file_secret:
        return _validate_terminal_jwt_secret(file_secret, secret_path)

    if create_if_missing:
        created_secret = _create_secret_file(secret_path)
        return _validate_terminal_jwt_secret(created_secret, secret_path)

    raise RuntimeError("Web Terminal secret is not configured: %s" % secret_path)


def is_safe_sql_identifier(value):
    if not isinstance(value, str):
        return False
    return SQL_IDENTIFIER_RE.match(value) is not None


def is_safe_numeric_id(value):
    return NUMERIC_ID_RE.match(str(value)) is not None


def is_safe_remote_host(value):
    if not isinstance(value, str):
        return False
    return REMOTE_HOST_RE.match(value) is not None


def is_safe_port(value):
    if not PORT_RE.match(str(value)):
        return False
    port = int(value)
    return 1 <= port <= 65535


def safe_path_under(base_path, *parts):
    try:
        real_base = os.path.realpath(base_path)
        candidate = os.path.realpath(os.path.join(real_base, *[str(part) for part in parts]))
        if os.path.commonpath([real_base, candidate]) != real_base:
            return ""
        return candidate
    except:
        return ""


def get_remote_transfer_dir_path(transfer_dir, base_path="/home/backup"):
    if not is_safe_numeric_id(transfer_dir):
        return ""

    return safe_path_under(base_path, "transfer-%s" % str(transfer_dir))


def get_remote_transfer_log_path(transfer_dir, base_path="/home/backup"):
    if not is_safe_numeric_id(transfer_dir):
        return ""

    return safe_path_under(base_path, "transfer-%s" % str(transfer_dir), "backup_log")


def get_remote_transfer_pid_path(transfer_dir, base_path="/home/backup"):
    if not is_safe_numeric_id(transfer_dir):
        return ""

    return safe_path_under(base_path, "transfer-%s" % str(transfer_dir), "pid")
