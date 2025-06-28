import os
import subprocess
import shutil
try:
    import installLog as logging
except ImportError:
    # Fallback if installLog is not available
    class logging:
        @staticmethod
        def writeToFile(message):
            print(message)


class PackageManager:
    """Handles package installation across different distributions"""
    
    @staticmethod
    def get_install_command(packages, distro, ubuntu=1, centos=0, cent8=2, openeuler=3):
        """Returns the appropriate install command for the distribution"""
        if distro == ubuntu:
            return f"DEBIAN_FRONTEND=noninteractive apt-get -y install {packages}"
        elif distro == centos:
            return f"yum install -y {packages}"
        else:  # cent8 or openeuler
            return f"dnf install -y {packages}"
    
    @staticmethod
    def install_packages(packages, distro, ubuntu=1, centos=0, cent8=2, openeuler=3, use_shell=False):
        """Install packages with proper error handling"""
        command = PackageManager.get_install_command(packages, distro, ubuntu, centos, cent8, openeuler)
        # Use subprocess directly to avoid circular import
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logging.writeToFile(f'[ERROR] Package installation failed: {command}')
            raise Exception(f'Package installation failed: {result.stderr}')
        return result.returncode


class ServiceManager:
    """Handles service operations across different distributions"""
    
    @staticmethod
    def manage_service(service_name, action, distro, exit_on_error=True):
        """Manage systemd services (start, stop, enable, disable, restart)"""
        command = f"systemctl {action} {service_name}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0 and exit_on_error:
            logging.writeToFile(f'[ERROR] Service management failed: {command}')
            raise Exception(f'Service management failed: {result.stderr}')
        return result.returncode
    
    @staticmethod
    def start_service(service_name, distro):
        """Start a service"""
        ServiceManager.manage_service(service_name, "start", distro)
    
    @staticmethod
    def stop_service(service_name, distro, exit_on_error=False):
        """Stop a service"""
        ServiceManager.manage_service(service_name, "stop", distro, exit_on_error)
    
    @staticmethod
    def enable_service(service_name, distro):
        """Enable a service at startup"""
        ServiceManager.manage_service(service_name, "enable", distro)
    
    @staticmethod
    def disable_service(service_name, distro, exit_on_error=False):
        """Disable a service at startup"""
        ServiceManager.manage_service(service_name, "disable", distro, exit_on_error)
    
    @staticmethod
    def restart_service(service_name, distro):
        """Restart a service"""
        ServiceManager.manage_service(service_name, "restart", distro)


class ConfigFileHandler:
    """Handles configuration file operations"""
    
    @staticmethod
    def replace_in_file(file_path, replacements):
        """
        Replace multiple patterns in a file
        replacements: list of tuples (search_pattern, replacement)
        """
        try:
            with open(file_path, 'r') as f:
                data = f.readlines()
            
            with open(file_path, 'w') as f:
                for line in data:
                    modified_line = line
                    for search_pattern, replacement in replacements:
                        if search_pattern in line:
                            modified_line = replacement + '\n' if not replacement.endswith('\n') else replacement
                            break
                    f.write(modified_line)
            return True
        except IOError as e:
            logging.InstallLog.writeToFile(f'[ERROR] {str(e)} [ConfigFileHandler.replace_in_file]')
            return False
    
    @staticmethod
    def sed_replace(file_path, search, replace, distro):
        """Use sed command for replacements"""
        command = f"sed -i 's|{search}|{replace}|g' {file_path}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logging.writeToFile(f'[ERROR] sed command failed: {command}')
            raise Exception(f'sed command failed: {result.stderr}')
        return result.returncode
    
    @staticmethod
    def copy_config_file(source, destination, remove_existing=True):
        """Copy configuration file with optional removal of existing file"""
        try:
            if remove_existing and os.path.exists(destination):
                os.remove(destination)
            shutil.copy(source, destination)
            return True
        except Exception as e:
            logging.InstallLog.writeToFile(f'[ERROR] {str(e)} [ConfigFileHandler.copy_config_file]')
            return False


class CommandExecutor:
    """Centralized command execution with consistent error handling"""
    
    @staticmethod
    def execute(command, distro, description=None, exit_on_error=True, exit_code=os.EX_OSERR):
        """Execute a command with standard error handling"""
        if description is None:
            description = command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            if exit_on_error:
                logging.writeToFile(f'[ERROR] Command failed: {command}')
                raise Exception(f'Command failed: {result.stderr}')
            else:
                logging.writeToFile(f'[WARNING] Command failed but continuing: {command}')
        return result.returncode
    
    @staticmethod
    def execute_with_output(command, shell=True):
        """Execute command and return output"""
        try:
            result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=shell)
        except:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  universal_newlines=True, shell=shell)
        return result


class PHPInstaller:
    """Handles PHP installation for different versions and distributions"""
    
    @staticmethod
    def install_php_ubuntu(versions=None):
        """Install PHP versions on Ubuntu"""
        if versions is None:
            # Include PHP 8.4 for Ubuntu 24.04
            versions = ['7?', '80', '81', '82', '83', '84']
        
        for version in versions:
            if version == '7?':
                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install ' \
                          'lsphp7? lsphp7?-common lsphp7?-curl lsphp7?-dev lsphp7?-imap lsphp7?-intl lsphp7?-json ' \
                          'lsphp7?-ldap lsphp7?-mysql lsphp7?-opcache lsphp7?-pspell lsphp7?-recode ' \
                          'lsphp7?-sqlite3 lsphp7?-tidy'
            else:
                command = f'DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp{version}*'
            os.system(command)
    
    @staticmethod
    def install_php_centos(distro, centos=0, cent8=2, openeuler=3):
        """Install PHP versions on CentOS/RHEL based systems"""
        if distro == centos:
            # First install the group
            command = 'yum -y groupinstall lsphp-all'
            subprocess.run(command, shell=True, check=True)
            
            # Then install individual versions
            versions = ['71', '72', '73', '74', '80', '81', '82', '83']
            for version in versions:
                command = f'yum install -y lsphp{version}* --skip-broken'
                subprocess.call(command, shell=True)
        
        elif distro == cent8:
            command = 'dnf install lsphp71* lsphp72* lsphp73* lsphp74* lsphp80* --exclude lsphp73-pecl-zip --exclude *imagick* -y --skip-broken'
            subprocess.call(command, shell=True)
            
            command = 'dnf install lsphp81* lsphp82* lsphp83* --exclude *imagick* -y --skip-broken'
            subprocess.call(command, shell=True)
        
        elif distro == openeuler:
            command = 'dnf install lsphp71* lsphp72* lsphp73* lsphp74* lsphp80* lsphp81* lsphp82* lsphp83* -y'
            subprocess.call(command, shell=True)


class FileSystemHelper:
    """Helper for file system operations"""
    
    @staticmethod
    def create_directory(path, exit_on_error=False):
        """Create directory with error handling"""
        try:
            os.mkdir(path)
            return True
        except OSError as e:
            if exit_on_error:
                raise
            logging.InstallLog.writeToFile(f"[ERROR] Could not create directory {path}: {str(e)}")
            return False
    
    @staticmethod
    def create_user_and_group(user, group, uid, gid, shell="/bin/false", home="/bin/null", distro=None):
        """Create system user and group"""
        # Create group
        command = f'groupadd -g {gid} {group}'
        CommandExecutor.execute(command, distro, exit_on_error=True)
        
        # Create user
        command = f'useradd -u {uid} -s {shell} -d {home} -c "{user} user" -g {group} {user}'
        CommandExecutor.execute(command, distro, exit_on_error=True)


class DistroHandler:
    """Handles distribution-specific operations"""
    
    # Distribution constants
    CENTOS = 0
    UBUNTU = 1
    CENT8 = 2
    OPENEULER = 3
    
    @staticmethod
    def is_rhel_based(distro):
        """Check if distribution is RHEL-based"""
        return distro in [DistroHandler.CENTOS, DistroHandler.CENT8, DistroHandler.OPENEULER]
    
    @staticmethod
    def is_debian_based(distro):
        """Check if distribution is Debian-based"""
        return distro == DistroHandler.UBUNTU
    
    @staticmethod
    def get_package_manager(distro):
        """Get the package manager for the distribution"""
        if distro == DistroHandler.UBUNTU:
            return "apt-get"
        elif distro == DistroHandler.CENTOS:
            return "yum"
        else:  # CENT8, OPENEULER
            return "dnf"
    
    @staticmethod
    def get_service_name(base_service, distro):
        """Get distribution-specific service name"""
        # Add logic for service name mapping if needed
        service_map = {
            'mysql': {
                DistroHandler.UBUNTU: 'mysql',
                DistroHandler.CENTOS: 'mariadb',
                DistroHandler.CENT8: 'mariadb',
                DistroHandler.OPENEULER: 'mariadb'
            }
        }
        
        if base_service in service_map and distro in service_map[base_service]:
            return service_map[base_service][distro]
        return base_service


class PermissionManager:
    """Handles file permissions and ownership"""
    
    @staticmethod
    def set_permissions(path, mode, distro, owner=None, group=None):
        """Set file permissions and optionally ownership"""
        # Set permissions
        CommandExecutor.execute(f'chmod {mode} {path}', distro)
        
        # Set ownership if specified
        if owner or group:
            owner_str = owner if owner else ""
            group_str = group if group else ""
            if owner and group:
                ownership = f"{owner}:{group}"
            elif owner:
                ownership = owner
            else:
                ownership = f":{group}"
            
            CommandExecutor.execute(f'chown {ownership} {path}', distro)
    
    @staticmethod
    def batch_set_permissions(permission_list, distro):
        """Apply multiple permission changes efficiently"""
        for perm in permission_list:
            PermissionManager.set_permissions(
                perm['path'], 
                perm['mode'], 
                distro,
                perm.get('owner'), 
                perm.get('group')
            )


class DownloadHelper:
    """Helper for downloading and extracting files"""
    
    @staticmethod
    def download_file(url, destination, distro):
        """Download a file using wget"""
        command = f'wget -O {destination} {url}' if destination else f'wget {url}'
        CommandExecutor.execute(command, distro)
    
    @staticmethod
    def extract_archive(archive_path, destination, distro, archive_type='tar'):
        """Extract an archive file"""
        if archive_type == 'tar':
            command = f'tar -xf {archive_path} -C {destination}'
        elif archive_type == 'tar.gz':
            command = f'tar -xzf {archive_path} -C {destination}'
        elif archive_type == 'zip':
            command = f'unzip {archive_path} -d {destination}'
        else:
            raise ValueError(f"Unsupported archive type: {archive_type}")
        
        CommandExecutor.execute(command, distro)
    
    @staticmethod
    def download_and_extract(url, extract_dir, distro, archive_type='tar.gz'):
        """Download and extract in one operation"""
        filename = os.path.basename(url)
        DownloadHelper.download_file(url, filename, distro)
        DownloadHelper.extract_archive(filename, extract_dir, distro, archive_type)
        return filename


class SSLCertificateHelper:
    """Helper for SSL certificate operations"""
    
    @staticmethod
    def generate_self_signed_cert(cert_path, key_path, distro, days=3650, 
                                  subject="/C=US/ST=State/L=City/O=Org/CN=localhost"):
        """Generate a self-signed SSL certificate"""
        command = (f'openssl req -x509 -nodes -days {days} -newkey rsa:2048 '
                  f'-subj "{subject}" -keyout {key_path} -out {cert_path}')
        CommandExecutor.execute(command, distro)
    
    @staticmethod
    def generate_csr(key_path, csr_path, distro, 
                     subject="/C=US/ST=State/L=City/O=Org/CN=localhost"):
        """Generate a certificate signing request"""
        command = (f'openssl req -new -key {key_path} -out {csr_path} '
                  f'-subj "{subject}"')
        CommandExecutor.execute(command, distro)