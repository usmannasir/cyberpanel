import hmac
import os
import re
import secrets


LEGACY_TERMINAL_JWT_SECRET = "DAsjK2gl50PE09d1N3uZPTQ6JdwwfiuhlyWKMVbUEpc"
TERMINAL_JWT_SECRET_ENV = "CYBERPANEL_TERMINAL_JWT_SECRET"
TERMINAL_JWT_SECRET_FILE_ENV = "CYBERPANEL_TERMINAL_JWT_SECRET_FILE"
DEFAULT_TERMINAL_JWT_SECRET_FILE = "/usr/local/CyberCP/terminal_jwt_secret"
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
        return _read_secret_file(path)
    except OSError:
        return ""


def get_terminal_jwt_secret(create_if_missing=False):
    env_secret = os.environ.get(TERMINAL_JWT_SECRET_ENV, "").strip()
    if env_secret:
        return env_secret

    secret_path = os.environ.get(TERMINAL_JWT_SECRET_FILE_ENV, DEFAULT_TERMINAL_JWT_SECRET_FILE)
    file_secret = _read_secret_file(secret_path)
    if file_secret:
        return file_secret

    if create_if_missing:
        created_secret = _create_secret_file(secret_path)
        if created_secret:
            return created_secret

    return LEGACY_TERMINAL_JWT_SECRET


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
