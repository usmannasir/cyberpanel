"""
Web Terminal SSH bridge (FastAPI + WebSocket).

JWT secret and claims are loaded from /etc/cyberpanel/fastapi_ssh_server.conf (see plogical.fastapi_ssh_config).
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import pwd
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import asyncssh
import paramiko
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

from plogical.fastapi_ssh_config import (
    CONF_PATH,
    DEFAULT_AUD,
    DEFAULT_ISS,
    is_strong_secret,
    read_conf_file_dict,
)

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger("cyberpanel.fastapi_ssh_server")

JWT_ALGORITHM = "HS256"
MAX_TOKEN_LIFETIME_SEC = 15 * 60


@dataclass
class RuntimeSettings:
    jwt_secret: str
    jwt_iss: str
    jwt_aud: str
    cors_origins: List[str]
    cors_origin_regex: Optional[str]


def _load_runtime_settings() -> RuntimeSettings:
    secret = (os.environ.get("JWT_SECRET") or "").strip()
    conf = read_conf_file_dict()
    if not secret:
        secret = (conf.get("JWT_SECRET") or "").strip()
    if not is_strong_secret(secret):
        _LOGGER.error(
            "Refusing to start: JWT_SECRET missing, weak, or known-insecure. "
            "Configure %s (chmod 600) with a random secret (32+ chars).",
            CONF_PATH,
        )
        sys.exit(1)

    iss = (os.environ.get("JWT_ISS") or conf.get("JWT_ISS") or DEFAULT_ISS).strip()
    aud = (os.environ.get("JWT_AUD") or conf.get("JWT_AUD") or DEFAULT_AUD).strip()
    origins_csv = (os.environ.get("ALLOWED_ORIGINS") or conf.get("ALLOWED_ORIGINS") or "").strip()
    origins = [o.strip() for o in origins_csv.split(",") if o.strip()]
    regex: Optional[str] = None
    if not origins:
        regex = r"https?://[\w\-.]+:8090$"
    return RuntimeSettings(
        jwt_secret=secret,
        jwt_iss=iss,
        jwt_aud=aud,
        cors_origins=origins,
        cors_origin_regex=regex,
    )


RUNTIME = _load_runtime_settings()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=RUNTIME.cors_origins if RUNTIME.cors_origins else [],
    allow_origin_regex=RUNTIME.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SSH_USER = "your_website_user"
AUTHORIZED_KEYS_PATH = f"/home/{SSH_USER}/.ssh/authorized_keys"


def get_ssh_port() -> int:
    try:
        with open("/etc/ssh/sshd_config", "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                line = line.split("#")[0].strip()
                parts = line.split()
                if len(parts) >= 2 and parts[0].lower() == "port":
                    port = int(parts[1])
                    _LOGGER.info("[get_ssh_port] SSH port detected: %s", port)
                    return port
    except Exception as exc:
        _LOGGER.warning("[get_ssh_port] Could not read sshd_config: %s", exc)
    _LOGGER.warning("[get_ssh_port] Falling back to default port 22")
    return 22


SSH_PORT = get_ssh_port()


def generate_ssh_keypair():
    key = paramiko.RSAKey.generate(2048)
    private_io = io.StringIO()
    key.write_private_key(private_io)
    private_key = private_io.getvalue()
    public_key = "%s %s" % (key.get_name(), key.get_base64())
    return private_key, public_key


def add_key_to_authorized_keys(public_key, comment):
    entry = 'from="127.0.0.1,::1" %s %s\n' % (public_key, comment)
    with open(AUTHORIZED_KEYS_PATH, "a", encoding="utf-8") as handle:
        handle.write(entry)


def remove_key_from_authorized_keys(comment):
    with open(AUTHORIZED_KEYS_PATH, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    with open(AUTHORIZED_KEYS_PATH, "w", encoding="utf-8") as handle:
        for line in lines:
            if comment not in line:
                handle.write(line)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(None), ssh_user: str = Query(None)
):
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = jwt.decode(
            token,
            RUNTIME.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=RUNTIME.jwt_aud,
            issuer=RUNTIME.jwt_iss,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "require_exp": True,
                "verify_iat": True,
                "require_iat": True,
            },
        )
    except JWTError:
        await websocket.close(code=4403)
        return

    user = payload.get("ssh_user")
    if not user or not isinstance(user, str):
        await websocket.close(code=4403)
        return
    if ssh_user is not None and ssh_user != user:
        _LOGGER.warning("ssh_user query claim does not match token; rejecting.")
        await websocket.close(code=4403)
        return

    iat = payload.get("iat")
    exp = payload.get("exp")
    try:
        if iat is None or exp is None:
            raise ValueError("missing iat/exp")
        if int(exp) - int(iat) > MAX_TOKEN_LIFETIME_SEC:
            raise ValueError("token lifetime too long")
    except (TypeError, ValueError):
        await websocket.close(code=4403)
        return

    try:
        pwd.getpwnam(user)
    except KeyError:
        _LOGGER.warning("Unknown ssh_user in token.")
        await websocket.close(code=4403)
        return

    home_dir = pwd.getpwnam(user).pw_dir
    ssh_dir = os.path.join(home_dir, ".ssh")
    authorized_keys_path = os.path.join(ssh_dir, "authorized_keys")

    os.makedirs(ssh_dir, exist_ok=True)
    if not os.path.exists(authorized_keys_path):
        with open(authorized_keys_path, "w", encoding="utf-8"):
            pass
    os.chown(ssh_dir, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
    os.chmod(ssh_dir, 0o700)
    os.chown(authorized_keys_path, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
    os.chmod(authorized_keys_path, 0o600)

    private_key, public_key = generate_ssh_keypair()
    comment = "webterm-%s" % (os.urandom(8).hex(),)
    entry = 'from="127.0.0.1,::1" %s %s\n' % (public_key, comment)
    with open(authorized_keys_path, "a", encoding="utf-8") as handle:
        handle.write(entry)

    with tempfile.NamedTemporaryFile(delete=False) as keyfile:
        keyfile.write(private_key.encode())
        keyfile_path = keyfile.name

    await websocket.accept()
    conn = None
    process = None
    try:
        conn = await asyncssh.connect(
            "127.0.0.1",
            port=SSH_PORT,
            username=user,
            client_keys=[keyfile_path],
            known_hosts=None,
        )
        process = await conn.create_process(term_type="xterm")

        async def ws_to_ssh():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    process.stdin.write(data.decode("utf-8", errors="replace"))
            except WebSocketDisconnect:
                process.stdin.close()

        async def ssh_to_ws():
            try:
                while not process.stdout.at_eof():
                    data = await process.stdout.read(1024)
                    if data:
                        _LOGGER.debug(
                            "[ssh_to_ws] Sending to WS: type=%s", type(data).__name__
                        )
                        if isinstance(data, bytes):
                            await websocket.send_bytes(data)
                        elif isinstance(data, str):
                            await websocket.send_text(data)
                        else:
                            await websocket.send_text(str(data))
            except Exception as exc:
                _LOGGER.exception("[ssh_to_ws] Exception: %s", exc)

        await asyncio.gather(ws_to_ssh(), ssh_to_ws())
    except Exception as exc:
        try:
            msg = "Connection error: %s" % (exc,)
            _LOGGER.exception("[websocket_endpoint] Exception: %s", exc)
            await websocket.send_text(str(msg))
        except Exception as send_exc:
            _LOGGER.exception(
                "[websocket_endpoint] Error sending error message: %s", send_exc
            )
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        with open(authorized_keys_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        with open(authorized_keys_path, "w", encoding="utf-8") as handle:
            for line in lines:
                if comment not in line:
                    handle.write(line)
        try:
            os.remove(keyfile_path)
        except OSError:
            pass
        if process:
            process.close()
        if conn:
            conn.close()
