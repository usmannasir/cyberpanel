# -*- coding: utf-8 -*-
"""
AES-256-CBC encryption for plugin <-> api.newstargeted.com communication.
Key must match PLUGIN_VERIFICATION_CIPHER_KEY in config.php on the API server.
"""
import json
import base64
import os

CIPHER_KEY_B64 = '1VLPEKTmLGUbIxHUFEtsuVM2MPN1tl8HPFtyJc4dr58='
ENCRYPTION_ENABLED = True

_ENCRYPTION_CIPHER_KEY = None


def _get_key():
    """Get 32-byte AES key from base64."""
    global _ENCRYPTION_CIPHER_KEY
    if _ENCRYPTION_CIPHER_KEY is not None:
        return _ENCRYPTION_CIPHER_KEY
    try:
        key = base64.b64decode(CIPHER_KEY_B64)
        if len(key) == 32:
            _ENCRYPTION_CIPHER_KEY = key
            return key
    except Exception:
        pass
    return None


def encrypt_payload(data):
    """Encrypt JSON payload for API request. Returns (body_bytes, headers_dict)."""
    if not ENCRYPTION_ENABLED or not _get_key():
        body = json.dumps(data, separators=(',', ':')).encode('utf-8')
        return body, {'Content-Type': 'application/json'}
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend
        key = _get_key()
        plain = json.dumps(data, separators=(',', ':')).encode('utf-8')
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plain) + padder.finalize()
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        payload = base64.b64encode(iv).decode('ascii') + '.' + base64.b64encode(ciphertext).decode('ascii')
        return payload.encode('utf-8'), {'Content-Type': 'text/plain', 'X-Encrypted': '1'}
    except Exception:
        body = json.dumps(data, separators=(',', ':')).encode('utf-8')
        return body, {'Content-Type': 'application/json'}


def decrypt_response(body_bytes, content_type='', expect_encrypted=False):
    """Decrypt API response. Handles both encrypted and plain JSON."""
    try:
        body_str = body_bytes.decode('utf-8') if isinstance(body_bytes, bytes) else str(body_bytes)
        is_encrypted = (
            expect_encrypted or
            ('text/plain' in content_type and '.' in body_str) or
            ('.' in body_str and body_str.strip() and body_str.strip()[0] not in '{[')
        )
        parts = body_str.strip().split('.', 1)
        if is_encrypted and len(parts) == 2 and ENCRYPTION_ENABLED and _get_key():
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.backends import default_backend
            iv = base64.b64decode(parts[0])
            ciphertext = base64.b64decode(parts[1])
            key = _get_key()
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plain = unpadder.update(padded) + unpadder.finalize()
            return json.loads(plain.decode('utf-8'))
        return json.loads(body_str)
    except Exception:
        try:
            return json.loads(body_bytes.decode('utf-8') if isinstance(body_bytes, bytes) else body_bytes)
        except Exception:
            return {}
