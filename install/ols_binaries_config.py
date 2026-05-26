"""
OpenLiteSpeed binary configuration - single source of truth for OLS/ModSec URLs and SHA256 hashes.
Used by install/install.py, plogical/upgrade.py, and plogical/modSec.py.

Filename tokens like openlitespeed-2.4.4-x86_64-rhel9 are CyberPanel bundle IDs, not upstream
OpenLiteSpeed semver (see openlitespeed -v). Minimum upstream version before skipping this
overlay is defined in ols_version_policy.MIN_OFFICIAL_OLS.

Update this file when new OLS binaries are released (e.g. v2.4.5).
"""
# OpenLiteSpeed v2.4.4 - Universal binaries with PHPConfig API, Origin Header Forwarding,
# ReadApacheConf with Portmap, Auto-SSL ACME v2, ModSecurity ABI compatibility.
# Updated Feb 2026: SSL listener auto-map fix, default VHost wildcard fix.
# Module v2.7.1: v2.7.0 directives (AddDefaultCharset, SSLRequireSSL, Satisfy, /,
# AuthGroupFile / Require group) plus performance work (.htaccess negative-cache,
# hook short-circuit). OLS binary stays at 2.4.4.

BINARY_CONFIGS = {
    'rhel8': {
        'url': 'https://cyberpanel.net/openlitespeed-2.4.4-x86_64-rhel8',
        'sha256': 'd08512da7a77468c09d6161de858db60bcc29aed7ce0abf76dca1c72104dc485',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.1-x86_64-rhel8.so',
        'module_sha256': '',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-rhel8.so',
        'modsec_sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/openlitespeed-2.4.4-x86_64-rhel9',
        'sha256': '418d2ea06e29c0f847a2e6cf01f7641d5fb72b65a04e27a8f6b3b54d673cc2df',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.1-x86_64-rhel9.so',
        'module_sha256': '',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-rhel9.so',
        'modsec_sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/openlitespeed-2.4.4-x86_64-ubuntu',
        'sha256': '60edf815379c32705540ad4525ea6d07c0390cabca232b6be12376ee538f4b1b',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.1-x86_64-ubuntu.so',
        'module_sha256': '',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-ubuntu.so',
        'modsec_sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}

# For plogical/modSec.py - compatible ModSecurity binaries (same as BINARY_CONFIGS modsec_*)
MODSEC_COMPATIBLE = {
    'rhel8': {
        'url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-rhel8.so',
        'sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-rhel9.so',
        'sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/mod_security-2.4.4-x86_64-ubuntu.so',
        'sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}
