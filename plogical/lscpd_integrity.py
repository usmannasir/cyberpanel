"""
Verify bundled and installed lscpd binaries against the shipped checksum manifest.

Mitigates supply-chain tampering of panel daemon binaries copied from the CyberCP tree.
"""

from typing import Dict, Optional
import hashlib
import json
import os

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

CYBERCP_ROOT = '/usr/local/CyberCP'
MANIFEST_PATH = os.path.join(CYBERCP_ROOT, 'plogical', 'lscpd_checksums.json')
INSTALLED_PATH = '/usr/local/lscp/bin/lscpd'


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str = MANIFEST_PATH) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError('manifest must be a JSON object')
        return data
    except Exception as exc:
        logging.writeToFile(f'[lscpd_integrity] Failed to load manifest {path}: {exc}')
        return {}


def expected_checksum(binary_name: str, manifest: Optional[Dict] = None) -> str:
    manifest = manifest if manifest is not None else load_manifest()
    return (manifest.get(binary_name) or '').strip().lower()


def verify_bundled_binary(binary_name: str, cybercp_root: str = CYBERCP_ROOT) -> bool:
    """
    Return True when the bundled lscpd file matches the manifest SHA-256.
    Unknown binaries without a manifest entry are rejected.
    """
    manifest = load_manifest()
    expected = expected_checksum(binary_name, manifest)
    if not expected:
        logging.writeToFile(
            f'[lscpd_integrity] No checksum manifest entry for bundled binary {binary_name}'
        )
        return False

    source_path = os.path.join(cybercp_root, binary_name)
    if not os.path.isfile(source_path):
        logging.writeToFile(f'[lscpd_integrity] Bundled binary missing: {source_path}')
        return False

    actual = _sha256_file(source_path)
    if actual.lower() != expected:
        logging.writeToFile(
            f'[lscpd_integrity] Checksum mismatch for {binary_name}: expected {expected}, got {actual}'
        )
        return False

    logging.writeToFile(f'[lscpd_integrity] Verified bundled binary {binary_name}')
    return True


def verify_installed_binary(installed_path: str = INSTALLED_PATH, manifest: Optional[Dict] = None) -> bool:
    """
    Return True when the running lscpd binary matches any known-good manifest hash.
    """
    manifest = manifest if manifest is not None else load_manifest()
    if not manifest:
        logging.writeToFile('[lscpd_integrity] Cannot verify installed lscpd: empty manifest')
        return False
    if not os.path.isfile(installed_path):
        logging.writeToFile(f'[lscpd_integrity] Installed lscpd missing: {installed_path}')
        return False

    actual = _sha256_file(installed_path).lower()
    known = {value.lower() for value in manifest.values() if value}
    if actual not in known:
        logging.writeToFile(
            f'[lscpd_integrity] Installed lscpd hash not in manifest: {actual}'
        )
        return False

    logging.writeToFile('[lscpd_integrity] Installed lscpd matches known-good manifest hash')
    return True
