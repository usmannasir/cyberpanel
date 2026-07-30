#!/usr/bin/env python3
"""Regression test for GitHub usmannasir/cyberpanel#1847.

Installed fullchain.pem files with trailing non-UTF-8 bytes must still load
via binary open + OpenSSL, while text-mode open raises UnicodeDecodeError.
"""
from __future__ import print_function

import os
import ssl
import sys
import tempfile

try:
    import OpenSSL
except ImportError:
    print('SKIP: pyOpenSSL not installed')
    sys.exit(0)


def _make_pem_bytes():
    # Self-signed cert via stdlib (no openssl CLI required)
    from datetime import datetime, timedelta
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        # Fallback: openssl CLI
        d = tempfile.mkdtemp()
        key = os.path.join(d, 'key.pem')
        cert = os.path.join(d, 'cert.pem')
        cmd = (
            'openssl req -x509 -nodes -days 1 -newkey rsa:2048 '
            '-keyout {k} -out {c} -subj /CN=test.example'.format(k=key, c=cert)
        )
        if os.system(cmd + ' >/dev/null 2>&1') != 0:
            print('FAIL: could not generate test certificate')
            sys.exit(1)
        with open(cert, 'rb') as f:
            return f.read()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u'test.example')])
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


def main():
    pem = _make_pem_bytes()
    if b'-----BEGIN CERTIFICATE-----' not in pem or b'-----END CERTIFICATE-----' not in pem:
        print('FAIL: generated PEM missing markers')
        return 1

    garbage = b'\xf9\x00garbage'
    corrupt = pem.rstrip(b'\n') + b'\n' + garbage

    fd, path = tempfile.mkstemp(prefix='fullchain1847_', suffix='.pem')
    os.close(fd)
    try:
        with open(path, 'wb') as f:
            f.write(corrupt)

        # Text mode must fail (documents the bug)
        text_failed = False
        try:
            with open(path, 'r') as f:
                f.read()
        except UnicodeDecodeError:
            text_failed = True
        if not text_failed:
            print('FAIL: expected UnicodeDecodeError on text-mode read')
            return 1

        # Binary mode + OpenSSL must succeed (the fix)
        data = open(path, 'rb').read()
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, data)
        cn = None
        for component in x509.get_subject().get_components():
            if component[0].decode('utf-8') == 'CN':
                cn = component[1].decode('utf-8')
                break
        if cn != 'test.example':
            print('FAIL: unexpected CN: %r' % (cn,))
            return 1

        print('PASS: #1847 binary PEM load tolerates trailing garbage')
        return 0
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


if __name__ == '__main__':
    sys.exit(main())
