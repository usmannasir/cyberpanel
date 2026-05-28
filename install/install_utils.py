#!/usr/bin/env python
"""
Common utility functions for CyberPanel installation scripts.
This module contains shared functions used by both install.py and installCyberPanel.py
"""

import os
import glob
import sys
import shutil
import time
import logging
import subprocess
import shlex
import secrets
import string
from os.path import exists


def FetchCloudLinuxAlmaVersionVersion():
    """
    Detect CloudLinux or AlmaLinux version by parsing /etc/os-release
    Returns: version string or -1 if not found
    """
    if os.path.exists('/etc/os-release'):
        data = open('/etc/os-release', 'r').read()
        if (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.9') > -1 or data.find('Anatoly Levchenko') > -1 or data.find('VERSION="8.') > -1):
            return 'cl-89'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.8') > -1 or data.find('Anatoly Filipchenko') > -1):
            return 'cl-88'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('9.4') > -1 or data.find('VERSION="9.') > -1):
            return 'cl-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.9') > -1 or data.find('Midnight Oncilla') > -1 or data.find('VERSION="8.') > -1):
            return 'al-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.7') > -1 or data.find('Stone Smilodon') > -1):
            return 'al-87'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('9.4') > -1 or data.find('9.3') > -1 or data.find('Shamrock Pampas') > -1 or data.find('Seafoam Ocelot') > -1 or data.find('VERSION="9.') > -1):
            return 'al-93'
        elif data.find('CentOS Stream 9') > -1:
            return 'el-9'
        elif data.find('CentOS Linux 9') > -1:
            return 'el-9'
        elif data.find('Rocky Linux 9') > -1:
            return 'el-9'
        elif data.find('Red Hat Enterprise Linux 9') > -1:
            return 'el-9'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('10.0') > -1 or data.find('Purple Lion') > -1 or data.find('VERSION="10.') > -1):
            return 'al-100'
    else:
        return -1


def get_Ubuntu_release(use_print=False, exit_on_error=True):
    """
    Get Ubuntu release version from /etc/lsb-release

    Args:
        use_print: If True, use print() for errors, otherwise use the provided output function
        exit_on_error: If True, exit on error

    Returns: float release number or -1 if not found
    """
    release = -1
    if exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line[:16] == "DISTRIB_RELEASE=":
                    release = float(line[16:])

        if release == -1:
            error_msg = "Can't find distro release name in " + distro_file + " - fatal error"
            if use_print:
                print(error_msg)
            else:
                # This will be overridden by the calling module
                return -1

    else:
        error_msg = "Can't find linux release file - fatal error"
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(error_msg)
        if use_print:
            print(error_msg)
        if exit_on_error:
            os._exit(os.EX_UNAVAILABLE)

    return release


def get_Debian_version():
    """
    Get Debian version from /etc/debian_version

    Returns: float version number or -1 if not found
    """
    if exists("/etc/debian_version"):
        try:
            with open("/etc/debian_version", 'r') as f:
                version_str = f.read().strip()
                # Extract numeric version (e.g., "13.8" from "13.8" or "13" from "13/sid")
                if '/' in version_str:
                    version_str = version_str.split('/')[0]
                try:
                    return float(version_str)
                except ValueError:
                    # Handle non-numeric versions like "bookworm/sid"
                    if 'bookworm' in version_str.lower():
                        return 12.0
                    elif 'trixie' in version_str.lower():
                        return 13.0
                    elif 'bullseye' in version_str.lower():
                        return 11.0
                    else:
                        return -1
        except Exception:
            return -1
    return -1


def is_debian():
    """
    Check if the system is Debian (not Ubuntu)

    Returns: bool indicating if it's Debian
    """
    if exists("/etc/debian_version") and not exists("/etc/lsb-release"):
        return True
    return False


def get_debian_mariadb_packages():
    """
    Get appropriate MariaDB packages for Debian based on version

    Returns: dict with package mappings
    """
    debian_version = get_Debian_version()

    # Package mappings for different Debian versions
    if debian_version >= 13.0:
        # Debian 13 (Trixie) uses newer package names
        return {
            'libmariadbclient-dev': 'libmariadb-dev-compat libmariadb-dev',
            'python-mysqldb': 'python3-mysqldb',
            'python-dev': 'python3-dev',
            'python-pip': 'python3-pip',
            'python-setuptools': 'python3-setuptools',
            'python-minimal': '',  # Not needed in newer versions
            'python-gpg': 'python3-gpg',
            'python': 'python3',
            'dovecot-pigeonhole': 'dovecot-sieve',
            'pdns': 'pdns-server',
            'pdns-backend-mysql': 'pdns-backend-mysql',
            'firewalld': 'firewalld'
        }
    elif debian_version >= 12.0:
        # Debian 12 (Bookworm)
        return {
            'libmariadbclient-dev': 'libmariadb-dev',
            'python-mysqldb': 'python3-mysqldb',
            'python-dev': 'python3-dev',
            'python-pip': 'python3-pip',
            'python-setuptools': 'python3-setuptools',
            'python-minimal': '',
            'python-gpg': 'python3-gpg',
            'python': 'python3',
            'dovecot-pigeonhole': 'dovecot-sieve',
            'pdns': 'pdns-server',
            'pdns-backend-mysql': 'pdns-backend-mysql',
            'firewalld': 'firewalld'
        }
    else:
        # Older Debian versions (11 and below)
        return {
            'libmariadbclient-dev': 'libmariadbclient-dev',
            'python-mysqldb': 'python-mysqldb',
            'python-dev': 'python-dev',
            'python-pip': 'python-pip',
            'python-setuptools': 'python-setuptools',
            'python-minimal': 'python-minimal',
            'python-gpg': 'python-gpg',
            'python': 'python'
        }


# ANSI color codes
class Colors:
    HEADER = '\033[95m'      # Purple
    INFO = '\033[94m'        # Blue
    SUCCESS = '\033[92m'     # Green
    WARNING = '\033[93m'     # Yellow
    ERROR = '\033[91m'       # Red
    ENDC = '\033[0m'         # Reset
    BOLD = '\033[1m'         # Bold
    UNDERLINE = '\033[4m'    # Underline


def get_message_color(message):
    """
    Determine the appropriate color based on message content
    
    Args:
        message: The message to analyze
        
    Returns:
        str: ANSI color code
    """
    message_lower = message.lower()
    
    # Error messages
    if any(word in message_lower for word in ['error', 'failed', 'fatal', 'critical', 'unable']):
        return Colors.ERROR
    
    # Warning messages
    elif any(word in message_lower for word in ['warning', 'warn', 'caution', 'alert']):
        return Colors.WARNING
    
    # Success messages
    elif any(word in message_lower for word in ['success', 'completed', 'installed', 'finished', 'done', 'enabled']):
        return Colors.SUCCESS
    
    # Running/Processing messages
    elif any(word in message_lower for word in ['running', 'installing', 'downloading', 'processing', 'starting', 'configuring']):
        return Colors.INFO
    
    # Default color
    else:
        return Colors.HEADER


def stdOut(message, log=0, do_exit=0, code=os.EX_OK):
    """
    Standard output function with timestamps, coloring, and logging
    
    Args:
        message: Message to output
        log: If 1, write to log file
        do_exit: If 1, exit after outputting
        code: Exit code to use if do_exit is 1
    """
    # Get appropriate color for the message
    color = get_message_color(message)
    
    # Check if terminal supports color
    try:
        # Check if output is to a terminal
        if not sys.stdout.isatty():
            color = ''
            color_end = ''
        else:
            color_end = Colors.ENDC
    except:
        color = ''
        color_end = ''
    
    # Format timestamps
    timestamp = time.strftime("%m.%d.%Y_%H-%M-%S")
    
    print("\n\n")
    print(f"{color}[{timestamp}] #########################################################################{color_end}\n")
    print(f"{color}[{timestamp}] {message}{color_end}\n")
    print(f"{color}[{timestamp}] #########################################################################{color_end}\n")

    if log and hasattr(logging, 'InstallLog'):
        logging.InstallLog.writeToFile(message)
    if do_exit:
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(message)
        sys.exit(code)


def format_restart_litespeed_command(server_root_path):
    """
    Format the LiteSpeed restart command
    
    Args:
        server_root_path: Root path of the server installation
    
    Returns: Formatted command string
    """
    return '%sbin/lswsctrl restart' % (server_root_path)


PURE_FTPD_GROUPADD_CMD = (
    'getent group ftpgroup >/dev/null || groupadd -g 2001 ftpgroup'
)
PURE_FTPD_USERADD_CMD = (
    'getent passwd ftpuser >/dev/null || useradd -u 2001 -s /bin/false -d /bin/null '
    '-c "pureftpd user" -g ftpgroup ftpuser'
)


def ensure_pureftpd_system_user(distro, log=1):
    """
    Create Pure-FTPd system group/user if missing (safe on re-install).
    groupadd exit 9 (group exists) must not abort the installer.
    """
    ok = True
    ok = call(
        PURE_FTPD_GROUPADD_CMD, distro, '', 'ensure ftpgroup (gid 2001)',
        log, 0, os.EX_OSERR, True,
    ) and ok
    ok = call(
        PURE_FTPD_USERADD_CMD, distro, '', 'ensure ftpuser (uid 2001)',
        log, 0, os.EX_OSERR, True,
    ) and ok
    return ok


def get_installed_ols_version():
    """Return installed OpenLiteSpeed version as (major, minor, patch) or None."""
    import re
    for binary in ('/usr/local/lsws/bin/lshttpd', '/usr/local/lsws/bin/openlitespeed'):
        if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
            continue
        try:
            result = subprocess.run(
                [binary, '-v'],
                capture_output=True,
                timeout=5,
                universal_newlines=True,
                env=dict(os.environ, PATH=os.environ.get('PATH', '/usr/bin:/bin')),
            )
            out = (result.stdout or '') + (result.stderr or '')
            m = re.search(r'(\d+)\.(\d+)\.(\d+)', out)
            if m:
                return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def openlitespeed_rpm_layout_ok():
    """True when RPM layout includes control binary and main config."""
    return (
        os.path.isfile('/usr/local/lsws/bin/lswsctrl')
        and os.access('/usr/local/lsws/bin/lswsctrl', os.X_OK)
        and os.path.isfile('/usr/local/lsws/conf/httpd_config.conf')
    )


def ensure_openlitespeed_rpm_layout(distro, log=1):
    """
    Reinstall openlitespeed RPM when the package is registered but bin/conf are missing
    (common after partial cleanup or custom-binary-only overlay on re-install).
    """
    if openlitespeed_rpm_layout_ok():
        return True
    try:
        chk = subprocess.run(
            ['rpm', '-q', 'openlitespeed'],
            capture_output=True,
            timeout=30,
        )
        if chk.returncode != 0:
            return False
    except (OSError, subprocess.SubprocessError):
        return False

    writeToFile('OpenLiteSpeed RPM incomplete; reinstalling openlitespeed package...')
    call(
        'dnf reinstall -y openlitespeed 2>/dev/null || yum reinstall -y openlitespeed 2>/dev/null || true',
        distro,
        'reinstall openlitespeed',
        'reinstall openlitespeed',
        log,
        0,
        os.EX_OSERR,
        True,
    )
    ok = openlitespeed_rpm_layout_ok()
    if ok:
        writeToFile('OpenLiteSpeed RPM layout restored (lswsctrl and httpd_config.conf present)')
    else:
        writeToFile('WARNING: openlitespeed reinstall did not restore full layout')
    return ok


def should_skip_custom_ols_overlay():
    """
    Use official LiteSpeed repo OLS when version is new enough or EL10 layout is intact.
    Avoids replacing only openlitespeed binary and leaving lswsctrl missing.
    """
    try:
        import ols_version_policy
        min_ols = ols_version_policy.MIN_OFFICIAL_OLS
    except ImportError:
        min_ols = (1, 9, 0)

    ols_ver = get_installed_ols_version()
    if ols_ver and ols_ver >= min_ols:
        return True
    if is_rhel_el10() and openlitespeed_rpm_layout_ok():
        return True
    return False


def restart_litespeed(server_root_path='/usr/local/lsws/'):
    """
    Restart OpenLiteSpeed via lswsctrl or systemd when binaries are missing (re-install).
    Returns True if a restart was attempted successfully.
    """
    if not server_root_path.endswith('/'):
        server_root_path = server_root_path + '/'

    for ctrl in (
        server_root_path + 'bin/lswsctrl',
        '/usr/local/lsws/bin/lswsctrl',
        '/opt/lsws/bin/lswsctrl',
    ):
        if os.path.isfile(ctrl) and os.access(ctrl, os.X_OK):
            try:
                res = subprocess.call([ctrl, 'restart'])
                if res == 0:
                    return True
            except OSError:
                pass

    for unit in ('lsws', 'openlitespeed', 'lshttpd'):
        try:
            res = subprocess.call(['systemctl', 'restart', unit])
            if res == 0:
                writeToFile('LiteSpeed restarted via systemctl %s' % unit)
                return True
        except OSError:
            pass

    writeToFile('WARNING: could not restart LiteSpeed (lswsctrl and systemctl units unavailable)')
    return False


# Distribution constants
ubuntu = 0
centos = 1
cent8 = 2
openeuler = 3
debian12 = 4


def get_lsphp_install_suffixes():
    """
    LiteSpeed lsphp* two-digit version suffixes to install for this OS (pre-repo check).
    Mirrors the base list in plogical/upgrade.py get_available_php_versions() before
    check_package_availability filtering.

    Returns:
        list[str]: e.g. ['74','80',...,'85'] on AlmaLinux 9+/10+ and modern EL9/Ubuntu24+/Debian13+,
        or ['71',...,'85'] on older platforms where 7.1–7.3 packages exist.
    """
    long_list = ['71', '72', '73', '74', '80', '81', '82', '83', '84', '85']
    short_list = ['74', '80', '81', '82', '83', '84', '85']
    # EL10 LiteSpeed repo: no lsphp71–80; 8.1+ only (imap needs libc-client from gf-plus or build deps)
    el10_list = ['81', '82', '83', '84', '85']

    # AlmaLinux: explicit release file (matches upgrade.get_available_php_versions)
    if exists('/etc/almalinux-release'):
        try:
            with open('/etc/almalinux-release', 'r') as f:
                content = f.read().lower()
            if 'release 10' in content:
                return list(el10_list)
            if 'release 9' in content:
                return list(short_list)
        except (OSError, IOError, UnicodeError):
            pass
        return list(long_list)

    # Other RHEL family (Rocky/RHEL/CentOS Stream) without almalinux-release: EL9+ uses short list
    if exists('/etc/redhat-release'):
        try:
            with open('/etc/redhat-release', 'r') as f:
                data = f.read().lower()
            if 'release 10' in data or 'stream 10' in data:
                return list(el10_list)
            if 'release 9' in data or 'stream 9' in data:
                return list(short_list)
        except (OSError, IOError, UnicodeError):
            pass

    # Ubuntu 24.04+ (upgrade: Ubuntu24 branch)
    if exists('/etc/lsb-release'):
        try:
            with open('/etc/lsb-release', 'r') as f:
                lsb = f.read()
            if 'DISTRIB_ID=Ubuntu' in lsb:
                for line in lsb.splitlines():
                    if line.startswith('DISTRIB_RELEASE='):
                        rel = line.split('=', 1)[1].strip().strip('"').strip("'")
                        try:
                            parts = rel.split('.')
                            major = int(parts[0])
                            minor = int(parts[1]) if len(parts) > 1 else 0
                            if major > 24 or (major == 24 and minor >= 4):
                                return list(short_list)
                        except (ValueError, IndexError):
                            pass
                        break
        except (OSError, IOError, UnicodeError):
            pass

    # Debian 13+ (trixie+): upgrade uses Debian13 for short list
    if exists('/etc/os-release'):
        try:
            with open('/etc/os-release', 'r') as f:
                osr = f.read()
            osr_l = osr.lower().replace(' ', '')
            if 'id=debian' in osr_l:
                for line in osr.splitlines():
                    if line.upper().startswith('VERSION_ID='):
                        vid = line.split('=', 1)[1].strip().strip('"').strip("'")
                        try:
                            if int(vid.split('.')[0]) >= 13:
                                return list(short_list)
                        except (ValueError, IndexError):
                            pass
                        break
        except (OSError, IOError, UnicodeError):
            pass

    return list(long_list)


def resolve_mysql_cli():
    """Return first usable mysql/mariadb client binary path, or None."""
    for path in (
        '/usr/bin/mariadb',
        '/usr/bin/mysql',
        '/usr/sbin/mariadb',
        '/usr/sbin/mysql',
        '/usr/local/bin/mariadb',
        '/usr/local/bin/mysql',
    ):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def ensure_mariadb_client_cli(distro, log=1):
    """
    Ensure MariaDB/MySQL CLI exists (EL10 often ships only mariadb after server install).
    Installs MariaDB-client if missing and adds /usr/bin/mysql -> mariadb when needed.
    """
    cli = resolve_mysql_cli()
    if cli:
        if cli.endswith('mariadb') and not os.path.isfile('/usr/bin/mysql'):
            try:
                if not os.path.lexists('/usr/bin/mysql'):
                    os.symlink(cli, '/usr/bin/mysql')
            except OSError:
                pass
        return cli

    for pkg_cmd in (
        'dnf install -y --nobest MariaDB-client 2>/dev/null || true',
        'dnf install -y mariadb 2>/dev/null || true',
        'yum install -y MariaDB-client 2>/dev/null || true',
    ):
        call(pkg_cmd, distro, pkg_cmd, pkg_cmd, log, 0, os.EX_OSERR, True)

    cli = resolve_mysql_cli()
    if cli and cli.endswith('mariadb') and not os.path.isfile('/usr/bin/mysql'):
        try:
            if not os.path.lexists('/usr/bin/mysql'):
                os.symlink(cli, '/usr/bin/mysql')
        except OSError:
            pass
    return cli


def mariadb_repo_setup_shell_cmd(mariadb_version='11.8'):
    """Shell pipeline for MariaDB.org repo setup (root, follow redirects, skip broken prereq check)."""
    ver = str(mariadb_version or '11.8').strip().strip("'\"")
    try:
        parts = ver.split('.')[:2]
        if len(parts) < 2 or not all(p.isdigit() for p in parts):
            ver = '11.8'
    except (ValueError, TypeError):
        ver = '11.8'
    return (
        'curl -fsSL https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | '
        'bash -s -- --skip-check-installed --mariadb-server-version=%s' % ver
    )


def _mariadb_server_rpm_installed():
    """True if MariaDB.org or distro mariadb-server RPM is installed."""
    try:
        for pkg in ('MariaDB-server', 'mariadb-server'):
            result = subprocess.run(
                ['rpm', '-q', pkg],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0:
                return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def install_mariadb_server_rhel(distro, mariadb_version='11.8', log=1):
    """
    Install MariaDB on RHEL family: MariaDB.org packages first, then AppStream fallback (EL10).
    On RHEL/Alma 10+, AppStream is tried first (MariaDB.org conflicts with bootstrap connector-c).
    Returns True when server RPM is present and a client binary resolves.
    """
    if _mariadb_server_rpm_installed() and resolve_mysql_cli():
        return True

    mariadb_ver = str(mariadb_version or '11.8').strip().strip("'\"")

    def _install_appstream():
        stdOut(
            'Installing MariaDB from distro AppStream (mariadb-server)...',
            log,
        )
        appstream_cmd = (
            'dnf install -y mariadb-server mariadb mariadb-backup mariadb-devel '
            '|| dnf install -y --nobest mariadb-server mariadb mariadb-backup mariadb-devel'
        )
        call(
            appstream_cmd,
            distro,
            'AppStream MariaDB packages',
            'AppStream MariaDB packages',
            log,
            0,
            os.EX_OSERR,
            True,
        )
        ensure_mariadb_client_cli(distro, log)
        return _mariadb_server_rpm_installed() and bool(resolve_mysql_cli())

    if is_rhel_el10():
        if mariadb_ver not in ('10.11', '10.11.15', '10'):
            stdOut(
                'AlmaLinux/RHEL 10: MariaDB.org %s is not used (package conflicts). '
                'Installing AppStream mariadb-server (10.11.x).' % mariadb_ver,
                log,
            )
        if _install_appstream():
            return True

    setup_msg = 'MariaDB repository setup (%s)' % mariadb_ver
    call(
        mariadb_repo_setup_shell_cmd(mariadb_ver),
        distro,
        setup_msg,
        setup_msg,
        log,
        0,
        os.EX_OSERR,
        True,
    )

    mariadb_packages = 'MariaDB-server MariaDB-client MariaDB-backup MariaDB-devel'
    use_nobest = True
    try:
        maj_min = tuple(int(x) for x in mariadb_ver.split('.')[:2])
        use_nobest = (maj_min[0] == 10) or (maj_min[0] == 11 and maj_min[1] <= 8)
    except (ValueError, IndexError):
        pass
    nobest = ' --nobest' if use_nobest else ''
    official_cmd = 'dnf install -y%s %s' % (nobest, mariadb_packages)
    call(
        official_cmd,
        distro,
        'MariaDB.org packages',
        'MariaDB.org packages',
        log,
        0,
        os.EX_OSERR,
        True,
    )

    if _mariadb_server_rpm_installed():
        ensure_mariadb_client_cli(distro, log)
        return bool(resolve_mysql_cli())

    stdOut(
        'MariaDB.org packages unavailable; trying distro AppStream mariadb-server...',
        log,
    )
    return _install_appstream()


def ensure_lsphp_runtime_deps(distro, log=1):
    """Install oniguruma/libc-client where available so lsphp imap/mbstring can resolve on EL10."""
    if not exists('/etc/redhat-release') and not exists('/etc/almalinux-release'):
        return

    is_el10 = False
    for path in ('/etc/almalinux-release', '/etc/redhat-release'):
        if not exists(path):
            continue
        try:
            with open(path, 'r') as f:
                data = f.read().lower()
            if 'release 10' in data or 'stream 10' in data:
                is_el10 = True
                break
        except (OSError, IOError, UnicodeError):
            pass

    if not is_el10:
        return

    for cmd in (
        'dnf install -y --nobest oniguruma oniguruma-devel 2>/dev/null || true',
        'dnf install -y --nobest libc-client libc-client-devel 2>/dev/null || true',
        'dnf install -y --nobest cyrus-imap-devel 2>/dev/null || true',
    ):
        call(cmd, distro, cmd, cmd, log, 0, os.EX_OSERR, True)


def get_distro():
    """
    Detect Linux distribution

    Returns: Distribution constant (ubuntu, centos, cent8, openeuler, or debian12)
    """
    distro = -1
    distro_file = ""

    # Check for Debian first
    if exists("/etc/debian_version"):
        # Check if it's actually Ubuntu (which also has debian_version)
        if exists("/etc/lsb-release"):
            distro_file = "/etc/lsb-release"
            with open(distro_file) as f:
                for line in f:
                    if line == "DISTRIB_ID=Ubuntu\n":
                        distro = ubuntu
                        break
        else:
            # Pure Debian system - check version
            distro_file = "/etc/debian_version"
            with open(distro_file) as f:
                debian_version = f.read().strip()
                # Check specific Debian versions
                if debian_version.startswith('bookworm') or '12' in debian_version:
                    distro = debian12
                else:
                    # For other Debian versions, treat same as Ubuntu for compatibility
                    distro = ubuntu

    elif exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line == "DISTRIB_ID=Ubuntu\n":
                    distro = ubuntu

    elif exists("/etc/redhat-release"):
        distro_file = "/etc/redhat-release"
        distro = centos

        data = open('/etc/redhat-release', 'r').read()

        if data.find('CentOS Linux release 8') > -1:
            return cent8
        if data.find('CentOS Linux release 9') > -1 or data.find('CentOS Stream 9') > -1:
            return cent8
        if data.find('Rocky Linux release 9') > -1 or data.find('Rocky Linux 9') > -1:
            return cent8
        if data.find('Red Hat Enterprise Linux 8') > -1 or data.find('Red Hat Enterprise Linux 9') > -1:
            return cent8
        ## if almalinux 9 or 10 then pretty much same as cent8
        if data.find('AlmaLinux release 8') > -1 or data.find('AlmaLinux release 9') > -1 or data.find('AlmaLinux release 10') > -1:
            return cent8
        if data.find('Rocky Linux release 8') > -1 or data.find('Rocky Linux 8') > -1 or data.find('rocky:8') > -1:
            return cent8
        if data.find('CloudLinux 8') or data.find('cloudlinux 8') or data.find('CloudLinux 9') or data.find('cloudlinux 9'):
            return cent8

    else:
        if exists("/etc/openEuler-release"):
            distro_file = "/etc/openEuler-release"
            distro = openeuler

        else:
            if hasattr(logging, 'InstallLog'):
                logging.InstallLog.writeToFile("Can't find linux release file - fatal error")
            print("Can't find linux release file - fatal error")
            os._exit(os.EX_UNAVAILABLE)

    if distro == -1:
        error_msg = "Can't find distro name in " + distro_file + " - fatal error"
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(error_msg)
        print(error_msg)
        os._exit(os.EX_UNAVAILABLE)

    return distro


def map_debian_packages(package_string):
    """
    Map package names for Debian compatibility

    Args:
        package_string: Space-separated package names

    Returns:
        str: Mapped package names for Debian
    """
    if not is_debian():
        return package_string

    package_map = get_debian_mariadb_packages()
    packages = package_string.split()
    mapped_packages = []

    for package in packages:
        if package in package_map:
            replacement = package_map[package]
            if replacement:  # Skip empty replacements
                mapped_packages.extend(replacement.split())
        else:
            mapped_packages.append(package)

    return ' '.join(mapped_packages)


def get_package_install_command(distro, package_name, options=""):
    """
    Get the package installation command for a specific distribution

    Args:
        distro: Distribution constant
        package_name: Name of the package to install
        options: Additional options for the package manager

    Returns:
        tuple: (command, shell) where shell indicates if shell=True is needed
    """
    if distro == ubuntu or distro == debian12:
        # Map packages for Debian compatibility
        package_name = map_debian_packages(package_name)
        command = f"DEBIAN_FRONTEND=noninteractive apt-get -y install {package_name} {options}"
        shell = True
    elif distro == centos:
        command = f"yum install -y {package_name} {options}"
        shell = False
    else:  # cent8, openeuler
        command = f"dnf install -y {package_name} {options}"
        shell = False

    return command, shell


def get_package_remove_command(distro, package_name):
    """
    Get the package removal command for a specific distribution
    
    Args:
        distro: Distribution constant
        package_name: Name of the package to remove
    
    Returns:
        tuple: (command, shell) where shell indicates if shell=True is needed
    """
    if distro == ubuntu or distro == debian12:
        command = f"DEBIAN_FRONTEND=noninteractive apt-get -y remove {package_name}"
        shell = True
    elif distro == centos:
        command = f"yum remove -y {package_name}"
        shell = False
    else:  # cent8, openeuler
        command = f"dnf remove -y {package_name}"
        shell = False
    
    return command, shell


def rhel_major_version():
    """Major version from /etc/os-release VERSION_ID (e.g. 10 for AlmaLinux 10), or 0."""
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('VERSION_ID='):
                    vid = line.split('=', 1)[1].strip().strip('"').strip("'")
                    return int(vid.split('.')[0])
    except (OSError, ValueError, IndexError):
        pass
    return 0


def is_rhel_el10():
    """True on AlmaLinux/RHEL/Rocky/CentOS Stream 10+ (dnf-only, AppStream MariaDB)."""
    return rhel_major_version() >= 10


LITESPEED_REPO_RPM_URL = (
    'http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm'
)


def install_litespeed_repo_rhel(distro, log=1):
    """
    Install LiteSpeed RPM repo if missing. Idempotent (rpm exit 2 = already installed).
    Returns True on success.
    """
    cmd = (
        'rpm -q litespeed-repo >/dev/null 2>&1 || '
        'rpm -Uvh ' + LITESPEED_REPO_RPM_URL
    )
    return call(
        cmd,
        distro,
        'LiteSpeed repository',
        'LiteSpeed repository',
        log,
        0,
        os.EX_OSERR,
        True,
    )


def resFailed(distro, res, command=None):
    """
    Check if a command execution result indicates failure
    
    Args:
        distro: Distribution constant
        res: Return code from subprocess
        command: Optional command string (rpm exit 2 = already installed)
    
    Returns:
        bool: True if failed, False if successful
    """
    if res == 0:
        return False
    cmd = command or ''
    if res == 2 and 'rpm' in cmd and ('-Uvh' in cmd or '-ivh' in cmd or '-U ' in cmd):
        return False
    if distro in (ubuntu, debian12, centos, cent8, openeuler):
        return True
    return False


def wait_for_apt_lock():
    """
    Wait for apt lock to be released and clean up stuck processes if needed
    """
    import time
    import glob

    lock_files = [
        '/var/lib/dpkg/lock-frontend',
        '/var/lib/dpkg/lock',
        '/var/cache/apt/archives/lock'
    ]

    max_wait = 300  # Wait up to 5 minutes
    wait_time = 0

    while wait_time < max_wait:
        locks_exist = any(os.path.exists(lock) for lock in lock_files)

        if not locks_exist:
            return True

        # Check if any apt processes are actually running
        try:
            result = subprocess.run(['pgrep', '-f', 'apt'], capture_output=True)
            if result.returncode != 0:
                # No apt processes running but locks exist - remove them
                stdOut("No apt processes running, removing stale locks...")
                for lock_file in lock_files:
                    if os.path.exists(lock_file):
                        try:
                            os.remove(lock_file)
                            stdOut(f"Removed stale lock: {lock_file}")
                        except:
                            pass
                return True
        except:
            pass

        stdOut(f"Waiting for apt lock to be released... ({wait_time}s/{max_wait}s)")
        time.sleep(10)
        wait_time += 10

    # If we get here, we've waited too long - try to clean up
    stdOut("Timeout waiting for apt lock, attempting cleanup...")
    try:
        # Kill any stuck apt processes
        subprocess.run(['killall', '-9', 'apt-get'], capture_output=True)
        subprocess.run(['killall', '-9', 'apt'], capture_output=True)

        # Remove locks
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass

        # Reconfigure dpkg
        subprocess.run(['dpkg', '--configure', '-a'], capture_output=True)
        return True
    except:
        return False


def call(command, distro, bracket, message, log=0, do_exit=0, code=os.EX_OK, shell=False):
    """
    Execute a shell command with retry logic and error handling
    
    Args:
        command: Command to execute
        distro: Distribution constant
        bracket: Not used (kept for compatibility)
        message: Description of the command for logging
        log: If 1, write to log file
        do_exit: If 1, exit on failure
        code: Exit code to use if do_exit is 1
        shell: If True, execute through shell
    
    Returns:
        bool: True if successful, False if failed
    """
    # CRITICAL (first): Replace missing CyberPanel Python so old/cached installers never hit FileNotFoundError
    if isinstance(command, str):
        bad_path = '/usr/local/CyberPanel/bin/python'
        if bad_path in command and not os.path.isfile(bad_path):
            fallback = '/usr/bin/python3'
            if not os.path.isfile(fallback):
                fallback = '/usr/local/bin/python3'
            if os.path.isfile(fallback):
                command = command.replace(bad_path, fallback)
                shell = True
        # Use /tmp/composer.sh when command references relative composer.sh (avoids "chmod: cannot access 'composer.sh'")
        # Only replace local file refs, not URLs (e.g. https://cyberpanel.sh/composer.sh)
        if not os.path.isfile(os.path.join(os.getcwd(), 'composer.sh')):
            if './composer.sh' in command:
                command = command.replace('./composer.sh', '/tmp/composer.sh')
                shell = True
            elif ' composer.sh' in command and 'http' not in command.split('composer.sh')[0][-20:]:
                command = command.replace(' composer.sh', ' /tmp/composer.sh')
                shell = True

    # Check for apt lock before running apt commands
    if 'apt-get' in command or 'apt ' in command:
        if not wait_for_apt_lock():
            stdOut("Failed to acquire apt lock after waiting")
            if do_exit:
                os._exit(code)
            return False

    # CRITICAL: Use shell=True for commands with shell metacharacters
    # Avoids "No matching repo to modify: 2>/dev/null, true, ||" and "Could not resolve host: |" when shlex.split splits them
    if not shell and (any(x in command for x in (' || ', ' 2>/dev', ' 2>', ' | ', '; true', '|| true')) or '|' in command):
        shell = True

    # CRITICAL: For mysql/mariadb commands, always use shell=True and full binary path
    # This fixes "No such file or directory: 'mysql'" when run via shlex.split
    if not shell and ('mysql' in command or 'mariadb' in command):
        import re
        mysql_bin = None
        for _mp in ('/usr/bin/mariadb', '/usr/bin/mysql'):
            if os.path.isfile(_mp) and os.access(_mp, os.X_OK):
                mysql_bin = _mp
                break
        if not mysql_bin:
            call('dnf install -y --nobest MariaDB-client 2>/dev/null || true', distro, '', '', log, 0, os.EX_OSERR, True)
            for _mp in ('/usr/bin/mariadb', '/usr/bin/mysql'):
                if os.path.isfile(_mp) and os.access(_mp, os.X_OK):
                    mysql_bin = _mp
                    break
        if not mysql_bin:
            mysql_bin = '/usr/bin/mariadb' if os.path.exists('/usr/bin/mariadb') else '/usr/bin/mysql'
        # Replace only leading "mysql" or "mariadb" (executable), not "mysql" in SQL like "use mysql;"
        if re.match(r'^\s*(sudo\s+)?(mysql|mariadb)\s', command):
            command = re.sub(r'^(\s*)(?:sudo\s+)?(mysql|mariadb)(\s)', r'\g<1>' + mysql_bin + r'\g<3>', command, count=1)
        shell = True

    finalMessage = 'Running: %s' % (message)
    stdOut(finalMessage, log)
    count = 0
    while True:
        try:
            if shell:
                res = subprocess.call(command, shell=True)
            else:
                res = subprocess.call(shlex.split(command))
        except FileNotFoundError as e:
            # Old installer may pass /usr/local/CyberPanel/bin/python; retry with system python once
            if isinstance(command, str) and '/usr/local/CyberPanel/bin/python' in command:
                fallback = '/usr/bin/python3'
                if not os.path.isfile(fallback):
                    fallback = '/usr/local/bin/python3'
                if os.path.isfile(fallback):
                    command = command.replace('/usr/local/CyberPanel/bin/python', fallback)
                    shell = True
                    stdOut("Retrying with %s (CyberPanel python missing)" % fallback, log)
                    res = subprocess.call(command, shell=True)
                else:
                    raise
            else:
                raise

        if resFailed(distro, res, command):
            count = count + 1
            finalMessage = 'Running %s failed. Running again, try number %s' % (message, str(count))
            stdOut(finalMessage)
            if count == 3:
                fatal_message = ''
                if do_exit:
                    fatal_message = '.  Fatal error, see /var/log/installLogs.txt for full details'

                stdOut("[ERROR] We are not able to run " + message + ' return code: ' + str(res) +
                       fatal_message + ".", 1, do_exit, code)
                return False
        else:
            stdOut('Successfully ran: %s.' % (message), log)
            break

    return True


# Character sets for password generation (kept for backward compatibility)
char_set = {
    'small': 'abcdefghijklmnopqrstuvwxyz',
    'nums': '0123456789',
    'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
}


def generate_pass(length=14):
    """
    Generate a cryptographically secure random password
    
    Args:
        length: Length of the password to generate (default 14)
    
    Returns:
        str: Random password containing uppercase, lowercase letters and digits
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_random_string(length=32, include_special=False):
    """
    Generate a random string with optional special characters
    
    Args:
        length: Length of the string to generate
        include_special: If True, include special characters
    
    Returns:
        str: Random string
    """
    alphabet = string.ascii_letters + string.digits
    if include_special:
        alphabet += string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))



def strip_mariadb_maxscale_apt_repos():
    """
    MariaDB mariadb_repo_setup adds MaxScale apt repo; Ubuntu noble has no Release (GH usmannasir/cyberpanel#1740).
    """
    slist = '/etc/apt/sources.list.d'
    try:
        if not os.path.isdir(slist):
            return
        for pattern in (
            'mariadb-maxscale*.list', 'mariadb-maxscale*.sources',
            '*maxscale*.list', '*maxscale*.sources',
        ):
            for fp in glob.glob(os.path.join(slist, pattern)):
                try:
                    os.remove(fp)
                except OSError:
                    pass
        for fp in glob.glob(os.path.join(slist, 'mariadb*.list')):
            try:
                with open(fp, 'r', encoding='utf-8', errors='replace') as handle:
                    lines = handle.readlines()
                new_lines = [
                    ln for ln in lines
                    if 'maxscale' not in ln.lower()
                    and 'dlm.mariadb.com/repo/maxscale' not in ln
                ]
                if new_lines != lines:
                    with open(fp, 'w', encoding='utf-8') as handle:
                        handle.writelines(new_lines)
            except OSError:
                pass
        for fp in glob.glob(os.path.join(slist, 'mariadb*.sources')):
            try:
                with open(fp, 'r', encoding='utf-8', errors='replace') as handle:
                    content = handle.read()
                if 'maxscale' not in content.lower() and 'dlm.mariadb.com/repo/maxscale' not in content:
                    continue
                blocks = content.split('\n\n')
                kept = []
                for block in blocks:
                    bl = block.lower()
                    if 'maxscale' in bl or 'dlm.mariadb.com/repo/maxscale' in block:
                        continue
                    kept.append(block)
                new_content = '\n\n'.join(kept)
                if new_content.strip() != content.strip():
                    with open(fp, 'w', encoding='utf-8') as handle:
                        handle.write(new_content)
            except OSError:
                pass
    except Exception:
        pass


def writeToFile(message):
    """
    Write a message to the installation log file
    
    Args:
        message: Message to write to the log file
    """
    # Import logging module if available
    try:
        import installLog as logging
        if hasattr(logging, 'InstallLog') and hasattr(logging.InstallLog, 'writeToFile'):
            logging.InstallLog.writeToFile(message)
    except ImportError:
        # If installLog module is not available, just print the message
        print(f"[LOG] {message}")


CYBERCP_ROOT = '/usr/local/CyberCP'

CYBERCP_MIGRATION_APPS_FALLBACK = [
    'loginSystem', 'packages', 'websiteFunctions', 'baseTemplate', 'userManagment',
    'dns', 'databases', 'ftp', 'filemanager', 'mailServer', 'emailPremium',
    'emailDelivery', 'webmail',
    'cloudAPI', 'containerization', 'IncBackups', 'CLManager',
    's3Backups', 'dockerManager', 'aiScanner', 'firewall', 'tuning', 'serverStatus',
    'serverLogs', 'backup', 'managePHP', 'manageSSL', 'api', 'manageServices',
    'pluginHolder', 'highAvailability', 'WebTerminal',
]


def cyberpanel_github_owner():
    """GitHub org/user for CyberPanel source (installer exports CYBERPANEL_GITHUB_OWNER)."""
    owner = (os.environ.get('CYBERPANEL_GITHUB_OWNER') or 'master3395').strip()
    if not owner or '/' in owner or ' ' in owner:
        return 'master3395'
    return owner


def cyberpanel_github_owners_to_try():
    """Fork first, then upstream usmannasir if different."""
    primary = cyberpanel_github_owner()
    owners = [primary]
    if primary != 'usmannasir':
        owners.append('usmannasir')
    return owners


def cyberpanel_github_repo_base(owner=None):
    o = owner or cyberpanel_github_owner()
    return 'https://github.com/%s/cyberpanel' % o


def discover_cybercp_migration_apps(cybercp_root=None):
    """
    Django app labels under CyberCP that ship a migrations package.
    Used before makemigrations so stale files (e.g. emailDelivery -> loginSystem) are removed.
    """
    root = cybercp_root or CYBERCP_ROOT
    if not os.path.isdir(root):
        return list(CYBERCP_MIGRATION_APPS_FALLBACK)

    skip_dirs = {
        'CyberCP', 'lib', 'bin', 'public', 'static', 'locale',
        'install', 'test', 'tests', 'Test', 'docs', 'pkg', 'modules',
    }
    apps = []
    for name in os.listdir(root):
        if name in skip_dirs or name.startswith('.'):
            continue
        app_path = os.path.join(root, name)
        if not os.path.isdir(app_path):
            continue
        mig = os.path.join(app_path, 'migrations')
        if os.path.isdir(mig) and os.path.isfile(os.path.join(mig, '__init__.py')):
            apps.append(name)

    if not apps:
        return list(CYBERCP_MIGRATION_APPS_FALLBACK)
    return sorted(set(apps))


def build_cyberpanel_clone_commands(branch_name):
    """Ordered git clone commands: primary fork, then upstream fallback."""
    commands = []
    seen = set()

    def add(cmd):
        if cmd not in seen:
            seen.add(cmd)
            commands.append(cmd)

    for owner in cyberpanel_github_owners_to_try():
        base = cyberpanel_github_repo_base(owner)
        if branch_name and branch_name != 'stable':
            if branch_name.startswith('commit:'):
                commit_hash = branch_name[7:]
                add('git clone %s /usr/local/CyberCP' % base)
                add('cd /usr/local/CyberCP && git checkout %s' % commit_hash)
            elif branch_name.startswith('v'):
                add('git clone --depth 1 --branch %s %s /usr/local/CyberCP' % (branch_name, base))
            elif branch_name.endswith('-dev'):
                add('git clone --depth 1 --branch %s %s /usr/local/CyberCP' % (branch_name, base))
            elif len(branch_name) >= 7 and all(c in '0123456789abcdef' for c in branch_name.lower()):
                add('git clone %s /usr/local/CyberCP' % base)
                add('cd /usr/local/CyberCP && git checkout %s' % branch_name)
            else:
                add('git clone --depth 1 --branch v%s %s /usr/local/CyberCP' % (branch_name, base))
                add('git clone --depth 1 --branch %s %s /usr/local/CyberCP' % (branch_name, base))
        add('git clone %s /usr/local/CyberCP' % base)
        add('git clone --depth 1 %s /usr/local/CyberCP' % base)
        add('git clone --single-branch --branch stable %s /usr/local/CyberCP' % base)

    return commands


def build_cyberpanel_archive_download(branch_name, owner=None):
    """
    Return (download_url, extract_dir) for wget/unzip fallback when git clone fails.
  """
    base = cyberpanel_github_repo_base(owner)
    if branch_name and branch_name != 'stable':
        if branch_name.startswith('commit:'):
            commit_hash = branch_name[7:]
            return ('%s/archive/%s.zip' % (base, commit_hash), 'cyberpanel-%s' % commit_hash)
        if len(branch_name) >= 7 and all(c in '0123456789abcdef' for c in branch_name.lower()):
            return ('%s/archive/%s.zip' % (base, branch_name), 'cyberpanel-%s' % branch_name)
        if branch_name.startswith('v'):
            return (
                '%s/archive/refs/tags/%s.zip' % (base, branch_name),
                'cyberpanel-%s' % branch_name[1:],
            )
        if branch_name.endswith('-dev'):
            return (
                '%s/archive/refs/heads/%s.zip' % (base, branch_name),
                'cyberpanel-%s' % branch_name,
            )
        return (
            '%s/archive/refs/tags/v%s.zip' % (base, branch_name),
            'cyberpanel-%s' % branch_name,
        )
    return ('%s/archive/refs/heads/stable.zip' % base, 'cyberpanel-stable')


def pick_cybercp_venv_bootstrap_python():
  """
  Interpreter used to create or repair /usr/local/CyberCP venv.
  Prefer CYBERCP_VENV_PYTHON from the shell installer, then Python 3.10+ on disk.
  """
  env_p = (os.environ.get('CYBERCP_VENV_PYTHON') or '').strip()
  if env_p and os.path.isfile(env_p) and os.access(env_p, os.X_OK):
    return env_p
  for cand in (
      '/usr/bin/python3.12',
      '/usr/bin/python3.13',
      '/usr/bin/python3.11',
      '/usr/local/bin/python3.11',
      '/usr/bin/python3.10',
  ):
    if not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
      continue
    try:
      r = subprocess.run(
          [cand, '-c', 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)'],
          capture_output=True,
          text=True,
          timeout=10,
      )
      if r.returncode == 0:
        return cand
    except (OSError, subprocess.SubprocessError):
      continue
  return sys.executable or shutil.which('python3') or 'python3'


def cybercp_venv_has_django(python_path):
  """Return True if the given interpreter can import django."""
  if not python_path or not os.path.isfile(python_path):
    return False
  try:
    r = subprocess.run(
        [python_path, '-c', 'import django'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.returncode == 0
  except (OSError, subprocess.SubprocessError):
    return False


def _cybercp_pip_install_requirements(pip_path, cybercp_root=CYBERCP_ROOT, log=1):
  """Install CyberCP requirements into the venv. Returns True on success."""
  req_file = os.path.join(cybercp_root, 'requirments.txt')
  if not os.path.isfile(req_file):
    req_file = os.path.join(cybercp_root, 'requirements.txt')
  if os.path.isfile(req_file):
    cmd = [pip_path, 'install', '-r', req_file]
  else:
    cmd = [
        pip_path, 'install',
        'Django>=4.2', 'PyMySQL', 'mysqlclient', 'requests', 'cryptography',
        'psutil', 'gunicorn', 'python-dotenv',
    ]
  try:
    subprocess.run(
        [pip_path, 'install', '--upgrade', 'pip', 'setuptools', 'wheel'],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=cybercp_root,
    )
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,
        cwd=cybercp_root,
    )
    if r.returncode != 0:
      writeToFile('CyberCP pip install failed (exit %s): %s' % (
          r.returncode, (r.stderr or r.stdout or '')[:800]))
      return False
    return True
  except (OSError, subprocess.SubprocessError) as exc:
    writeToFile('CyberCP pip install error: %s' % exc)
    return False


def ensure_cybercp_venv(log=1):
  """
  After git clone into /usr/local/CyberCP, ensure bin/python exists and can import django.
  Uses virtualenv --system-site-packages (same as upgrade path) so the clone is not wiped.
  """
  cybercp_root = CYBERCP_ROOT
  venv_py = os.path.join(cybercp_root, 'bin', 'python')
  venv_pip = os.path.join(cybercp_root, 'bin', 'pip')

  if cybercp_venv_has_django(venv_py):
    writeToFile('CyberCP venv OK (django importable)')
    return True

  vpy = pick_cybercp_venv_bootstrap_python()
  writeToFile('CyberCP venv bootstrap interpreter: %s' % vpy)

  if os.path.isfile(venv_py) and os.path.isfile(venv_pip):
    writeToFile('CyberCP venv present without Django; installing requirements...')
    if _cybercp_pip_install_requirements(venv_pip, cybercp_root, log):
      return cybercp_venv_has_django(venv_py)
    writeToFile('pip install into existing venv did not provide django')

  writeToFile('Creating CyberCP virtualenv at %s' % cybercp_root)
  try:
    subprocess.run(
        [vpy, '-m', 'pip', 'install', '--upgrade', 'pip', 'virtualenv'],
        capture_output=True,
        text=True,
        timeout=180,
    )
    r = subprocess.run(
        [vpy, '-m', 'virtualenv', '--system-site-packages', cybercp_root],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
      writeToFile('virtualenv failed: %s' % (r.stderr or r.stdout or '')[:500])
      r = subprocess.run(
          [vpy, '-m', 'venv', '--system-site-packages', cybercp_root],
          capture_output=True,
          text=True,
          timeout=300,
      )
      if r.returncode != 0:
        writeToFile('python -m venv failed: %s' % (r.stderr or r.stdout or '')[:500])
        return False
  except (OSError, subprocess.SubprocessError) as exc:
    writeToFile('CyberCP venv creation error: %s' % exc)
    return False

  if not os.path.isfile(venv_pip):
    writeToFile('CyberCP venv missing bin/pip after creation')
    return False

  if not _cybercp_pip_install_requirements(venv_pip, cybercp_root, log):
    return False

  if cybercp_venv_has_django(venv_py):
    writeToFile('CyberCP venv created and django is importable')
    return True

  writeToFile('FATAL: django still not importable after venv setup')
  return False


def _is_debian_family_os():
  if not os.path.isfile('/etc/os-release'):
    return False
  try:
    with open('/etc/os-release', 'r') as f:
      content = f.read().lower()
    return 'id=ubuntu' in content or 'id=debian' in content or 'id_like=debian' in content
  except (OSError, IOError):
    return False


def ensure_mysqlclient_for_python(python_exe=None, log=1):
  """
  Ensure the given Python can ``import MySQLdb`` (mysqlclient package).
  Used before installCyberPanel is imported during install.py.
  Returns True if import works after optional pip install.
  """
  python_exe = python_exe or sys.executable
  if not python_exe or not os.path.isfile(python_exe):
    writeToFile('ensure_mysqlclient: invalid python path')
    return False

  def _can_import():
    try:
      r = subprocess.run(
          [python_exe, '-c', 'import MySQLdb'],
          capture_output=True,
          text=True,
          timeout=90,
      )
      return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
      return False

  if _can_import():
    return True

  writeToFile('Installing mysqlclient for %s' % python_exe)

  if _is_debian_family_os():
    subprocess.run(
        'DEBIAN_FRONTEND=noninteractive apt-get install -y -qq '
        'libmariadb-dev-compat libmariadb-dev python3-dev pkg-config gcc build-essential',
        shell=True,
        capture_output=True,
        timeout=600,
    )
  else:
    for pkg_cmd in (
        'dnf install -y mariadb-devel python3-devel gcc pkgconfig',
        'yum install -y mariadb-devel python3-devel gcc pkgconfig',
    ):
      subprocess.run(pkg_cmd, shell=True, capture_output=True, timeout=600)

  pip_extra = ['--break-system-packages'] if _is_debian_family_os() else []
  for pip_cmd in (
      [python_exe, '-m', 'pip', 'install', '--upgrade', 'pip', 'wheel', 'setuptools'] + pip_extra,
      [python_exe, '-m', 'pip', 'install', 'mysqlclient'] + pip_extra,
  ):
    try:
      subprocess.run(pip_cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
      writeToFile('mysqlclient pip install error: %s' % exc)

  ok = _can_import()
  if not ok:
    writeToFile('WARNING: mysqlclient still not importable for %s' % python_exe)
  return ok
