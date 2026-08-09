import asyncio
import asyncssh
import fcntl
import tempfile
import os
import stat
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import paramiko  # For key generation and manipulation
import io
import pwd
import subprocess
from jose import jwt, JWTError
import logging
from plogical.securityUtils import (
    TERMINAL_JWT_AUDIENCE,
    TERMINAL_JWT_ISSUER,
    consume_terminal_request,
    get_terminal_jwt_secret,
)

app = FastAPI()
JWT_SECRET = get_terminal_jwt_secret(create_if_missing=True)
JWT_ALGORITHM = "HS256"
MAX_TOKEN_LIFETIME_SECONDS = 15 * 60

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("CYBERPANEL_TERMINAL_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ssh_port_from_text(content):
    for raw_line in content.splitlines():
        line = raw_line.partition("#")[0].strip()
        parts = line.split()
        if len(parts) < 2 or parts[0].lower() != "port":
            continue
        try:
            port = int(parts[1])
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            return port
    return None


def get_ssh_port():
    try:
        result = subprocess.run(
            ["/usr/sbin/sshd", "-T"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            port = _ssh_port_from_text(result.stdout)
            if port is not None:
                return port
    except (OSError, subprocess.SubprocessError) as error:
        logging.warning("Unable to read effective SSH configuration: %s", error)

    try:
        with open("/etc/ssh/sshd_config", "r", encoding="utf-8") as config:
            port = _ssh_port_from_text(config.read())
            if port is not None:
                return port
    except OSError as error:
        logging.warning("Unable to read SSH configuration: %s", error)

    logging.warning("Unable to determine the SSH port; using port 22")
    return 22


SSH_PORT = get_ssh_port()

# Helper to generate a keypair
def generate_ssh_keypair():
    key = paramiko.RSAKey.generate(2048)
    private_io = io.StringIO()
    key.write_private_key(private_io)
    private_key = private_io.getvalue()
    public_key = f"{key.get_name()} {key.get_base64()}"
    return private_key, public_key

def _write_all(descriptor, content):
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("Unable to update authorized_keys")
        remaining = remaining[written:]


def open_authorized_keys(account, allowed_home_root="/home"):
    home_root = os.path.realpath(allowed_home_root)
    home_dir = os.path.abspath(account.pw_dir)
    try:
        if os.path.commonpath([home_root, home_dir]) != home_root:
            raise PermissionError("Web Terminal account home is outside /home")
    except ValueError as error:
        raise PermissionError("Invalid Web Terminal account home") from error
    if os.path.realpath(home_dir) != home_dir:
        raise PermissionError("Web Terminal account home cannot contain symlinks")

    home_stat = os.lstat(home_dir)
    if not stat.S_ISDIR(home_stat.st_mode):
        raise PermissionError("Web Terminal account home must be a directory")

    ssh_dir = os.path.join(home_dir, ".ssh")
    ssh_created = False
    try:
        ssh_descriptor = os.open(
            ssh_dir,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    except FileNotFoundError:
        try:
            os.mkdir(ssh_dir, 0o700)
            ssh_created = True
        except FileExistsError:
            pass
        ssh_descriptor = os.open(
            ssh_dir,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )

    try:
        ssh_stat = os.fstat(ssh_descriptor)
        if not stat.S_ISDIR(ssh_stat.st_mode):
            raise PermissionError("Web Terminal SSH path must be a directory")
        if not ssh_created and ssh_stat.st_uid != account.pw_uid:
            raise PermissionError("Web Terminal SSH directory has an unexpected owner")
        os.fchown(ssh_descriptor, account.pw_uid, account.pw_gid)
        os.fchmod(ssh_descriptor, 0o700)

        key_created = False
        try:
            key_descriptor = os.open(
                "authorized_keys",
                os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=ssh_descriptor,
            )
        except FileNotFoundError:
            key_descriptor = os.open(
                "authorized_keys",
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=ssh_descriptor,
            )
            key_created = True

        try:
            key_stat = os.fstat(key_descriptor)
            if not stat.S_ISREG(key_stat.st_mode) or key_stat.st_nlink != 1:
                raise PermissionError("Web Terminal authorized_keys must be a regular file")
            if not key_created and key_stat.st_uid != account.pw_uid:
                raise PermissionError("Web Terminal authorized_keys has an unexpected owner")
            os.fchown(key_descriptor, account.pw_uid, account.pw_gid)
            os.fchmod(key_descriptor, 0o600)
            return key_descriptor
        except BaseException:
            os.close(key_descriptor)
            raise
    finally:
        os.close(ssh_descriptor)


def add_ephemeral_key(key_descriptor, public_key, comment):
    entry = f'from="127.0.0.1,::1" {public_key} {comment}\n'.encode()
    fcntl.flock(key_descriptor, fcntl.LOCK_EX)
    try:
        os.lseek(key_descriptor, 0, os.SEEK_END)
        _write_all(key_descriptor, entry)
        os.fsync(key_descriptor)
    finally:
        fcntl.flock(key_descriptor, fcntl.LOCK_UN)


def remove_ephemeral_key(key_descriptor, comment):
    marker = (" " + comment).encode()
    fcntl.flock(key_descriptor, fcntl.LOCK_EX)
    try:
        os.lseek(key_descriptor, 0, os.SEEK_SET)
        chunks = []
        while True:
            chunk = os.read(key_descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        lines = b"".join(chunks).splitlines(keepends=True)
        updated = b"".join(
            line for line in lines
            if not line.rstrip(b"\r\n").endswith(marker)
        )
        os.ftruncate(key_descriptor, 0)
        os.lseek(key_descriptor, 0, os.SEEK_SET)
        _write_all(key_descriptor, updated)
        os.fsync(key_descriptor)
    finally:
        fcntl.flock(key_descriptor, fcntl.LOCK_UN)


def decode_terminal_token(token):
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        audience=TERMINAL_JWT_AUDIENCE,
        issuer=TERMINAL_JWT_ISSUER,
        options={
            "verify_signature": True,
            "verify_aud": True,
            "require_aud": True,
            "verify_iss": True,
            "require_iss": True,
            "verify_exp": True,
            "require_exp": True,
            "verify_iat": True,
            "require_iat": True,
            "verify_nbf": True,
            "require_nbf": True,
        },
    )

    try:
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError) as error:
        raise JWTError("Invalid Web Terminal token timestamps") from error
    if expires_at <= issued_at or expires_at - issued_at > MAX_TOKEN_LIFETIME_SECONDS:
        raise JWTError("Invalid Web Terminal token lifetime")

    request_token = payload.get("jti")
    panel_user_id = payload.get("sub")
    ssh_user = payload.get("ssh_user")
    if not consume_terminal_request(
            request_token,
            panel_user_id,
            ssh_user):
        raise JWTError("Invalid or expired Web Terminal request")

    return payload


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None), ssh_user: str = Query(None)):
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_terminal_token(token)
        user = payload.get("ssh_user")
        if not user or not isinstance(user, str):
            await websocket.close(code=4403)
            return
    except JWTError:
        await websocket.close(code=4403)
        return

    if ssh_user is not None and ssh_user != user:
        await websocket.close(code=4403)
        return

    try:
        account = pwd.getpwnam(user)
    except KeyError:
        await websocket.close(code=4403)
        return

    if account.pw_uid == 0:
        await websocket.close(code=4403)
        return

    key_descriptor = None
    keyfile_path = None
    comment = None
    key_added = False
    try:
        key_descriptor = open_authorized_keys(account)
        private_key, public_key = generate_ssh_keypair()
        comment = f"webterm-{os.urandom(8).hex()}"
        add_ephemeral_key(key_descriptor, public_key, comment)
        key_added = True

        with tempfile.NamedTemporaryFile(delete=False) as keyfile:
            keyfile.write(private_key.encode())
            keyfile_path = keyfile.name
    except Exception as error:
        logging.warning("Web Terminal account preparation rejected: %s", error)
        if key_added:
            try:
                remove_ephemeral_key(key_descriptor, comment)
            except OSError:
                logging.exception("Unable to remove rejected Web Terminal key")
        if key_descriptor is not None:
            os.close(key_descriptor)
        if keyfile_path is not None:
            try:
                os.unlink(keyfile_path)
            except OSError:
                pass
        await websocket.close(code=4403)
        return

    conn = None
    process = None
    try:
        await websocket.accept()
        conn = await asyncssh.connect(
            "127.0.0.1",
            port=SSH_PORT,
            username=user,
            client_keys=[keyfile_path],
            known_hosts=None
        )
        process = await conn.create_process(term_type="xterm")

        async def ws_to_ssh():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    # Decode bytes to str before writing to SSH stdin
                    process.stdin.write(data.decode('utf-8', errors='replace'))
            except WebSocketDisconnect:
                process.stdin.close()

        async def ssh_to_ws():
            try:
                while not process.stdout.at_eof():
                    data = await process.stdout.read(1024)
                    if data:
                        if isinstance(data, bytes):
                            await websocket.send_bytes(data)
                        elif isinstance(data, str):
                            await websocket.send_text(data)
                        else:
                            await websocket.send_text(str(data))
            except Exception as ex:
                logging.exception(f"[ssh_to_ws] Exception: {ex}")
                pass

        await asyncio.gather(ws_to_ssh(), ssh_to_ws())
    except Exception as e:
        try:
            # Always send error as text (string)
            msg = f"Connection error: {e}"
            logging.exception(f"[websocket_endpoint] Exception: {e}")
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            await websocket.send_text(str(msg))
        except Exception as ex:
            logging.exception(f"[websocket_endpoint] Error sending error message: {ex}")
            pass
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        try:
            remove_ephemeral_key(key_descriptor, comment)
        except OSError:
            logging.exception("Unable to remove Web Terminal key")
        os.close(key_descriptor)
        try:
            os.unlink(keyfile_path)
        except OSError:
            pass
        if process:
            process.close()
        if conn:
            conn.close()
