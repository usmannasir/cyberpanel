import fcntl
import hashlib
import hmac
import json
import os
import pwd
import re
import secrets
import stat
import time


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
PRIVATE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
EMAIL_REPORT_DIRECTORY = "/home/cyberpanel/.email-reports"
BACKUP_REQUEST_DIRECTORY = "/home/cyberpanel/.backup-requests"
FILE_DOWNLOAD_DIRECTORY = "/usr/local/lscp/cyberpanel/.file-downloads"
SYSTEM_PASSWORD_REQUEST_DIRECTORY = "/tmp/cyberpanel-system-password-requests"
TERMINAL_REQUEST_DIRECTORY = "/home/cyberpanel/.terminal-requests"
BACKUP_REQUEST_MAX_AGE = 300
TERMINAL_REQUEST_MAX_AGE = 15 * 60
SYSTEM_USER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
HOSTNAME_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
MYSQL_UPGRADE_STATUS_RE = re.compile(r"^mysql-upgrade-[A-Za-z0-9_.-]{1,80}$")
INVALID_API_TOKEN_VALUES = frozenset(("", "none", "null", "undefined"))
API_TOKEN_PREFIX = "cp_api_v1_"
API_TOKEN_RE = re.compile(r"^cp_api_v1_[A-Za-z0-9_-]{64}$")
API_OTP_FAILURE_LIMIT = 10
API_OTP_FAILURE_WINDOW = 5 * 60


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


def is_usable_api_token(token):
    return is_current_api_token(token)


def is_current_api_token(token):
    normalized = normalize_api_token(token).strip()
    if normalized.lower() in INVALID_API_TOKEN_VALUES:
        return False
    return API_TOKEN_RE.fullmatch(normalized) is not None


def generate_api_token():
    return "Basic %s%s" % (API_TOKEN_PREFIX, secrets.token_urlsafe(48))


def rotate_api_token(account):
    account.token = generate_api_token()
    account.save(update_fields=['token'])
    return account.token


def ensure_api_token(account):
    if is_current_api_token(account.token):
        return False
    rotate_api_token(account)
    return True


def api_token_matches(provided, stored):
    provided_token = normalize_api_token(provided)
    stored_token = normalize_api_token(stored)
    if not is_current_api_token(provided_token) or not is_current_api_token(stored_token):
        return False
    return constant_time_equal(provided_token, stored_token)


def _api_two_factor_code(request, data=None):
    code = request.META.get('HTTP_X_CYBERPANEL_OTP', '')
    if not code and data:
        for key in ('twofa', 'twoFactorCode', 'otp'):
            code = data.get(key, '')
            if code:
                break
    if not code and hasattr(request, 'POST'):
        for key in ('twofa', 'twoFactorCode', 'otp'):
            code = request.POST.get(key, '')
            if code:
                break
    return str(code).strip()


def _api_otp_cache_key(account, request):
    account_id = getattr(account, 'pk', None) or getattr(account, 'userName', '')
    remote_address = request.META.get('REMOTE_ADDR', '')
    key_material = '%s\0%s' % (account_id, remote_address)
    return 'cp_api_otp_%s' % hashlib.sha256(key_material.encode()).hexdigest()


def _record_api_otp_failure(cache, cache_key):
    if cache.add(cache_key, 1, API_OTP_FAILURE_WINDOW):
        return
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, API_OTP_FAILURE_WINDOW)


def api_two_factor_matches(account, request, data=None):
    if not getattr(account, 'twoFA', 0):
        return True

    from django.core.cache import cache

    cache_key = _api_otp_cache_key(account, request)
    if cache.get(cache_key, 0) >= API_OTP_FAILURE_LIMIT:
        return False

    code = _api_two_factor_code(request, data)
    secret = str(getattr(account, 'secretKey', '') or '').strip()
    if re.fullmatch(r'[0-9]{6}', code) is None or secret.lower() in INVALID_API_TOKEN_VALUES:
        _record_api_otp_failure(cache, cache_key)
        return False

    try:
        import pyotp
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            cache.delete(cache_key)
            return True
        _record_api_otp_failure(cache, cache_key)
        return False
    except Exception:
        _record_api_otp_failure(cache, cache_key)
        return False


def _read_secret_file(path):
    descriptor = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
            return ""
        if stat.S_IMODE(file_status.st_mode) != 0o600:
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "r") as secret_file:
            descriptor = None
            return secret_file.read().strip()
    except OSError:
        return ""
    finally:
        if descriptor is not None:
            os.close(descriptor)


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


def is_safe_system_user(value):
    return isinstance(value, str) and SYSTEM_USER_RE.fullmatch(value) is not None


def is_safe_hostname(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        return False
    labels = value.split('.')
    return len(labels) > 1 and all(
        HOSTNAME_LABEL_RE.fullmatch(label) is not None for label in labels
    )


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


def get_mysql_upgrade_status_path(status_file, base_path="/home/cyberpanel"):
    if not isinstance(status_file, str):
        return ""
    try:
        real_base = os.path.realpath(base_path)
        candidate = os.path.abspath(status_file)
        if os.path.dirname(candidate) != real_base:
            return ""
        if os.path.realpath(candidate) != candidate:
            return ""
        if MYSQL_UPGRADE_STATUS_RE.fullmatch(os.path.basename(candidate)) is None:
            return ""
        file_status = os.lstat(candidate)
        if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
            return ""
        if stat.S_IMODE(file_status.st_mode) & 0o077:
            return ""
        return candidate
    except (OSError, ValueError):
        return ""


def _owner_ids(owner_user):
    if owner_user is None:
        return None
    account = pwd.getpwnam(owner_user)
    return account.pw_uid, account.pw_gid


def _open_private_directory(directory, owner_user=None):
    directory = os.path.abspath(directory)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(directory, flags)
    file_status = os.fstat(descriptor)
    if not stat.S_ISDIR(file_status.st_mode):
        os.close(descriptor)
        raise OSError("Private storage is not a directory")
    owner_ids = _owner_ids(owner_user)
    if owner_ids is not None and os.geteuid() == 0:
        os.fchown(descriptor, owner_ids[0], owner_ids[1])
    os.fchmod(descriptor, 0o700)
    return descriptor


def _validate_private_token(token):
    if not isinstance(token, str) or PRIVATE_TOKEN_RE.fullmatch(token) is None:
        raise ValueError("Invalid private request token")
    return token


def create_private_token_file(directory, content="", owner_user=None):
    directory = os.path.abspath(directory)
    directory_fd = _open_private_directory(directory, owner_user)
    owner_ids = _owner_ids(owner_user)
    try:
        for unused_attempt in range(10):
            token = secrets.token_urlsafe(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
            try:
                descriptor = os.open(token, flags, 0o600, dir_fd=directory_fd)
            except FileExistsError:
                continue
            if owner_ids is not None and os.geteuid() == 0:
                os.fchown(descriptor, owner_ids[0], owner_ids[1])
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(str(content))
            return token, os.path.join(directory, token)
    finally:
        os.close(directory_fd)
    raise OSError("Unable to allocate private request token")


def read_private_token_file(token, directory, consume=False, max_age=None, max_bytes=1048576):
    token = _validate_private_token(token)
    directory_fd = _open_private_directory(directory)
    stored_name = token
    consumed_name = None
    try:
        if consume:
            consumed_name = ".consuming-%s-%s" % (token, secrets.token_urlsafe(12))
            os.rename(
                token,
                consumed_name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            stored_name = consumed_name

        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        descriptor = os.open(stored_name, flags, dir_fd=directory_fd)
        locked = False
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            locked = True
            file_status = os.fstat(descriptor)
            if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
                raise OSError("Private request is not a regular file")
            if max_age is not None and time.time() - file_status.st_mtime > max_age:
                raise ValueError("Private request expired")
            if file_status.st_size > max_bytes:
                raise ValueError("Private request is too large")

            chunks = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            if len(content) > max_bytes:
                raise ValueError("Private request is too large")
            return content.decode("utf-8")
        finally:
            if locked:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
    finally:
        if consumed_name is not None:
            try:
                os.unlink(consumed_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.close(directory_fd)


def remove_stale_private_token_files(directory, max_age):
    directory_fd = _open_private_directory(directory)
    removed = 0
    try:
        now = time.time()
        for name in os.listdir(directory_fd):
            if PRIVATE_TOKEN_RE.fullmatch(name) is None:
                continue
            try:
                file_status = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (stat.S_ISREG(file_status.st_mode) and file_status.st_nlink == 1
                        and now - file_status.st_mtime > max_age):
                    os.unlink(name, dir_fd=directory_fd)
                    removed += 1
            except FileNotFoundError:
                continue
    finally:
        os.close(directory_fd)
    return removed


def is_private_token_path(path, directory):
    if not isinstance(path, str):
        return False
    absolute_path = os.path.abspath(path)
    absolute_directory = os.path.abspath(directory)
    return (
        os.path.dirname(absolute_path) == absolute_directory
        and PRIVATE_TOKEN_RE.fullmatch(os.path.basename(absolute_path)) is not None
    )


def create_backup_request(domain, directory=BACKUP_REQUEST_DIRECTORY):
    domain = str(domain)
    if not domain or len(domain) > 255 or "\x00" in domain:
        raise ValueError("Invalid backup domain")
    remove_stale_private_token_files(directory, BACKUP_REQUEST_MAX_AGE)
    content = json.dumps({"domain": domain, "issued": int(time.time())})
    token, unused_path = create_private_token_file(
        directory,
        content,
        owner_user="cyberpanel",
    )
    return token


def consume_backup_request(token, domain, directory=BACKUP_REQUEST_DIRECTORY):
    try:
        content = read_private_token_file(
            token,
            directory,
            consume=True,
            max_age=BACKUP_REQUEST_MAX_AGE,
            max_bytes=4096,
        )
        request_data = json.loads(content)
        issued = int(request_data["issued"])
        age = time.time() - issued
        if age < -30 or age > BACKUP_REQUEST_MAX_AGE:
            return False
        return constant_time_equal(request_data.get("domain"), str(domain))
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False


def create_terminal_request(
        panel_user_id,
        ssh_user,
        directory=TERMINAL_REQUEST_DIRECTORY):
    panel_user_id = str(panel_user_id)
    ssh_user = str(ssh_user)
    if not is_safe_numeric_id(panel_user_id) or SYSTEM_USER_RE.fullmatch(ssh_user) is None:
        raise ValueError("Invalid terminal request identity")
    remove_stale_private_token_files(directory, TERMINAL_REQUEST_MAX_AGE)
    content = json.dumps({
        "panel_user_id": panel_user_id,
        "ssh_user": ssh_user,
        "issued": int(time.time()),
    })
    token, unused_path = create_private_token_file(
        directory,
        content,
        owner_user="cyberpanel",
    )
    return token


def consume_terminal_request(
        token,
        panel_user_id,
        ssh_user,
        directory=TERMINAL_REQUEST_DIRECTORY):
    try:
        content = read_private_token_file(
            token,
            directory,
            consume=True,
            max_age=TERMINAL_REQUEST_MAX_AGE,
            max_bytes=4096,
        )
        request_data = json.loads(content)
        issued = int(request_data["issued"])
        age = time.time() - issued
        if age < -30 or age > TERMINAL_REQUEST_MAX_AGE:
            return False
        return (
            constant_time_equal(
                request_data.get("panel_user_id"),
                str(panel_user_id),
            )
            and constant_time_equal(
                request_data.get("ssh_user"),
                str(ssh_user),
            )
        )
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False
