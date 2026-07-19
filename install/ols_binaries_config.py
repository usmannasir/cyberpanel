"""
OpenLiteSpeed binary configuration - single source of truth for OLS/ModSec URLs and SHA256 hashes.
Used by install/install.py, plogical/upgrade.py, and plogical/modSec.py.

Filename tokens like openlitespeed-2.5.1-x86_64-rhel9 are CyberPanel bundle IDs, not upstream
OpenLiteSpeed semver (see openlitespeed -v). Minimum upstream version before skipping this
overlay is defined in ols_version_policy.MIN_OFFICIAL_OLS.

Update this file when new OLS binaries are released.

OpenLiteSpeed v2.5.1 - Universal binaries with PHPConfig API, Origin Header Forwarding,
ReadApacheConf with Portmap, Auto-SSL ACME v2, ModSecurity ABI compatibility.
Core v2.5.1: HttpReq::getDocRoot NULL-vhost hardening - no module can crash the worker
on unmatched-Host 4xx responses.
Module v2.7.5: fixes the 4xx segfault on requests whose Host maps to no vhost
(2.7.0-2.7.3 all affected, Cloudflare 520 storms); adds a real ls_enabled 0 kill-switch.
NEVER ship module 2.7.0-2.7.3 again.
rhel9 artifact covers EL9 + EL10 (AlmaLinux 10); ubuntu artifact covers 22.04/24.04/26.04.
"""

BINARY_CONFIGS = {
    'rhel8': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.1-x86_64-rhel8',
        'sha256': 'd4ea7459997b4bed06f4a48ebd153e9dd96321e5548b9344f45adb984dfc87a0',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.5-x86_64-rhel8.so',
        'module_sha256': '48450ea904623110d643b85fb064d7a7da2e7713f33b3b19b71fd61f3b9a693c',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-rhel8.so',
        'modsec_sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.1-x86_64-rhel9',
        'sha256': '28423bf1076a2d36dab9955bab71e25768f69175f09edbf4f554ddfd5b9280a5',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.5-x86_64-rhel9.so',
        'module_sha256': 'ed1ab032484b05d00133c0f06e99f881e56bd33d8f145e1a5110e20215bc9aa0',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-rhel9.so',
        'modsec_sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/openlitespeed-2.5.1-x86_64-ubuntu',
        'sha256': 'd61e9c6f474495bcbe7803783ffe301779eaaeed833a5d607e7c65aa38ace5f2',
        'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.5-x86_64-ubuntu.so',
        'module_sha256': '61ef59ac7a46f3c9de7ec7156bbc4359a6dc5b12b3ffb03ea986a49895b70148',
        'modsec_url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-ubuntu.so',
        'modsec_sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}

# For plogical/modSec.py - compatible ModSecurity binaries (same as BINARY_CONFIGS modsec_*)
MODSEC_COMPATIBLE = {
    'rhel8': {
        'url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-rhel8.so',
        'sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
    },
    'rhel9': {
        'url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-rhel9.so',
        'sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
    },
    'ubuntu': {
        'url': 'https://cyberpanel.net/mod_security-2.5.1-x86_64-ubuntu.so',
        'sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
    },
}
