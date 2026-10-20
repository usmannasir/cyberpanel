"""Choose the bundled panel server for the host's actual ABI."""
import os
import platform
import re


def host_glibc_version():
    """Prefer libc's own version over distribution release-name guesses."""
    try:
        value = os.confstr('CS_GNU_LIBC_VERSION') or ''
    except (AttributeError, OSError, ValueError):
        value = ''
    match = re.fullmatch(r'glibc\s+(\d+)\.(\d+)(?:\.\d+)*', value.strip())
    if match:
        return tuple(int(part) for part in match.groups())
    name, version = platform.libc_ver()
    match = re.fullmatch(r'(\d+)\.(\d+)(?:\.\d+)*', version)
    if name == 'glibc' and match:
        return tuple(int(part) for part in match.groups())
    return None


def select_lscpd_binary(machine=None, glibc_version=None):
    """Use 0.4.0 on compatible x86 hosts; keep legacy glibc hosts bootable.

    The bundled x86 0.4.0 ELF requires GLIBC_2.25. Both x86 binaries
    require libcrypt.so.1, so this does not add a new crypt ABI dependency.
    """
    machine = (machine or platform.machine()).lower()
    if machine in ('aarch64', 'arm64'):
        return 'lscpd.aarch64'
    if machine not in ('x86_64', 'amd64'):
        raise RuntimeError('No bundled lscpd binary supports architecture %s' % machine)
    version = glibc_version if glibc_version is not None else host_glibc_version()
    if version is not None and version >= (2, 25):
        return 'lscpd.0.4.0'
    return 'lscpd-0.3.1'
