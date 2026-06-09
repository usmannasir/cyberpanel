"""
OpenLiteSpeed binary configuration - single source of truth for OLS/ModSec URLs and SHA256 hashes.
Used by install/install.py, plogical/upgrade.py, and plogical/modSec.py.

Filename tokens like openlitespeed-2.5.0-x86_64-rhel9 are CyberPanel bundle IDs, not upstream
OpenLiteSpeed semver (see openlitespeed -v). Minimum upstream version before skipping this
overlay is defined in ols_version_policy.MIN_OFFICIAL_OLS.

Update this file when new OLS binaries are released (e.g. v2.5.1).
"""
# OpenLiteSpeed v2.5.0 - Universal binaries with PHPConfig API, Origin Header Forwarding,
# ReadApacheConf with Portmap, Auto-SSL ACME v2, ModSecurity ABI compatibility.
# Module v2.7.3: preserves Content-Encoding on LSCache hits.
# rhel9 artifact covers EL9 + EL10 (AlmaLinux 10); ubuntu artifact covers 22.04/24.04.

BINARY_CONFIGS = {
    'rhel8': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-rhel8',
        'sha256': '48c8423edfaec3fe1b6eee118925ed3ac55314c53e9bdf2e5bdd4960c4806a62',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-rhel8.so',
        'module_sha256': '83111c8a3310b40e998070b07002a205975a06e09c6e0f8e8054e8d18b8682e1',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel8.so',
        'modsec_sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-rhel9',
        'sha256': '780163ee7c0304c9b1db6abaeeaca2e58dbfc05436de776e921ca1d493462596',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-rhel9.so',
        'module_sha256': 'a189da7ec5c09c5ba836209aa10746b691bbef21010cbe4c4c622614cf03c5e1',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel9.so',
        'modsec_sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-ubuntu',
        'sha256': '2a836d4bf17fe5152d15dd60fd3817c1d3c294b48b35f12b776fa2efb7771422',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-ubuntu.so',
        'module_sha256': 'f1c1ab881625fa6fe6545e45283220e86245a1e3c96e29c4d86af9ab15fd6c2b',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-ubuntu.so',
        'modsec_sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}

# For plogical/modSec.py - compatible ModSecurity binaries (same as BINARY_CONFIGS modsec_*)
MODSEC_COMPATIBLE = {
    'rhel8': {
        'url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel8.so',
        'sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel9.so',
        'sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-ubuntu.so',
        'sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}
