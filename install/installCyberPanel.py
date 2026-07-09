import shutil
import subprocess
import os
from mysqlUtilities import mysqlUtilities
import installLog as logging
import errno
import MySQLdb as mariadb
import install
from os.path import exists
import time
import install_utils
import urllib.request
import re

# distros - using from install_utils
centos = install_utils.centos
ubuntu = install_utils.ubuntu
cent8 = install_utils.cent8
openeuler = install_utils.openeuler


def get_Ubuntu_release():
    return install_utils.get_Ubuntu_release(use_print=True, exit_on_error=True)


def get_Ubuntu_code_name():
    """Get Ubuntu codename based on version"""
    release = get_Ubuntu_release()
    if release >= 24.04:
        return "noble"
    elif release >= 22.04:
        return "jammy"
    elif release >= 20.04:
        return "focal"
    elif release >= 18.04:
        return "bionic"
    else:
        return "xenial"


# Using shared function from install_utils
FetchCloudLinuxAlmaVersionVersion = install_utils.FetchCloudLinuxAlmaVersionVersion

class InstallCyberPanel:
    mysql_Root_password = ""
    mysqlPassword = ""
    CloudLinux8 = 0

    def install_package(self, package_name, options=""):
        """Unified package installation across distributions"""
        command, shell = install_utils.get_package_install_command(self.distro, package_name, options)
        
        # InstallCyberPanel always uses verbose mode (no silent option)
        if self.distro == ubuntu:
            return install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, shell)
        else:
            # For non-Ubuntu, original code didn't pass shell parameter
            return install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def manage_service(self, service_name, action="start"):
        """Unified service management"""
        service_map = {
            'mariadb': 'mariadb',
            'pureftpd': 'pure-ftpd-mysql' if self.distro == ubuntu else 'pure-ftpd',
            'pdns': 'pdns'
        }
        
        actual_service = service_map.get(service_name, service_name)
        
        # For AlmaLinux 9, try both mariadb and mysqld services
        if service_name == 'mariadb' and (self.distro == cent8 or self.distro == openeuler):
            # Try mariadb first, then mysqld if mariadb fails
            command = f'systemctl {action} {actual_service}'
            result = install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            if result != 0:
                # If mariadb service fails, try mysqld
                command = f'systemctl {action} mysqld'
                return install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            return result
        else:
            command = f'systemctl {action} {actual_service}'
            return install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def modify_file_content(self, file_path, replacements):
        """Generic file content modification"""
        try:
            with open(file_path, 'r') as f:
                data = f.readlines()
            
            with open(file_path, 'w') as f:
                for line in data:
                    modified_line = line
                    for old, new in replacements.items():
                        if old in line:
                            modified_line = line.replace(old, new)
                            break
                    f.write(modified_line)
            return True
        except IOError as e:
            logging.InstallLog.writeToFile(f'[ERROR] {str(e)} [modify_file_content]')
            return False

    def copy_config_file(self, source_dir, dest_path, mysql_mode='One'):
        """Handle configuration file copying with mode selection"""
        # For directories like 'dns' vs 'dns-one', 'pure-ftpd' vs 'pure-ftpd-one'
        # Default mode is 'One' which uses the -one directories
        if mysql_mode == 'Two':
            source_path = source_dir
        else:
            # Default mode 'One' uses directories with -one suffix
            source_path = f"{source_dir}-one"
        
        # Ensure we're working with absolute paths
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.cwd, source_path)
        
        # Determine the actual file to copy
        if os.path.isdir(source_path):
            # If dest_path is a file (like pdns.conf), copy the specific file
            if dest_path.endswith('.conf'):
                # Look for the specific config file
                source_file = os.path.join(source_path, os.path.basename(dest_path))
                if os.path.exists(source_file):
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.copy(source_file, dest_path)
                else:
                    raise IOError(f"Source file {source_file} not found")
            else:
                # If it's a directory, copy the whole directory
                if os.path.exists(dest_path):
                    if os.path.isdir(dest_path):
                        shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
        else:
            raise IOError(f"Source path {source_path} not found")

    @staticmethod
    def ISARM():

        try:
            command = 'uname -a'
            try:
                result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
            except:
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

            if 'aarch64' in result.stdout:
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    def OSFlags():
        if os.path.exists("/etc/redhat-release"):
            data = open('/etc/redhat-release', 'r').read()

            if data.find('CloudLinux 8') > -1 or data.find('cloudlinux 8') > -1:
                InstallCyberPanel.CloudLinux8 = 1

    def __init__(self, rootPath, cwd, distro, ent, serial=None, port=None, ftp=None, dns=None, publicip=None,
                 remotemysql=None, mysqlhost=None, mysqldb=None, mysqluser=None, mysqlpassword=None, mysqlport=None):
        self.server_root_path = rootPath
        self.cwd = cwd
        self.distro = distro
        self.ent = ent
        self.serial = serial
        self.port = port
        self.ftp = None
        self.dns = dns
        self.publicip = publicip
        self.remotemysql = remotemysql
        self.mysqlhost = mysqlhost
        self.mysqluser = mysqluser
        self.mysqlpassword = mysqlpassword
        self.mysqlport = mysqlport
        self.mysqldb = mysqldb

        ## TURN ON OS FLAGS FOR SPECIFIC NEEDS LATER

        InstallCyberPanel.OSFlags()

    @staticmethod
    def stdOut(message, log=0, exit=0, code=os.EX_OK):
        install_utils.stdOut(message, log, exit, code)

    @staticmethod
    def getLatestLSWSVersion():
        """Fetch the latest LSWS Enterprise version from LiteSpeed's website"""
        try:
            # Try to fetch from the download page
            url = "https://www.litespeedtech.com/products/litespeed-web-server/download"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')

            # Look for the latest version pattern: lsws-X.Y.Z-ent
            version_pattern = r'lsws-(\d+\.\d+\.\d+)-ent'
            versions = re.findall(version_pattern, html)

            if versions:
                # Get the latest version
                latest_version = sorted(versions, key=lambda v: [int(x) for x in v.split('.')])[-1]
                InstallCyberPanel.stdOut(f"Found latest LSWS Enterprise version: {latest_version}", 1)
                return latest_version
            else:
                InstallCyberPanel.stdOut("Could not find version pattern in HTML, using fallback", 1)

        except Exception as e:
            InstallCyberPanel.stdOut(f"Failed to fetch latest LSWS version: {str(e)}, using fallback", 1)

        # Fallback to known latest version
        return "6.3.4"

    def detectArchitecture(self):
        """Detect system architecture - custom binaries only for x86_64"""
        try:
            import platform
            arch = platform.machine()
            return arch == "x86_64"
        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [detectArchitecture]")
            return False

    def detectPlatform(self):
        """Detect OS platform for binary selection (rhel8, rhel9, ubuntu)"""
        try:
            # Check for Ubuntu
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    content = f.read()
                    if 'Ubuntu' in content or 'ubuntu' in content:
                        # The 'ubuntu' artifact is built on 22.04 (needs GLIBC_2.34) and
                        # does NOT run on Ubuntu 20.04 (glibc 2.31, ticket #OXHTOK7AH).
                        # Skip the overlay there and keep stock OLS.
                        if 'DISTRIB_RELEASE=20.04' in content:
                            InstallCyberPanel.stdOut("Ubuntu 20.04 detected: custom OLS binary requires GLIBC_2.34 (22.04+); keeping stock OLS", 1)
                            return 'skip'
                        return 'ubuntu'

            # Check for RHEL-based distributions
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()

                    # Check for version 8.x (RHEL, AlmaLinux, Rocky, CloudLinux, CentOS 8)
                    if 'version="8.' in content or 'version_id="8.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel8'

                    # Check for version 9.x
                    if 'version="9.' in content or 'version_id="9.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

                    # Check for version 10.x (AlmaLinux 10, etc.) — the el9 binary runs on el10
                    # (GLIBC_2.35 <= 2.39, libcrypt.so.2), so map it to the rhel9 artifact.
                    if 'version="10.' in content or 'version_id="10.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

            # Default to rhel9 if can't detect (safer default for newer systems)
            InstallCyberPanel.stdOut("WARNING: Could not detect platform, defaulting to rhel9", 1)
            return 'rhel9'

        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [detectPlatform]")
            InstallCyberPanel.stdOut(f"ERROR detecting platform: {msg}, defaulting to rhel9", 1)
            return 'rhel9'

    def downloadCustomBinary(self, url, destination):
        """Download custom binary file"""
        try:
            InstallCyberPanel.stdOut(f"Downloading {os.path.basename(destination)}...", 1)

            # Use wget for better progress display
            command = f'wget -q --show-progress {url} -O {destination}'
            install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Check if file was downloaded successfully by verifying it exists and has reasonable size
            if os.path.exists(destination):
                file_size = os.path.getsize(destination)
                # Verify file size is reasonable (at least 10KB to avoid error pages/empty files)
                if file_size > 10240:  # 10KB
                    if file_size > 1048576:  # 1MB
                        InstallCyberPanel.stdOut(f"Downloaded successfully ({file_size / (1024*1024):.2f} MB)", 1)
                    else:
                        InstallCyberPanel.stdOut(f"Downloaded successfully ({file_size / 1024:.2f} KB)", 1)

                    return True
                else:
                    InstallCyberPanel.stdOut(f"ERROR: Downloaded file too small ({file_size} bytes)", 1)
                    return False
            else:
                InstallCyberPanel.stdOut("ERROR: Download failed - file not found", 1)
                return False

        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [downloadCustomBinary]")
            InstallCyberPanel.stdOut(f"ERROR: {msg}", 1)
            return False

    def verifyChecksum(self, file_path, expected_sha256):
        """Verify a downloaded file against an expected SHA256.

        Returns True when the hash matches OR when no expected hash is
        configured (verification is then skipped and the size-check still
        applies). Returns False only on a real mismatch, so callers can
        abort and keep the existing/stock binary.
        """
        if not expected_sha256:
            return True  # no published hash to check against; skip
        try:
            import hashlib
            h = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            actual = h.hexdigest()
            if actual.lower() == expected_sha256.lower():
                InstallCyberPanel.stdOut(f"SHA256 verified: {os.path.basename(file_path)}", 1)
                return True
            InstallCyberPanel.stdOut(f"ERROR: SHA256 mismatch for {os.path.basename(file_path)}", 1)
            InstallCyberPanel.stdOut(f"  expected: {expected_sha256}", 1)
            InstallCyberPanel.stdOut(f"  actual:   {actual}", 1)
            return False
        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [verifyChecksum]")
            InstallCyberPanel.stdOut(f"ERROR: {msg} [verifyChecksum]", 1)
            return False

    def checkGlibcCompat(self, binary_path):
        """Pre-flight ABI check: ldd the downloaded binary and fail if any
        shared library is unresolved ('not found'). Prevents installing a
        binary that can't load on this OS (the GLIBC/libcrypt outage class).
        A fully static binary reports 'not a dynamic executable' (no
        'not found') and passes. ldd being unavailable is non-blocking.
        """
        try:
            result = subprocess.run(['ldd', binary_path], capture_output=True, text=True, timeout=15)
            output = (result.stdout or '') + (result.stderr or '')
            if 'not found' in output:
                InstallCyberPanel.stdOut("ERROR: Downloaded binary has unresolved libraries (incompatible with this OS):", 1)
                for line in output.splitlines():
                    if 'not found' in line:
                        InstallCyberPanel.stdOut(f"  {line.strip()}", 1)
                return False
            return True
        except Exception as msg:
            InstallCyberPanel.stdOut(f"WARNING: Could not run ldd pre-check ({msg}); continuing", 1)
            return True

    def installCustomOLSBinaries(self):
        """Install custom OpenLiteSpeed binaries with PHP config support"""
        try:
            InstallCyberPanel.stdOut("Installing Custom OpenLiteSpeed Binaries", 1)
            InstallCyberPanel.stdOut("=" * 50, 1)

            # Check architecture
            if not self.detectArchitecture():
                InstallCyberPanel.stdOut("WARNING: Custom binaries only available for x86_64", 1)
                InstallCyberPanel.stdOut("Skipping custom binary installation", 1)
                InstallCyberPanel.stdOut("Standard OLS will be used", 1)
                return True  # Not a failure, just skip

            # Detect platform
            platform = self.detectPlatform()
            InstallCyberPanel.stdOut(f"Detected platform: {platform}", 1)

            # Some platforms intentionally skip the custom overlay (e.g. Ubuntu 20.04,
            # where the binary's GLIBC requirement isn't met) and keep stock OLS.
            if platform == 'skip':
                InstallCyberPanel.stdOut("Custom binary installation skipped for this platform; using standard OLS", 1)
                return True  # Not a failure, just skip

            # Platform-specific URLs and checksums (OpenLiteSpeed v2.5.0 — all features config-driven, static linking)
            # Includes: PHPConfig API, Origin Header Forwarding, ReadApacheConf (with Portmap), Auto-SSL (ACME v2), ModSecurity ABI Compatibility
            # Module v2.7.3: preserves Content-Encoding on LSCache hits
            # rhel9 artifact covers EL9 + EL10 (AlmaLinux 10); ubuntu artifact covers 22.04/24.04 (not 20.04 — see detectPlatform)
            BINARY_CONFIGS = {
                'rhel8': {
                    'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-rhel8',
                    'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-rhel8.so',
                    'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel8.so',
                    'sha256': {
                        'binary': '48c8423edfaec3fe1b6eee118925ed3ac55314c53e9bdf2e5bdd4960c4806a62',
                        'module': '83111c8a3310b40e998070b07002a205975a06e09c6e0f8e8054e8d18b8682e1',
                        'modsec': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2',
                    },
                },
                'rhel9': {
                    'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-rhel9',
                    'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-rhel9.so',
                    'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-rhel9.so',
                    'sha256': {
                        'binary': '780163ee7c0304c9b1db6abaeeaca2e58dbfc05436de776e921ca1d493462596',
                        'module': 'a189da7ec5c09c5ba836209aa10746b691bbef21010cbe4c4c622614cf03c5e1',
                        'modsec': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629',
                    },
                },
                'ubuntu': {
                    'url': 'https://cyberpanel.net/openlitespeed-2.5.0-x86_64-ubuntu',
                    'module_url': 'https://cyberpanel.net/cyberpanel_ols-2.7.3-x86_64-ubuntu.so',
                    'modsec_url': 'https://cyberpanel.net/mod_security-2.5.0-x86_64-ubuntu.so',
                    'sha256': {
                        'binary': '2a836d4bf17fe5152d15dd60fd3817c1d3c294b48b35f12b776fa2efb7771422',
                        'module': 'f1c1ab881625fa6fe6545e45283220e86245a1e3c96e29c4d86af9ab15fd6c2b',
                        'modsec': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd',
                    },
                }
            }

            config = BINARY_CONFIGS.get(platform)
            if not config:
                InstallCyberPanel.stdOut(f"ERROR: No binaries available for platform {platform}", 1)
                InstallCyberPanel.stdOut("Skipping custom binary installation", 1)
                return True  # Not fatal

            OLS_BINARY_URL = config['url']
            MODULE_URL = config['module_url']
            MODSEC_URL = config.get('modsec_url')
            SHA256 = config.get('sha256', {})
            OLS_BINARY_PATH = "/usr/local/lsws/bin/openlitespeed"
            MODULE_PATH = "/usr/local/lsws/modules/cyberpanel_ols.so"
            MODSEC_PATH = "/usr/local/lsws/modules/mod_security.so"

            # Create backup
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_dir = f"/usr/local/lsws/backup-{timestamp}"

            try:
                os.makedirs(backup_dir, exist_ok=True)
                if os.path.exists(OLS_BINARY_PATH):
                    shutil.copy2(OLS_BINARY_PATH, f"{backup_dir}/openlitespeed.backup")
                    InstallCyberPanel.stdOut(f"Backup created at: {backup_dir}", 1)
                # Also backup existing ModSecurity if it exists
                if os.path.exists(MODSEC_PATH):
                    shutil.copy2(MODSEC_PATH, f"{backup_dir}/mod_security.so.backup")
            except Exception as e:
                InstallCyberPanel.stdOut(f"WARNING: Could not create backup: {e}", 1)

            # Download binaries to temp location
            tmp_binary = "/tmp/openlitespeed-custom"
            tmp_module = "/tmp/cyberpanel_ols.so"
            tmp_modsec = "/tmp/mod_security.so"

            InstallCyberPanel.stdOut("Downloading custom binaries...", 1)

            # Download OpenLiteSpeed binary
            if not self.downloadCustomBinary(OLS_BINARY_URL, tmp_binary):
                InstallCyberPanel.stdOut("ERROR: Failed to download or verify OLS binary", 1)
                InstallCyberPanel.stdOut("Continuing with standard OLS", 1)
                return True  # Not fatal, continue with standard OLS

            # Verify integrity (SHA256) and ABI compatibility (ldd) before touching the live install
            if not self.verifyChecksum(tmp_binary, SHA256.get('binary')):
                InstallCyberPanel.stdOut("ERROR: OLS binary failed checksum verification; keeping stock OLS", 1)
                return True  # Not fatal, continue with standard OLS
            if not self.checkGlibcCompat(tmp_binary):
                InstallCyberPanel.stdOut("ERROR: OLS binary is not ABI-compatible with this OS; keeping stock OLS", 1)
                return True  # Not fatal, continue with standard OLS

            # Download module (if available)
            module_downloaded = False
            if MODULE_URL:
                if not self.downloadCustomBinary(MODULE_URL, tmp_module):
                    InstallCyberPanel.stdOut("ERROR: Failed to download or verify module", 1)
                    InstallCyberPanel.stdOut("Continuing with standard OLS", 1)
                    return True  # Not fatal, continue with standard OLS
                if not self.verifyChecksum(tmp_module, SHA256.get('module')):
                    InstallCyberPanel.stdOut("ERROR: Module failed checksum verification; keeping stock OLS", 1)
                    return True  # Not fatal, continue with standard OLS
                module_downloaded = True
            else:
                InstallCyberPanel.stdOut("Note: No CyberPanel module for this platform", 1)

            # Download the matching ModSecurity WAF module (ABI-compatible with the
            # custom OLS binary). Non-fatal: if it fails the rest of the install proceeds.
            modsec_downloaded = False
            if MODSEC_URL:
                InstallCyberPanel.stdOut("Downloading ModSecurity WAF module...", 1)
                if self.downloadCustomBinary(MODSEC_URL, tmp_modsec):
                    if self.verifyChecksum(tmp_modsec, SHA256.get('modsec')):
                        modsec_downloaded = True
                    else:
                        InstallCyberPanel.stdOut("WARNING: ModSecurity failed checksum verification; continuing without it", 1)
                else:
                    InstallCyberPanel.stdOut("WARNING: Failed to download ModSecurity module; continuing without it", 1)

            # Install OpenLiteSpeed binary
            InstallCyberPanel.stdOut("Installing custom binaries...", 1)

            try:
                shutil.move(tmp_binary, OLS_BINARY_PATH)
                os.chmod(OLS_BINARY_PATH, 0o755)
                InstallCyberPanel.stdOut("Installed OpenLiteSpeed binary", 1)
            except Exception as e:
                InstallCyberPanel.stdOut(f"ERROR: Failed to install binary: {e}", 1)
                logging.InstallLog.writeToFile(str(e) + " [installCustomOLSBinaries - binary install]")
                return False

            # Install module (if downloaded)
            if module_downloaded:
                try:
                    os.makedirs(os.path.dirname(MODULE_PATH), exist_ok=True)
                    shutil.move(tmp_module, MODULE_PATH)
                    os.chmod(MODULE_PATH, 0o644)
                    InstallCyberPanel.stdOut("Installed CyberPanel module", 1)
                except Exception as e:
                    InstallCyberPanel.stdOut(f"ERROR: Failed to install module: {e}", 1)
                    logging.InstallLog.writeToFile(str(e) + " [installCustomOLSBinaries - module install]")
                    return False

            # Install ModSecurity WAF module (if downloaded)
            if modsec_downloaded:
                try:
                    os.makedirs(os.path.dirname(MODSEC_PATH), exist_ok=True)
                    shutil.move(tmp_modsec, MODSEC_PATH)
                    os.chmod(MODSEC_PATH, 0o644)
                    InstallCyberPanel.stdOut("Installed ModSecurity WAF module", 1)
                except Exception as e:
                    InstallCyberPanel.stdOut(f"WARNING: Failed to install ModSecurity: {e}", 1)
                    logging.InstallLog.writeToFile(str(e) + " [installCustomOLSBinaries - modsec install]")
                    # Non-fatal, continue

            # Verify installation - test the binary actually runs before declaring success
            if os.path.exists(OLS_BINARY_PATH):
                if not module_downloaded or os.path.exists(MODULE_PATH):
                    InstallCyberPanel.stdOut("Verifying new binary...", 1)
                    try:
                        result = subprocess.run(
                            [OLS_BINARY_PATH, '-v'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode != 0:
                            raise Exception(f"Binary test failed with exit code {result.returncode}")
                        version_output = result.stdout if result.stdout else result.stderr
                        if 'LiteSpeed' in version_output or 'OpenLiteSpeed' in version_output:
                            InstallCyberPanel.stdOut("Binary version check passed", 1)
                        else:
                            InstallCyberPanel.stdOut("WARNING: Could not verify binary version", 1)
                    except Exception as e:
                        # The custom binary doesn't run here - roll back to the stock binary
                        # that was backed up so the install is left with a working OLS.
                        InstallCyberPanel.stdOut(f"ERROR: Binary verification failed: {e}", 1)
                        logging.InstallLog.writeToFile(str(e) + " [installCustomOLSBinaries - verify]")
                        backup_binary = f"{backup_dir}/openlitespeed.backup"
                        if os.path.exists(backup_binary):
                            InstallCyberPanel.stdOut("Rolling back to stock OpenLiteSpeed binary...", 1)
                            try:
                                shutil.copy2(backup_binary, OLS_BINARY_PATH)
                                os.chmod(OLS_BINARY_PATH, 0o755)
                                backup_modsec = f"{backup_dir}/mod_security.so.backup"
                                if modsec_downloaded and os.path.exists(backup_modsec):
                                    shutil.copy2(backup_modsec, MODSEC_PATH)
                                InstallCyberPanel.stdOut("Rollback completed; using stock OLS", 1)
                            except Exception as rollback_err:
                                InstallCyberPanel.stdOut(f"WARNING: Rollback may have failed: {rollback_err}", 1)
                                logging.InstallLog.writeToFile(str(rollback_err) + " [installCustomOLSBinaries - rollback]")
                        return True  # Not fatal - stock OLS remains in place

                    InstallCyberPanel.stdOut("=" * 50, 1)
                    InstallCyberPanel.stdOut("Custom Binaries Installed Successfully", 1)
                    InstallCyberPanel.stdOut("Features enabled:", 1)
                    InstallCyberPanel.stdOut("  - Static-linked cross-platform binary", 1)
                    if module_downloaded:
                        InstallCyberPanel.stdOut("  - Apache-style .htaccess support", 1)
                        InstallCyberPanel.stdOut("  - php_value/php_flag directives", 1)
                        InstallCyberPanel.stdOut("  - Enhanced header control", 1)
                    if modsec_downloaded:
                        InstallCyberPanel.stdOut("  - ModSecurity WAF module", 1)
                    InstallCyberPanel.stdOut(f"Backup: {backup_dir}", 1)
                    InstallCyberPanel.stdOut("=" * 50, 1)
                    return True

            InstallCyberPanel.stdOut("ERROR: Installation verification failed", 1)
            return False

        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCustomOLSBinaries]")
            InstallCyberPanel.stdOut(f"ERROR: {msg}", 1)
            InstallCyberPanel.stdOut("Continuing with standard OLS", 1)
            return True  # Non-fatal error, continue

    def configureCustomModule(self):
        """Configure CyberPanel module in OpenLiteSpeed config"""
        try:
            InstallCyberPanel.stdOut("Configuring CyberPanel module...", 1)

            CONFIG_FILE = "/usr/local/lsws/conf/httpd_config.conf"

            if not os.path.exists(CONFIG_FILE):
                InstallCyberPanel.stdOut("WARNING: Config file not found", 1)
                InstallCyberPanel.stdOut("Module will be auto-loaded", 1)
                return True

            # Check if module is already configured
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
            if 'cyberpanel_ols' in content:
                # Module present - make sure it isn't disabled. A stray
                # 'ls_enabled 0' inside the block silently turns off LSCache
                # and every .htaccess feature, so flip it back on.
                import re
                new_content = re.sub(
                    r'(module\s+cyberpanel_ols\s*\{.*?\})',
                    lambda m: re.sub(r'ls_enabled\s+0', 'ls_enabled          1', m.group(0)),
                    content,
                    flags=re.DOTALL,
                )
                if new_content != content:
                    shutil.copy2(CONFIG_FILE, f"{CONFIG_FILE}.backup")
                    with open(CONFIG_FILE, 'w') as f:
                        f.write(new_content)
                    InstallCyberPanel.stdOut("Module was disabled (ls_enabled 0); re-enabled LSCache module", 1)
                else:
                    InstallCyberPanel.stdOut("Module already configured", 1)
                return True

            # Add module configuration
            module_config = """
module cyberpanel_ols {
  ls_enabled          1
}
"""
            # Backup config
            shutil.copy2(CONFIG_FILE, f"{CONFIG_FILE}.backup")

            # Append module config
            with open(CONFIG_FILE, 'a') as f:
                f.write(module_config)

            InstallCyberPanel.stdOut("Module configured successfully", 1)
            return True

        except Exception as msg:
            logging.InstallLog.writeToFile(str(msg) + " [configureCustomModule]")
            InstallCyberPanel.stdOut(f"WARNING: Module configuration failed: {msg}", 1)
            InstallCyberPanel.stdOut("Module may still work via auto-load", 1)
            return True  # Non-fatal

    def installLiteSpeed(self):
        if self.ent == 0:
            # Install standard OpenLiteSpeed package
            self.install_package('openlitespeed')

            # Install custom binaries with PHP config support
            # This replaces the standard binary with enhanced version
            self.installCustomOLSBinaries()

            # Configure the custom module
            self.configureCustomModule()

            # Enable Auto-SSL in httpd_config.conf
            try:
                import re
                conf_path = '/usr/local/lsws/conf/httpd_config.conf'
                if os.path.exists(conf_path):
                    with open(conf_path, 'r') as f:
                        content = f.read()
                    if 'autoSSL' not in content:
                        content = re.sub(
                            r'(adminEmails\s+\S+)',
                            r'\1\nautoSSL                   1\nacmeEmail                 admin@cyberpanel.net',
                            content,
                            count=1
                        )
                        with open(conf_path, 'w') as f:
                            f.write(content)
                        InstallCyberPanel.stdOut("Auto-SSL enabled in httpd_config.conf", 1)
            except Exception as e:
                InstallCyberPanel.stdOut(f"WARNING: Could not enable Auto-SSL: {e}", 1)

        else:
            try:
                try:
                    command = 'groupadd nobody'
                    install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass

                try:
                    command = 'usermod -a -G nobody nobody'
                    install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass

                # Get the latest LSWS Enterprise version dynamically
                lsws_version = InstallCyberPanel.getLatestLSWSVersion()

                if InstallCyberPanel.ISARM():
                    command = f'wget https://www.litespeedtech.com/packages/6.0/lsws-{lsws_version}-ent-aarch64-linux.tar.gz'
                else:
                    command = f'wget https://www.litespeedtech.com/packages/6.0/lsws-{lsws_version}-ent-x86_64-linux.tar.gz'

                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                if InstallCyberPanel.ISARM():
                    command = f'tar zxf lsws-{lsws_version}-ent-aarch64-linux.tar.gz'
                else:
                    command = f'tar zxf lsws-{lsws_version}-ent-x86_64-linux.tar.gz'

                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                if str.lower(self.serial) == 'trial':
                    command = f'wget -q --output-document=lsws-{lsws_version}/trial.key http://license.litespeedtech.com/reseller/trial.key'
                if self.serial == '1111-2222-3333-4444':
                    command = f'wget -q --output-document=/root/cyberpanel/install/lsws-{lsws_version}/trial.key http://license.litespeedtech.com/reseller/trial.key'
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                else:
                    writeSerial = open(f'lsws-{lsws_version}/serial.no', 'w')
                    writeSerial.writelines(self.serial)
                    writeSerial.close()

                shutil.copy('litespeed/install.sh', f'lsws-{lsws_version}/')
                shutil.copy('litespeed/functions.sh', f'lsws-{lsws_version}/')

                os.chdir(f'lsws-{lsws_version}')

                command = 'chmod +x install.sh'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'chmod +x functions.sh'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = './install.sh'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                os.chdir(self.cwd)
                confPath = '/usr/local/lsws/conf/'
                shutil.copy('litespeed/httpd_config.xml', confPath)
                shutil.copy('litespeed/modsec.conf', confPath)
                shutil.copy('litespeed/httpd.conf', confPath)

                command = 'chown -R lsadm:lsadm ' + confPath
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            except BaseException as msg:
                logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installLiteSpeed]")
                return 0

            return 1

    def reStartLiteSpeed(self):
        command = install_utils.format_restart_litespeed_command(self.server_root_path)
        install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def fix_ols_configs(self):
        try:

            InstallCyberPanel.stdOut("Fixing OpenLiteSpeed configurations!", 1)

            ## remove example virtual host

            data = open(self.server_root_path + "conf/httpd_config.conf", 'r').readlines()

            writeDataToFile = open(self.server_root_path + "conf/httpd_config.conf", 'w')

            for items in data:
                if items.find("map") > -1 and items.find("Example") > -1:
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            InstallCyberPanel.stdOut("OpenLiteSpeed Configurations fixed!", 1)
        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [fix_ols_configs]")
            return 0

        return self.reStartLiteSpeed()

    def changePortTo80(self):
        try:
            InstallCyberPanel.stdOut("Changing default port to 80..", 1)

            file_path = self.server_root_path + "conf/httpd_config.conf"
            if self.modify_file_content(file_path, {"*:8088": "*:80"}):
                InstallCyberPanel.stdOut("Default port is now 80 for OpenLiteSpeed!", 1)
            else:
                return 0

        except Exception as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [changePortTo80]")
            return 0

        return self.reStartLiteSpeed()

    def installAllPHPVersions(self):
        php_versions = ['71', '72', '73', '74', '80', '81', '82', '83']
        
        if self.distro == ubuntu:
            # Install base PHP 7.x packages
            command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                      'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                      'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                      'lsphp7?-sqlite3 lsphp7?-tidy'
            os.system(command)
            
            # Install PHP 8.x versions
            for version in php_versions[4:]:  # 80, 81, 82, 83
                self.install_package(f'lsphp{version}*')
                
        elif self.distro == centos:
            # First install the group
            command = 'yum -y groupinstall lsphp-all'
            install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)
            
            # Install individual PHP versions
            for version in php_versions:
                self.install_package(f'lsphp{version}*', '--skip-broken')
                
        elif self.distro == cent8:
            # Install PHP versions in batches with exclusions
            exclude_flags = "--exclude lsphp73-pecl-zip --exclude *imagick*"
            
            # First batch: PHP 7.x and 8.0
            versions_batch1 = ' '.join([f'lsphp{v}*' for v in php_versions[:5]])
            self.install_package(versions_batch1, f'{exclude_flags} --skip-broken')
            
            # Second batch: PHP 8.1+
            versions_batch2 = ' '.join([f'lsphp{v}*' for v in php_versions[5:]])
            self.install_package(versions_batch2, f'{exclude_flags} --skip-broken')
            
        elif self.distro == openeuler:
            # Install all PHP versions at once
            all_versions = ' '.join([f'lsphp{v}*' for v in php_versions])
            self.install_package(all_versions)
            
        if self.distro != ubuntu:
            InstallCyberPanel.stdOut("LiteSpeed PHPs successfully installed!", 1)

    def installSieve(self):
        """Install Sieve (Dovecot Sieve) for email filtering on all OS variants"""
        try:
            InstallCyberPanel.stdOut("Installing Sieve (Dovecot Sieve) for email filtering...", 1)

            if self.distro == ubuntu:
                # Install dovecot-sieve and dovecot-managesieved
                self.install_package('dovecot-sieve dovecot-managesieved')
            else:
                # For CentOS/AlmaLinux/OpenEuler
                self.install_package('dovecot-pigeonhole')

            # Write ManageSieve config
            managesieve_conf = '/etc/dovecot/conf.d/20-managesieve.conf'
            os.makedirs('/etc/dovecot/conf.d', exist_ok=True)
            with open(managesieve_conf, 'w') as f:
                f.write("""protocols = $protocols sieve

service managesieve-login {
  inet_listener sieve {
    port = 4190
  }
}

service managesieve {
  process_limit = 256
}

protocol sieve {
  managesieve_notify_capability = mailto
  managesieve_sieve_capability = fileinto reject envelope encoded-character vacation subaddress comparator-i;ascii-numeric relational regex imap4flags copy include variables body enotify environment mailbox date index ihave duplicate mime foreverypart extracttext
}
""")

            # Add Sieve port 4190 to firewall
            try:
                import firewall.core.fw as fw
                subprocess.call(['firewall-cmd', '--permanent', '--add-port=4190/tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.call(['firewall-cmd', '--reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # firewalld may not be available, try ufw
                subprocess.call(['ufw', 'allow', '4190/tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            InstallCyberPanel.stdOut("Sieve successfully installed and configured!", 1)
            return 1

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installSieve]")
            return 0

    @staticmethod
    def setupWebmail():
        """Set up Dovecot master user and webmail config for SSO"""
        try:
            # Skip if dovecot not installed
            if not os.path.exists('/etc/dovecot/dovecot.conf'):
                InstallCyberPanel.stdOut("Dovecot not installed, skipping webmail setup.", 1)
                return 1

            # Skip if already configured
            if os.path.exists('/etc/cyberpanel/webmail.conf') and os.path.exists('/etc/dovecot/master-users'):
                InstallCyberPanel.stdOut("Webmail master user already configured.", 1)
                return 1

            InstallCyberPanel.stdOut("Setting up webmail master user for SSO...", 1)

            import secrets, string
            chars = string.ascii_letters + string.digits
            master_password = ''.join(secrets.choice(chars) for _ in range(32))

            # Hash the password using doveadm
            result = subprocess.run(
                ['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', master_password],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logging.InstallLog.writeToFile('[ERROR] doveadm pw failed: ' + result.stderr + " [setupWebmail]")
                return 0

            password_hash = result.stdout.strip()

            # Write /etc/dovecot/master-users
            with open('/etc/dovecot/master-users', 'w') as f:
                f.write('cyberpanel_master:' + password_hash + '\n')
            os.chmod('/etc/dovecot/master-users', 0o600)
            subprocess.call(['chown', 'dovecot:dovecot', '/etc/dovecot/master-users'])

            # Ensure /etc/cyberpanel/ exists
            os.makedirs('/etc/cyberpanel', exist_ok=True)

            # Write /etc/cyberpanel/webmail.conf
            import json as json_module
            webmail_conf = {
                'master_user': 'cyberpanel_master',
                'master_password': master_password
            }
            with open('/etc/cyberpanel/webmail.conf', 'w') as f:
                json_module.dump(webmail_conf, f)
            os.chmod('/etc/cyberpanel/webmail.conf', 0o600)
            subprocess.call(['chown', 'cyberpanel:cyberpanel', '/etc/cyberpanel/webmail.conf'])

            # Patch dovecot.conf if master passdb block missing
            dovecot_conf_path = '/etc/dovecot/dovecot.conf'
            with open(dovecot_conf_path, 'r') as f:
                dovecot_content = f.read()

            if 'auth_master_user_separator' not in dovecot_content:
                master_block = """auth_master_user_separator = *

passdb {
    driver = passwd-file
    master = yes
    args = /etc/dovecot/master-users
    result_success = continue
}

"""
                dovecot_content = dovecot_content.replace(
                    'passdb {',
                    master_block + 'passdb {',
                    1
                )
                with open(dovecot_conf_path, 'w') as f:
                    f.write(dovecot_content)

            # Restart Dovecot to pick up changes
            subprocess.call(['systemctl', 'restart', 'dovecot'])

            InstallCyberPanel.stdOut("Webmail master user setup complete!", 1)
            return 1

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupWebmail]")
            return 0

    def installMySQL(self, mysql):

        ############## Install mariadb ######################

        if self.distro == ubuntu:

            command = 'DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common apt-transport-https curl -y'
            install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

            command = "mkdir -p /etc/apt/keyrings"
            install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'"
            install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            RepoPath = '/etc/apt/sources.list.d/mariadb.sources'
            RepoContent = f"""
# MariaDB 10.11 repository list - created 2023-12-11 07:53 UTC
# https://mariadb.org/download/
X-Repolib-Name: MariaDB
Types: deb
# deb.mariadb.org is a dynamic mirror if your preferred mirror goes offline. See https://mariadb.org/mirrorbits/ for details.
# URIs: https://deb.mariadb.org/10.11/ubuntu
URIs: https://mirrors.gigenet.com/mariadb/repo/10.11/ubuntu
Suites: jammy
Components: main main/debug
Signed-By: /etc/apt/keyrings/mariadb-keyring.pgp
"""

            if get_Ubuntu_release() > 21.00:
                command = 'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=10.11'
                result = install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)
                
                # If the download fails, use manual repo configuration as fallback
                if result != 1:
                    install_utils.writeToFile("MariaDB repo setup script failed, using manual configuration...")
                    
                    # First, ensure directories exist
                    command = 'mkdir -p /usr/share/keyrings /etc/apt/sources.list.d'
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                    
                    # Download and add MariaDB signing key
                    command = 'curl -fsSL https://mariadb.org/mariadb_release_signing_key.pgp | gpg --dearmor -o /usr/share/keyrings/mariadb-keyring.pgp'
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                    
                    # Use multiple mirror options for better reliability
                    RepoPath = '/etc/apt/sources.list.d/mariadb.list'
                    codename = get_Ubuntu_code_name()
                    RepoContent = f"""# MariaDB 10.11 repository list - manual fallback
# Primary mirror
deb [arch=amd64,arm64,ppc64el,s390x signed-by=/usr/share/keyrings/mariadb-keyring.pgp] https://mirror.mariadb.org/repo/10.11/ubuntu {codename} main

# Alternative mirrors (uncomment if primary fails)
# deb [arch=amd64,arm64,ppc64el,s390x signed-by=/usr/share/keyrings/mariadb-keyring.pgp] https://mirrors.gigenet.com/mariadb/repo/10.11/ubuntu {codename} main
# deb [arch=amd64,arm64,ppc64el,s390x signed-by=/usr/share/keyrings/mariadb-keyring.pgp] https://ftp.osuosl.org/pub/mariadb/repo/10.11/ubuntu {codename} main
"""
                    
                    WriteToFile = open(RepoPath, 'w')
                    WriteToFile.write(RepoContent)
                    WriteToFile.close()
                    
                    install_utils.writeToFile("Manual MariaDB repository configuration completed.")



            command = 'DEBIAN_FRONTEND=noninteractive apt-get update -y'
            install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)


            command = "DEBIAN_FRONTEND=noninteractive apt-get install mariadb-server -y"
        elif self.distro == centos:

            RepoPath = '/etc/yum.repos.d/mariadb.repo'
            RepoContent = f"""
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.11/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1            
"""
            WriteToFile = open(RepoPath, 'w')
            WriteToFile.write(RepoContent)
            WriteToFile.close()

            command = 'dnf install mariadb-server -y'
        elif self.distro == cent8 or self.distro == openeuler:

            clAPVersion = FetchCloudLinuxAlmaVersionVersion()
            type = clAPVersion.split('-')[0]
            version = int(clAPVersion.split('-')[1])


            if type == 'cl' and version >= 88:

                command = 'yum remove db-governor db-governor-mysql -y'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'yum install governor-mysql -y'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = '/usr/share/lve/dbgovernor/mysqlgovernor.py --mysql-version=mariadb106'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = '/usr/share/lve/dbgovernor/mysqlgovernor.py --install --yes'

            else:

                command = 'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=10.11'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'yum remove mariadb* -y'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'sudo dnf -qy module disable mariadb'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'sudo dnf module reset mariadb -y'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                # Disable problematic mariadb-maxscale repository to avoid 404 errors
                command = 'dnf config-manager --disable mariadb-maxscale'
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)

                # Clear dnf cache to avoid repository issues
                command = 'dnf clean all'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'dnf install MariaDB-server MariaDB-client MariaDB-backup -y'

        install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        ############## Start mariadb ######################

        self.startMariaDB()

    def changeMYSQLRootPassword(self):
        if self.remotemysql == 'OFF':
            if self.distro == ubuntu:
                passwordCMD = "use mysql;DROP DATABASE IF EXISTS test;DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%%';GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '%s';UPDATE user SET plugin='' WHERE User='root';flush privileges;" % (
                    InstallCyberPanel.mysql_Root_password)
            else:
                passwordCMD = "use mysql;DROP DATABASE IF EXISTS test;DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%%';GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' IDENTIFIED BY '%s';flush privileges;" % (
                    InstallCyberPanel.mysql_Root_password)

            # For AlmaLinux 9, try mysql command first, then mariadb
            if self.distro == cent8 or self.distro == openeuler:
                command = 'mysql -u root -e "' + passwordCMD + '"'
                result = install_utils.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)
                if result != 0:
                    # If mysql command fails, try mariadb
                    command = 'mariadb -u root -e "' + passwordCMD + '"'
                    install_utils.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)
            else:
                command = 'mariadb -u root -e "' + passwordCMD + '"'
                install_utils.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)

    def startMariaDB(self):

        if self.remotemysql == 'OFF':
            ############## Start mariadb ######################
            self.manage_service('mariadb', 'start')

            ############## Enable mariadb at system startup ######################

            if os.path.exists('/etc/systemd/system/mysqld.service'):
                os.remove('/etc/systemd/system/mysqld.service')
            if os.path.exists('/etc/systemd/system/mariadb.service'):
                os.remove('/etc/systemd/system/mariadb.service')

            self.manage_service('mariadb', 'enable')

    def fixMariaDB(self):
        self.stdOut("Setup MariaDB so it can support Cyberpanel's needs")

        conn = mariadb.connect(user='root', passwd=self.mysql_Root_password)
        cursor = conn.cursor()
        cursor.execute('set global innodb_file_per_table = on;')
        try:
            cursor.execute('set global innodb_file_format = Barracuda;')
            cursor.execute('set global innodb_large_prefix = on;')
        except BaseException as msg:
            self.stdOut('%s. [ERROR:335]' % (str(msg)))
        cursor.close()
        conn.close()

        try:
            fileName = '/etc/mysql/mariadb.conf.d/50-server.cnf'
            data = open(fileName, 'r').readlines()

            writeDataToFile = open(fileName, 'w')
            for line in data:
                writeDataToFile.write(line.replace('utf8mb4', 'utf8'))
            writeDataToFile.close()
        except IOError as err:
            self.stdOut("[ERROR] Error in setting: " + fileName + ": " + str(err), 1, 1, os.EX_OSERR)

        # Use the manage_service method for consistent service management
        if self.distro == cent8 or self.distro == openeuler:
            # Try mariadb first, then mysqld
            result = os.system('systemctl restart mariadb')
            if result != 0:
                os.system('systemctl restart mysqld')
        else:
            os.system('systemctl restart mariadb')

        self.stdOut("MariaDB is now setup so it can support Cyberpanel's needs")

    def installPureFTPD(self):
        if self.distro == ubuntu:
            self.install_package('pure-ftpd-mysql')

            if get_Ubuntu_release() == 18.10:
                # Special handling for Ubuntu 18.10
                packages = [
                    ('pure-ftpd-common_1.0.47-3_all.deb', 'wget https://rep.cyberpanel.net/pure-ftpd-common_1.0.47-3_all.deb'),
                    ('pure-ftpd-mysql_1.0.47-3_amd64.deb', 'wget https://rep.cyberpanel.net/pure-ftpd-mysql_1.0.47-3_amd64.deb')
                ]
                
                for filename, wget_cmd in packages:
                    install_utils.call(wget_cmd, self.distro, wget_cmd, wget_cmd, 1, 1, os.EX_OSERR)
                    command = f'dpkg --install --force-confold {filename}'
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        else:
            self.install_package('pure-ftpd')

        ####### Install pureftpd to system startup

        command = "systemctl enable " + install.preFlightsChecks.pureFTPDServiceName(self.distro)
        install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ###### FTP Groups and user settings settings

        command = 'groupadd -g 2001 ftpgroup'
        install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        command = 'useradd -u 2001 -s /bin/false -d /bin/null -c "pureftpd user" -g ftpgroup ftpuser'
        install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def startPureFTPD(self):
        ############## Start pureftpd ######################
        serviceName = install.preFlightsChecks.pureFTPDServiceName(self.distro)
        
        # During fresh installation, don't start Pure-FTPd yet
        # It will be started after Django migrations create the required tables
        InstallCyberPanel.stdOut("Pure-FTPd enabled for startup.", 1)
        InstallCyberPanel.stdOut("Note: Pure-FTPd will start after database setup is complete.", 1)
        logging.InstallLog.writeToFile("Pure-FTPd enabled but not started - waiting for Django migrations")

    def installPureFTPDConfigurations(self, mysql):
        try:
            ## setup ssl for ftp

            InstallCyberPanel.stdOut("Configuring PureFTPD..", 1)

            try:
                if not os.path.exists("/etc/ssl/private"):
                    os.makedirs("/etc/ssl/private", mode=0o755)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    logging.InstallLog.writeToFile("[ERROR] Could not create directory for FTP SSL: " + str(e))
                    raise

            if (self.distro == centos or self.distro == cent8 or self.distro == openeuler) or (
                    self.distro == ubuntu and get_Ubuntu_release() == 18.14):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
            else:
                command = 'openssl req -x509 -nodes -days 7300 -newkey rsa:2048 -subj "/C=US/ST=Denial/L=Sprinal-ield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'

            install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir(self.cwd)
            ftpdPath = "/etc/pure-ftpd"

            self.copy_config_file("pure-ftpd", ftpdPath, mysql)

            if self.distro == ubuntu:
                try:
                    os.mkdir('/etc/pure-ftpd/conf')
                    os.mkdir('/etc/pure-ftpd/auth')
                    os.mkdir('/etc/pure-ftpd/db')
                except OSError as err:
                    self.stdOut("[ERROR] Error creating extra pure-ftpd directories: " + str(err), ".  Should be ok", 1)

            data = open(ftpdPath + "/pureftpd-mysql.conf", "r").readlines()

            writeDataToFile = open(ftpdPath + "/pureftpd-mysql.conf", "w")

            dataWritten = "MYSQLPassword " + InstallCyberPanel.mysqlPassword + '\n'
            for items in data:
                if items.find("MYSQLPassword") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            ftpConfPath = '/etc/pure-ftpd/pureftpd-mysql.conf'

            if self.remotemysql == 'ON':
                command = "sed -i 's|localhost|%s|g' %s" % (self.mysqlhost, ftpConfPath)
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|3306|%s|g' %s" % (self.mysqlport, ftpConfPath)
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|MYSQLSocket /var/lib/mysql/mysql.sock||g' %s" % (ftpConfPath)
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro == ubuntu:

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'echo %s > /etc/pure-ftpd/conf/ForcePassiveIP' % (self.publicip)
                subprocess.call(command, shell=True)

                command = 'echo "40110 40210" > /etc/pure-ftpd/conf/PassivePortRange'
                subprocess.call(command, shell=True)

                command = 'echo "no" > /etc/pure-ftpd/conf/UnixAuthentication'
                subprocess.call(command, shell=True)

                command = 'echo "/etc/pure-ftpd/db/mysql.conf" > /etc/pure-ftpd/conf/MySQLConfigFile'
                subprocess.call(command, shell=True)

                command = 'ln -s /etc/pure-ftpd/conf/MySQLConfigFile /etc/pure-ftpd/auth/30mysql'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'ln -s /etc/pure-ftpd/conf/UnixAuthentication /etc/pure-ftpd/auth/65unix'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = 'systemctl restart pure-ftpd-mysql.service'
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)




                if get_Ubuntu_release() > 21.00:
                    ### change mysql md5 to crypt

                    command = "sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' /etc/pure-ftpd/db/mysql.conf"
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                    command = "systemctl restart pure-ftpd-mysql.service"
                    install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            else:

                try:
                    clAPVersion = FetchCloudLinuxAlmaVersionVersion()
                    type = clAPVersion.split('-')[0]
                    version = int(clAPVersion.split('-')[1])

                    if type == 'al' and version >= 90:
                        command = "sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' /etc/pure-ftpd/pureftpd-mysql.conf"
                        install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                except:
                    pass



            InstallCyberPanel.stdOut("PureFTPD configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPureFTPDConfigurations]")
            return 0

    def installPowerDNS(self):
        try:
            if self.distro == ubuntu or self.distro == cent8 or self.distro == openeuler:
                # Stop and disable systemd-resolved
                self.manage_service('systemd-resolved', 'stop')
                self.manage_service('systemd-resolved.service', 'disable')

                try:
                    os.rename('/etc/resolv.conf', '/etc/resolv.conf.bak')
                except OSError as e:
                    if e.errno != errno.EEXIST and e.errno != errno.ENOENT:
                        InstallCyberPanel.stdOut("[ERROR] Unable to rename /etc/resolv.conf to install PowerDNS: " +
                                                 str(e), 1, 1, os.EX_OSERR)
                
                # Create a temporary resolv.conf with Google DNS for package installation
                try:
                    with open('/etc/resolv.conf', 'w') as f:
                        f.write('nameserver 8.8.8.8\n')
                        f.write('nameserver 8.8.4.4\n')
                    InstallCyberPanel.stdOut("Created temporary /etc/resolv.conf with Google DNS", 1)
                except IOError as e:
                    InstallCyberPanel.stdOut("[ERROR] Unable to create /etc/resolv.conf: " + str(e), 1, 1, os.EX_OSERR)

            # Install PowerDNS packages
            if self.distro == ubuntu:
                # Update package list first
                command = "DEBIAN_FRONTEND=noninteractive apt-get update"
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                
                # Install PowerDNS packages
                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                
                # Ensure service is stopped after installation for configuration
                command = 'systemctl stop pdns || true'
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)
                return 1
            else:
                self.install_package('pdns pdns-backend-mysql')

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [powerDNS]")

    def installPowerDNSConfigurations(self, mysqlPassword, mysql):
        try:

            InstallCyberPanel.stdOut("Configuring PowerDNS..", 1)

            os.chdir(self.cwd)
            if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                dnsPath = "/etc/pdns/pdns.conf"
            else:
                dnsPath = "/etc/powerdns/pdns.conf"
                # Ensure directory exists for Ubuntu
                dnsDir = os.path.dirname(dnsPath)
                if not os.path.exists(dnsDir):
                    try:
                        os.makedirs(dnsDir, mode=0o755)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise

            try:
                self.copy_config_file("dns", dnsPath, mysql)
            except Exception as e:
                InstallCyberPanel.stdOut("[ERROR] Failed to copy PowerDNS config: " + str(e), 1)
                logging.InstallLog.writeToFile('[ERROR] Failed to copy PowerDNS config: ' + str(e))
                raise

            # Verify the file was copied and has content
            if not os.path.exists(dnsPath):
                raise IOError(f"PowerDNS config file not found at {dnsPath} after copy")
            
            # Check if file has content
            with open(dnsPath, "r") as f:
                content = f.read()
                if not content or "launch=gmysql" not in content:
                    InstallCyberPanel.stdOut("[WARNING] PowerDNS config appears empty or incomplete, attempting to fix...", 1)
                    
                    # First try to re-copy
                    try:
                        if os.path.exists(dnsPath):
                            os.remove(dnsPath)
                        source_file = os.path.join(self.cwd, "dns-one", "pdns.conf")
                        shutil.copy2(source_file, dnsPath)
                    except Exception as copy_error:
                        InstallCyberPanel.stdOut("[WARNING] Failed to re-copy config: " + str(copy_error), 1)
                        
                        # Fallback: directly write the essential MySQL configuration
                        InstallCyberPanel.stdOut("[INFO] Directly writing MySQL backend configuration...", 1)
                        try:
                            mysql_config = f"""# PowerDNS MySQL Backend Configuration
launch=gmysql
gmysql-host=localhost
gmysql-port=3306
gmysql-user=cyberpanel
gmysql-password={mysqlPassword}
gmysql-dbname=cyberpanel

# Basic PowerDNS settings
daemon=no
guardian=no
setgid=pdns
setuid=pdns
"""
                            # If file exists and has some content, append our config
                            if os.path.exists(dnsPath) and content.strip():
                                # Check if it's just missing the MySQL part
                                with open(dnsPath, "a") as f:
                                    f.write("\n\n" + mysql_config)
                            else:
                                # Write a complete minimal config
                                with open(dnsPath, "w") as f:
                                    f.write(mysql_config)
                            
                            InstallCyberPanel.stdOut("[SUCCESS] MySQL backend configuration written directly", 1)
                        except Exception as write_error:
                            InstallCyberPanel.stdOut("[ERROR] Failed to write MySQL config: " + str(write_error), 1)
                            raise
            
            InstallCyberPanel.stdOut("PowerDNS config file prepared at: " + dnsPath, 1)
            
            data = open(dnsPath, "r").readlines()

            writeDataToFile = open(dnsPath, "w")

            dataWritten = "gmysql-password=" + mysqlPassword + "\n"

            for items in data:
                if items.find("gmysql-password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                command = "sed -i 's|gmysql-host=localhost|gmysql-host=%s|g' %s" % (self.mysqlhost, dnsPath)
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|gmysql-port=3306|gmysql-port=%s|g' %s" % (self.mysqlport, dnsPath)
                install_utils.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            # Set proper permissions for PowerDNS config
            if self.distro == ubuntu:
                # Ensure pdns user/group exists
                command = 'id -u pdns &>/dev/null || useradd -r -s /usr/sbin/nologin pdns'
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                command = 'chown root:pdns %s' % dnsPath
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                command = 'chmod 640 %s' % dnsPath
                install_utils.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            InstallCyberPanel.stdOut("PowerDNS configured!", 1)

        except IOError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installPowerDNSConfigurations]")
            return 0
        return 1

    def startPowerDNS(self):

        ############## Start PowerDNS ######################

        self.manage_service('pdns', 'enable')
        
        # During fresh installation, don't start PowerDNS yet
        # It will be started after Django migrations create the required tables
        InstallCyberPanel.stdOut("PowerDNS enabled for startup.", 1)
        InstallCyberPanel.stdOut("Note: PowerDNS will start after database setup is complete.", 1)
        logging.InstallLog.writeToFile("PowerDNS enabled but not started - waiting for Django migrations")
        
        # The service will be started later after migrations run
        # or manually by the admin after installation completes


def Main(cwd, mysql, distro, ent, serial=None, port="8090", ftp=None, dns=None, publicip=None, remotemysql=None,
         mysqlhost=None, mysqldb=None, mysqluser=None, mysqlpassword=None, mysqlport=None):
    InstallCyberPanel.mysqlPassword = install_utils.generate_pass()
    InstallCyberPanel.mysql_Root_password = install_utils.generate_pass()

    file_name = '/etc/cyberpanel/mysqlPassword'

    if remotemysql == 'OFF':
        if os.access(file_name, os.F_OK):
            password = open(file_name, 'r')
            InstallCyberPanel.mysql_Root_password = password.readline()
            password.close()
        else:
            password = open(file_name, "w")
            password.writelines(InstallCyberPanel.mysql_Root_password)
            password.close()
    else:
        mysqlData = {'remotemysql': remotemysql, 'mysqlhost': mysqlhost, 'mysqldb': mysqldb, 'mysqluser': mysqluser,
                     'mysqlpassword': mysqlpassword, 'mysqlport': mysqlport}
        from json import dumps
        writeToFile = open(file_name, 'w')
        writeToFile.write(dumps(mysqlData))
        writeToFile.close()

        if install.preFlightsChecks.debug:
            print(open(file_name, 'r').read())
            time.sleep(10)

    try:
        command = 'chmod 640 %s' % (file_name)
        install_utils.call(command, distro, '[chmod]',
                                      '',
                                      1, 0, os.EX_OSERR)
        command = 'chown root:cyberpanel %s' % (file_name)
        install_utils.call(command, distro, '[chmod]',
                                      '',
                                      1, 0, os.EX_OSERR)
    except:
        pass

    # For RHEL-based systems (CentOS, AlmaLinux, Rocky, etc.), generate a separate password
    if distro in [centos, cent8, openeuler]:
        InstallCyberPanel.mysqlPassword = install_utils.generate_pass()
    else:
        # For Ubuntu/Debian, use the same password as root
        InstallCyberPanel.mysqlPassword = InstallCyberPanel.mysql_Root_password

    installer = InstallCyberPanel("/usr/local/lsws/", cwd, distro, ent, serial, port, ftp, dns, publicip, remotemysql,
                                  mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport)

    logging.InstallLog.writeToFile('Installing LiteSpeed Web server,40')
    installer.installLiteSpeed()
    if ent == 0:
        installer.changePortTo80()
    logging.InstallLog.writeToFile('Installing Optimized PHPs..,50')
    installer.installAllPHPVersions()
    if ent == 0:
        installer.fix_ols_configs()

    logging.InstallLog.writeToFile('Installing Sieve for email filtering..,55')
    installer.installSieve()

    ## setupWebmail is called later, after Dovecot is installed (see install.py)

    logging.InstallLog.writeToFile('Installing MySQL,60')
    installer.installMySQL(mysql)
    installer.changeMYSQLRootPassword()

    installer.startMariaDB()

    if remotemysql == 'OFF':
        if distro == ubuntu:
            installer.fixMariaDB()

    mysqlUtilities.createDatabase("cyberpanel", "cyberpanel", InstallCyberPanel.mysqlPassword, publicip)

    if ftp is None:
        installer.installPureFTPD()
        installer.installPureFTPDConfigurations(mysql)
        installer.startPureFTPD()
    else:
        if ftp == 'ON':
            installer.installPureFTPD()
            installer.installPureFTPDConfigurations(mysql)
            installer.startPureFTPD()

    if dns is None:
        installer.installPowerDNS()
        installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
        installer.startPowerDNS()
    else:
        if dns == 'ON':
            installer.installPowerDNS()
            installer.installPowerDNSConfigurations(InstallCyberPanel.mysqlPassword, mysql)
            installer.startPowerDNS()
