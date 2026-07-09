import asyncio
import asyncssh
import tempfile
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import paramiko  # For key generation and manipulation
import io
import pwd
from jose import jwt, JWTError
import logging
from plogical.securityUtils import get_terminal_jwt_secret

app = FastAPI()
JWT_SECRET = get_terminal_jwt_secret(create_if_missing=True)
JWT_ALGORITHM = "HS256"

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

SSH_USER = "your_website_user"  # Replace with a real user for testing
AUTHORIZED_KEYS_PATH = f"/home/{SSH_USER}/.ssh/authorized_keys"

# Helper to generate a keypair
def generate_ssh_keypair():
    key = paramiko.RSAKey.generate(2048)
    private_io = io.StringIO()
    key.write_private_key(private_io)
    private_key = private_io.getvalue()
    public_key = f"{key.get_name()} {key.get_base64()}"
    return private_key, public_key

# Add public key to authorized_keys with a unique comment
def add_key_to_authorized_keys(public_key, comment):
    entry = f'from="127.0.0.1,::1" {public_key} {comment}\n'
    with open(AUTHORIZED_KEYS_PATH, "a") as f:
        f.write(entry)

# Remove public key from authorized_keys by comment
def remove_key_from_authorized_keys(comment):
    with open(AUTHORIZED_KEYS_PATH, "r") as f:
        lines = f.readlines()
    with open(AUTHORIZED_KEYS_PATH, "w") as f:
        for line in lines:
            if comment not in line:
                f.write(line)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None), ssh_user: str = Query(None)):
    # Re-enable JWT validation
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = payload.get("ssh_user")
        if not user:
            await websocket.close()
            return
    except JWTError:
        await websocket.close()
        return
    home_dir = pwd.getpwnam(user).pw_dir
    ssh_dir = os.path.join(home_dir, ".ssh")
    authorized_keys_path = os.path.join(ssh_dir, "authorized_keys")

    os.makedirs(ssh_dir, exist_ok=True)
    if not os.path.exists(authorized_keys_path):
        with open(authorized_keys_path, "w"): pass
    os.chown(ssh_dir, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
    os.chmod(ssh_dir, 0o700)
    os.chown(authorized_keys_path, pwd.getpwnam(user).pw_uid, pwd.getpwnam(user).pw_gid)
    os.chmod(authorized_keys_path, 0o600)

    private_key, public_key = generate_ssh_keypair()
    comment = f"webterm-{os.urandom(8).hex()}"
    entry = f'from="127.0.0.1,::1" {public_key} {comment}\n'
    with open(authorized_keys_path, "a") as f:
        f.write(entry)

    with tempfile.NamedTemporaryFile(delete=False) as keyfile:
        keyfile.write(private_key.encode())
        keyfile_path = keyfile.name

    await websocket.accept()
    conn = None
    process = None
    try:
        conn = await asyncssh.connect(
            "localhost",
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
                        # Defensive type check and logging
                        logging.debug(f"[ssh_to_ws] Sending to WS: type={type(data)}, sample={data[:40] if isinstance(data, bytes) else data}")
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
        # Remove key from authorized_keys and delete temp private key
        with open(authorized_keys_path, "r") as f:
            lines = f.readlines()
        with open(authorized_keys_path, "w") as f:
            for line in lines:
                if comment not in line:
                    f.write(line)
        os.remove(keyfile_path)
        if process:
            process.close()
        if conn:
            conn.close()
