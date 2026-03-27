#!/usr/bin/env python3
"""
CyberPanel Universal OS Compatibility Fixes
Ensures installer works on ALL supported operating systems
"""

import os
import sys
import subprocess
import platform
import json
import logging
from typing import Dict, List, Tuple, Optional

class UniversalOSFixes:
    """Universal OS compatibility fixes for CyberPanel installer"""
    
    def __init__(self):
        self.os_info = self.detect_os_info()
        self.logger = self.setup_logging()
        
        # Supported OS matrix
        self.supported_os = {
            'ubuntu': ['24.04', '22.04', '20.04'],
            'debian': ['13', '12', '11'],
            'almalinux': ['10', '9', '8'],
            'rocky': ['9', '8'],
            'rhel': ['9', '8'],
            'cloudlinux': ['9', '8'],
            'centos': ['7', '9'],
            'centos_stream': ['9']
        }
        
        # Package mappings for different OS
        self.package_mappings = {
            'ubuntu': {
                'python_dev': 'python3-dev',
                'build_tools': 'build-essential',
                'ssl_dev': 'libssl-dev',
                'ffi_dev': 'libffi-dev',
                'mysql_dev': 'libmariadb-dev',
                'memcached_dev': 'libmemcached-dev',
                'curl_dev': 'libcurl4-openssl-dev',
                'zlib_dev': 'zlib1g-dev',
                'xml_dev': 'libxml2-dev',
                'xslt_dev': 'libxslt1-dev',
                'jpeg_dev': 'libjpeg-dev',
                'png_dev': 'libpng-dev',
                'freetype_dev': 'libfreetype6-dev',
                'icu_dev': 'libicu-dev',
                'oniguruma_dev': 'libonig-dev',
                'aspell_dev': 'libaspell-dev',
                'enchant_dev': 'libenchant-2-dev',
                'tidy_dev': 'libtidy-dev',
                'zip_dev': 'libzip-dev',
                'sqlite_dev': 'libsqlite3-dev',
                'readline_dev': 'libreadline-dev',
                'ncurses_dev': 'libncurses5-dev',
                'bz2_dev': 'libbz2-dev',
                'lzma_dev': 'liblzma-dev',
                'gdbm_dev': 'libgdbm-dev',
                'db_dev': 'libdb-dev',
                'nss_dev': 'libnss3-dev',
                'krb5_dev': 'libkrb5-dev',
                'ldap_dev': 'libldap2-dev',
                'sasl_dev': 'libsasl2-dev',
                'gssapi_dev': 'libgssapi-krb5-2',
                'expat_dev': 'libexpat1-dev',
                'cairo_dev': 'libcairo2-dev',
                'pango_dev': 'libpango1.0-dev',
                'atk_dev': 'libatk1.0-dev',
                'gtk_dev': 'libgtk-3-dev',
                'gdk_dev': 'libgdk-pixbuf2.0-dev',
                'x11_dev': 'libx11-dev',
                'xext_dev': 'libxext-dev',
                'xrender_dev': 'libxrender-dev',
                'xfixes_dev': 'libxfixes-dev',
                'xdamage_dev': 'libxdamage-dev',
                'xcomposite_dev': 'libxcomposite-dev',
                'xrandr_dev': 'libxrandr-dev',
                'xss_dev': 'libxss-dev',
                'xinerama_dev': 'libxinerama-dev',
                'xcursor_dev': 'libxcursor-dev',
                'xi_dev': 'libxi-dev',
                'xtst_dev': 'libxtst-dev',
                'xrandr_dev': 'libxrandr-dev',
                'xss_dev': 'libxss-dev',
                'xinerama_dev': 'libxinerama-dev',
                'xcursor_dev': 'libxcursor-dev',
                'xi_dev': 'libxi-dev',
                'xtst_dev': 'libxtst-dev'
            },
            'debian': {
                'python_dev': 'python3-dev',
                'build_tools': 'build-essential',
                'ssl_dev': 'libssl-dev',
                'ffi_dev': 'libffi-dev',
                'mysql_dev': 'libmariadb-dev',
                'memcached_dev': 'libmemcached-dev',
                'curl_dev': 'libcurl4-openssl-dev',
                'zlib_dev': 'zlib1g-dev',
                'xml_dev': 'libxml2-dev',
                'xslt_dev': 'libxslt1-dev',
                'jpeg_dev': 'libjpeg-dev',
                'png_dev': 'libpng-dev',
                'freetype_dev': 'libfreetype6-dev',
                'icu_dev': 'libicu-dev',
                'oniguruma_dev': 'libonig-dev',
                'aspell_dev': 'libaspell-dev',
                'enchant_dev': 'libenchant-2-dev',
                'tidy_dev': 'libtidy-dev',
                'zip_dev': 'libzip-dev',
                'sqlite_dev': 'libsqlite3-dev',
                'readline_dev': 'libreadline-dev',
                'ncurses_dev': 'libncurses5-dev',
                'bz2_dev': 'libbz2-dev',
                'lzma_dev': 'liblzma-dev',
                'gdbm_dev': 'libgdbm-dev',
                'db_dev': 'libdb-dev',
                'nss_dev': 'libnss3-dev',
                'krb5_dev': 'libkrb5-dev',
                'ldap_dev': 'libldap2-dev',
                'sasl_dev': 'libsasl2-dev',
                'gssapi_dev': 'libgssapi-krb5-2',
                'expat_dev': 'libexpat1-dev'
            },
            'almalinux': {
                'python_dev': 'python3-devel',
                'build_tools': 'gcc gcc-c++ make',
                'ssl_dev': 'openssl-devel',
                'ffi_dev': 'libffi-devel',
                'mysql_dev': 'mariadb-devel',
                'memcached_dev': 'libmemcached-devel',
                'curl_dev': 'libcurl-devel',
                'zlib_dev': 'zlib-devel',
                'xml_dev': 'libxml2-devel',
                'xslt_dev': 'libxslt-devel',
                'jpeg_dev': 'libjpeg-turbo-devel',
                'png_dev': 'libpng-devel',
                'freetype_dev': 'freetype-devel',
                'icu_dev': 'libicu-devel',
                'oniguruma_dev': 'oniguruma-devel',
                'aspell_dev': 'aspell-devel',
                'enchant_dev': 'enchant-devel',
                'tidy_dev': 'tidy-devel',
                'zip_dev': 'libzip-devel',
                'sqlite_dev': 'sqlite-devel',
                'readline_dev': 'readline-devel',
                'ncurses_dev': 'ncurses-devel',
                'bz2_dev': 'bzip2-devel',
                'lzma_dev': 'xz-devel',
                'gdbm_dev': 'gdbm-devel',
                'db_dev': 'db4-devel',
                'nss_dev': 'nss-devel',
                'krb5_dev': 'krb5-devel',
                'ldap_dev': 'openldap-devel',
                'sasl_dev': 'cyrus-sasl-devel',
                'gssapi_dev': 'libgssapi-krb5',
                'expat_dev': 'expat-devel',
                'cairo_dev': 'cairo-devel',
                'pango_dev': 'pango-devel',
                'atk_dev': 'atk-devel',
                'gtk_dev': 'gtk3-devel',
                'gdk_dev': 'gdk-pixbuf2-devel',
                'x11_dev': 'libX11-devel',
                'xext_dev': 'libXext-devel',
                'xrender_dev': 'libXrender-devel',
                'xfixes_dev': 'libXfixes-devel',
                'xdamage_dev': 'libXdamage-devel',
                'xcomposite_dev': 'libXcomposite-devel',
                'xrandr_dev': 'libXrandr-devel',
                'xss_dev': 'libXScrnSaver-devel',
                'xinerama_dev': 'libXinerama-devel',
                'xcursor_dev': 'libXcursor-devel',
                'xi_dev': 'libXi-devel',
                'xtst_dev': 'libXtst-devel'
            },
            'rocky': {
                'python_dev': 'python3-devel',
                'build_tools': 'gcc gcc-c++ make',
                'ssl_dev': 'openssl-devel',
                'ffi_dev': 'libffi-devel',
                'mysql_dev': 'mariadb-devel',
                'memcached_dev': 'libmemcached-devel',
                'curl_dev': 'libcurl-devel',
                'zlib_dev': 'zlib-devel',
                'xml_dev': 'libxml2-devel',
                'xslt_dev': 'libxslt-devel',
                'jpeg_dev': 'libjpeg-turbo-devel',
                'png_dev': 'libpng-devel',
                'freetype_dev': 'freetype-devel',
                'icu_dev': 'libicu-devel',
                'oniguruma_dev': 'oniguruma-devel',
                'aspell_dev': 'aspell-devel',
                'enchant_dev': 'enchant-devel',
                'tidy_dev': 'tidy-devel',
                'zip_dev': 'libzip-devel',
                'sqlite_dev': 'sqlite-devel',
                'readline_dev': 'readline-devel',
                'ncurses_dev': 'ncurses-devel',
                'bz2_dev': 'bzip2-devel',
                'lzma_dev': 'xz-devel',
                'gdbm_dev': 'gdbm-devel',
                'db_dev': 'db4-devel',
                'nss_dev': 'nss-devel',
                'krb5_dev': 'krb5-devel',
                'ldap_dev': 'openldap-devel',
                'sasl_dev': 'cyrus-sasl-devel',
                'gssapi_dev': 'libgssapi-krb5',
                'expat_dev': 'expat-devel'
            },
            'rhel': {
                'python_dev': 'python3-devel',
                'build_tools': 'gcc gcc-c++ make',
                'ssl_dev': 'openssl-devel',
                'ffi_dev': 'libffi-devel',
                'mysql_dev': 'mariadb-devel',
                'memcached_dev': 'libmemcached-devel',
                'curl_dev': 'libcurl-devel',
                'zlib_dev': 'zlib-devel',
                'xml_dev': 'libxml2-devel',
                'xslt_dev': 'libxslt-devel',
                'jpeg_dev': 'libjpeg-turbo-devel',
                'png_dev': 'libpng-devel',
                'freetype_dev': 'freetype-devel',
                'icu_dev': 'libicu-devel',
                'oniguruma_dev': 'oniguruma-devel',
                'aspell_dev': 'aspell-devel',
                'enchant_dev': 'enchant-devel',
                'tidy_dev': 'tidy-devel',
                'zip_dev': 'libzip-devel',
                'sqlite_dev': 'sqlite-devel',
                'readline_dev': 'readline-devel',
                'ncurses_dev': 'ncurses-devel',
                'bz2_dev': 'bzip2-devel',
                'lzma_dev': 'xz-devel',
                'gdbm_dev': 'gdbm-devel',
                'db_dev': 'db4-devel',
                'nss_dev': 'nss-devel',
                'krb5_dev': 'krb5-devel',
                'ldap_dev': 'openldap-devel',
                'sasl_dev': 'cyrus-sasl-devel',
                'gssapi_dev': 'libgssapi-krb5',
                'expat_dev': 'expat-devel'
            },
            'cloudlinux': {
                'python_dev': 'python3-devel',
                'build_tools': 'gcc gcc-c++ make',
                'ssl_dev': 'openssl-devel',
                'ffi_dev': 'libffi-devel',
                'mysql_dev': 'mariadb-devel',
                'memcached_dev': 'libmemcached-devel',
                'curl_dev': 'libcurl-devel',
                'zlib_dev': 'zlib-devel',
                'xml_dev': 'libxml2-devel',
                'xslt_dev': 'libxslt-devel',
                'jpeg_dev': 'libjpeg-turbo-devel',
                'png_dev': 'libpng-devel',
                'freetype_dev': 'freetype-devel',
                'icu_dev': 'libicu-devel',
                'oniguruma_dev': 'oniguruma-devel',
                'aspell_dev': 'aspell-devel',
                'enchant_dev': 'enchant-devel',
                'tidy_dev': 'tidy-devel',
                'zip_dev': 'libzip-devel',
                'sqlite_dev': 'sqlite-devel',
                'readline_dev': 'readline-devel',
                'ncurses_dev': 'ncurses-devel',
                'bz2_dev': 'bzip2-devel',
                'lzma_dev': 'xz-devel',
                'gdbm_dev': 'gdbm-devel',
                'db_dev': 'db4-devel',
                'nss_dev': 'nss-devel',
                'krb5_dev': 'krb5-devel',
                'ldap_dev': 'openldap-devel',
                'sasl_dev': 'cyrus-sasl-devel',
                'gssapi_dev': 'libgssapi-krb5',
                'expat_dev': 'expat-devel'
            },
            'centos': {
                'python_dev': 'python3-devel',
                'build_tools': 'gcc gcc-c++ make',
                'ssl_dev': 'openssl-devel',
                'ffi_dev': 'libffi-devel',
                'mysql_dev': 'mariadb-devel',
                'memcached_dev': 'libmemcached-devel',
                'curl_dev': 'libcurl-devel',
                'zlib_dev': 'zlib-devel',
                'xml_dev': 'libxml2-devel',
                'xslt_dev': 'libxslt-devel',
                'jpeg_dev': 'libjpeg-turbo-devel',
                'png_dev': 'libpng-devel',
                'freetype_dev': 'freetype-devel',
                'icu_dev': 'libicu-devel',
                'oniguruma_dev': 'oniguruma-devel',
                'aspell_dev': 'aspell-devel',
                'enchant_dev': 'enchant-devel',
                'tidy_dev': 'tidy-devel',
                'zip_dev': 'libzip-devel',
                'sqlite_dev': 'sqlite-devel',
                'readline_dev': 'readline-devel',
                'ncurses_dev': 'ncurses-devel',
                'bz2_dev': 'bzip2-devel',
                'lzma_dev': 'xz-devel',
                'gdbm_dev': 'gdbm-devel',
                'db_dev': 'db4-devel',
                'nss_dev': 'nss-devel',
                'krb5_dev': 'krb5-devel',
                'ldap_dev': 'openldap-devel',
                'sasl_dev': 'cyrus-sasl-devel',
                'gssapi_dev': 'libgssapi-krb5',
                'expat_dev': 'expat-devel'
            }
        }
        
        # Repository configurations
        self.repo_configs = {
            'ubuntu': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/ubuntu/',
                'php': 'https://packages.sury.org/php/'
            },
            'debian': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/debian/',
                'php': 'https://packages.sury.org/php/'
            },
            'almalinux': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/centos/',
                'php': 'https://rpms.remirepo.net/enterprise/'
            },
            'rocky': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/centos/',
                'php': 'https://rpms.remirepo.net/enterprise/'
            },
            'rhel': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/centos/',
                'php': 'https://rpms.remirepo.net/enterprise/'
            },
            'cloudlinux': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/centos/',
                'php': 'https://rpms.remirepo.net/enterprise/'
            },
            'centos': {
                'mariadb': 'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                'litespeed': 'http://rpms.litespeedtech.com/centos/',
                'php': 'https://rpms.remirepo.net/enterprise/'
            }
        }
    
    def detect_os_info(self) -> Dict[str, str]:
        """Detect operating system information"""
        try:
            with open('/etc/os-release', 'r') as f:
                os_release = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os_release[key] = value.strip('"')
            
            # Normalize OS names
            os_name = os_release.get('NAME', '').lower()
            os_id = os_release.get('ID', '').lower()
            os_version = os_release.get('VERSION_ID', '')
            
            # Handle special cases
            if 'ubuntu' in os_name or os_id == 'ubuntu':
                return {'name': 'ubuntu', 'version': os_version, 'id': 'ubuntu'}
            elif 'debian' in os_name or os_id == 'debian':
                return {'name': 'debian', 'version': os_version, 'id': 'debian'}
            elif 'almalinux' in os_name or os_id == 'almalinux':
                return {'name': 'almalinux', 'version': os_version, 'id': 'almalinux'}
            elif 'rocky' in os_name or os_id == 'rocky':
                return {'name': 'rocky', 'version': os_version, 'id': 'rocky'}
            elif 'red hat' in os_name or os_id == 'rhel':
                return {'name': 'rhel', 'version': os_version, 'id': 'rhel'}
            elif 'cloudlinux' in os_name or os_id == 'cloudlinux':
                return {'name': 'cloudlinux', 'version': os_version, 'id': 'cloudlinux'}
            elif 'centos' in os_name or os_id == 'centos':
                return {'name': 'centos', 'version': os_version, 'id': 'centos'}
            else:
                return {'name': os_name, 'version': os_version, 'id': os_id}
                
        except Exception as e:
            self.logger.error(f"Error detecting OS: {e}")
            return {'name': 'unknown', 'version': 'unknown', 'id': 'unknown'}
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger('UniversalOSFixes')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def is_os_supported(self) -> bool:
        """Check if current OS is supported"""
        os_id = self.os_info['id']
        os_version = self.os_info['version']
        
        if os_id in self.supported_os:
            if os_version in self.supported_os[os_id]:
                return True
            else:
                self.logger.warning(f"OS version {os_version} not explicitly supported for {os_id}")
                return True  # Still try to install
        
        return False
    
    def get_package_name(self, package_key: str) -> str:
        """Get package name for current OS"""
        os_id = self.os_info['id']
        
        if os_id in self.package_mappings:
            return self.package_mappings[os_id].get(package_key, package_key)
        
        return package_key
    
    def get_package_manager_command(self) -> str:
        """Get package manager command for current OS"""
        os_id = self.os_info['id']
        
        if os_id in ['ubuntu', 'debian']:
            return 'apt'
        elif os_id in ['almalinux', 'rocky', 'rhel', 'cloudlinux', 'centos']:
            # Check if dnf is available
            try:
                subprocess.run(['which', 'dnf'], check=True, capture_output=True)
                return 'dnf'
            except subprocess.CalledProcessError:
                return 'yum'
        
        return 'unknown'
    
    def install_packages(self, packages: List[str]) -> bool:
        """Install packages using appropriate package manager"""
        try:
            package_manager = self.get_package_manager_command()
            
            if package_manager == 'apt':
                cmd = ['apt', 'update']
                subprocess.run(cmd, check=True)
                cmd = ['apt', 'install', '-y'] + packages
            elif package_manager == 'dnf':
                cmd = ['dnf', 'install', '-y'] + packages
            elif package_manager == 'yum':
                cmd = ['yum', 'install', '-y'] + packages
            else:
                self.logger.error(f"Unknown package manager: {package_manager}")
                return False
            
            subprocess.run(cmd, check=True)
            self.logger.info(f"Successfully installed packages: {packages}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install packages {packages}: {e}")
            return False
    
    def setup_mariadb_repository(self) -> bool:
        """Setup MariaDB repository for current OS"""
        try:
            os_id = self.os_info['id']
            
            if os_id in ['ubuntu', 'debian']:
                # Ubuntu/Debian MariaDB setup
                cmd = [
                    'curl', '-LsS', 
                    'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                    '|', 'sudo', 'bash', '-s', '--', '--mariadb-server-version=11.8'
                ]
            else:
                # RHEL family MariaDB setup
                cmd = [
                    'curl', '-LsS',
                    'https://downloads.mariadb.com/MariaDB/mariadb_repo_setup',
                    '|', 'sudo', 'bash', '-s', '--', '--mariadb-server-version=11.8'
                ]
            
            subprocess.run(' '.join(cmd), shell=True, check=True)
            if os_id in ['ubuntu', 'debian']:
                try:
                    import install_utils
                    install_utils.strip_mariadb_maxscale_apt_repos()
                except Exception:
                    pass
            self.logger.info("MariaDB repository setup completed")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to setup MariaDB repository: {e}")
            return False
    
    def setup_litespeed_repository(self) -> bool:
        """Setup LiteSpeed repository for current OS"""
        try:
            os_id = self.os_info['id']
            os_version = self.os_info['version']
            
            if os_id in ['ubuntu', 'debian']:
                # Ubuntu/Debian LiteSpeed setup
                cmd = [
                    'wget', '-O', '-', 
                    'https://cyberpanel.sh/litespeed/litespeed-repo.sh'
                ]
                subprocess.run(cmd, check=True)
                cmd = ['bash', 'litespeed-repo.sh']
                subprocess.run(cmd, check=True)
            else:
                # RHEL family LiteSpeed setup
                # Use el8 repository for AlmaLinux 9/10 compatibility
                if os_id in ['almalinux', 'rocky', 'rhel'] and int(os_version.split('.')[0]) >= 9:
                    repo_url = 'http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm'
                else:
                    repo_url = f'http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el{os_version.split(".")[0]}.noarch.rpm'
                
                cmd = ['rpm', '-Uvh', repo_url]
                subprocess.run(cmd, check=True)
            
            self.logger.info("LiteSpeed repository setup completed")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to setup LiteSpeed repository: {e}")
            return False
    
    def install_essential_packages(self) -> bool:
        """Install essential packages for CyberPanel"""
        try:
            os_id = self.os_info['id']
            
            # Common packages
            common_packages = [
                'curl', 'wget', 'git', 'python3', 'python3-pip',
                'unzip', 'tar', 'gzip', 'bzip2', 'xz'
            ]
            
            # OS-specific packages
            if os_id in ['ubuntu', 'debian']:
                packages = common_packages + [
                    'build-essential', 'python3-dev', 'libssl-dev',
                    'libffi-dev', 'libmariadb-dev', 'libcurl4-openssl-dev',
                    'zlib1g-dev', 'libxml2-dev', 'libxslt1-dev',
                    'libjpeg-dev', 'libpng-dev', 'libfreetype6-dev',
                    'libicu-dev', 'libonig-dev', 'libaspell-dev',
                    'libenchant-2-dev', 'libtidy-dev', 'libzip-dev',
                    'libsqlite3-dev', 'libreadline-dev', 'libncurses5-dev',
                    'libbz2-dev', 'liblzma-dev', 'libgdbm-dev',
                    'libdb-dev', 'libnss3-dev', 'libkrb5-dev',
                    'libldap2-dev', 'libsasl2-dev', 'libgssapi-krb5-2',
                    'libexpat1-dev'
                ]
            else:
                # RHEL family packages
                packages = common_packages + [
                    'gcc', 'gcc-c++', 'make', 'python3-devel',
                    'openssl-devel', 'libffi-devel', 'mariadb-devel',
                    'libcurl-devel', 'zlib-devel', 'libxml2-devel',
                    'libxslt-devel', 'libjpeg-turbo-devel', 'libpng-devel',
                    'freetype-devel', 'libicu-devel', 'oniguruma-devel',
                    'aspell-devel', 'enchant-devel', 'tidy-devel',
                    'libzip-devel', 'sqlite-devel', 'readline-devel',
                    'ncurses-devel', 'bzip2-devel', 'xz-devel',
                    'gdbm-devel', 'db4-devel', 'nss-devel',
                    'krb5-devel', 'openldap-devel', 'cyrus-sasl-devel',
                    'libgssapi-krb5', 'expat-devel'
                ]
            
            return self.install_packages(packages)
            
        except Exception as e:
            self.logger.error(f"Failed to install essential packages: {e}")
            return False
    
    def install_mariadb(self) -> bool:
        """Install MariaDB for current OS"""
        try:
            os_id = self.os_info['id']
            
            if os_id in ['ubuntu', 'debian']:
                packages = ['mariadb-server', 'mariadb-client', 'mariadb-common']
            else:
                packages = ['mariadb-server', 'mariadb', 'mariadb-devel']
            
            return self.install_packages(packages)
            
        except Exception as e:
            self.logger.error(f"Failed to install MariaDB: {e}")
            return False
    
    def install_openlitespeed(self) -> bool:
        """Install OpenLiteSpeed for current OS"""
        try:
            os_id = self.os_info['id']
            
            if os_id in ['ubuntu', 'debian']:
                packages = ['openlitespeed']
            else:
                packages = ['openlitespeed']
            
            return self.install_packages(packages)
            
        except Exception as e:
            self.logger.error(f"Failed to install OpenLiteSpeed: {e}")
            return False
    
    def create_systemd_services(self) -> bool:
        """Create systemd services for CyberPanel"""
        try:
            # Create LiteSpeed service
            lsws_service = """[Unit]
Description=LiteSpeed Web Server
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/lsws/bin/lswsctrl start
ExecReload=/usr/local/lsws/bin/lswsctrl restart
ExecStop=/usr/local/lsws/bin/lswsctrl stop
PIDFile=/usr/local/lsws/logs/httpd.pid
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
            
            with open('/etc/systemd/system/lsws.service', 'w') as f:
                f.write(lsws_service)
            
            # Create CyberPanel service
            cyberpanel_service = """[Unit]
Description=CyberPanel
After=network.target lsws.service

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/CyberCP
ExecStart=/usr/local/CyberPanel-venv/bin/python3 manage.py runserver 0.0.0.0:8090
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
            
            with open('/etc/systemd/system/cyberpanel.service', 'w') as f:
                f.write(cyberpanel_service)
            
            # Reload systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            self.logger.info("Systemd services created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create systemd services: {e}")
            return False
    
    def apply_os_specific_fixes(self) -> bool:
        """Apply OS-specific fixes"""
        try:
            os_id = self.os_info['id']
            os_version = self.os_info['version']
            
            if os_id == 'almalinux' and int(os_version.split('.')[0]) >= 9:
                # AlmaLinux 9+ specific fixes
                self.logger.info("Applying AlmaLinux 9+ specific fixes...")
                
                # Enable PowerTools repository
                try:
                    subprocess.run(['dnf', 'config-manager', '--set-enabled', 'powertools'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        subprocess.run(['dnf', 'config-manager', '--set-enabled', 'PowerTools'], check=True)
                    except subprocess.CalledProcessError:
                        self.logger.warning("Could not enable PowerTools repository")
                
                # Install compatibility packages
                compatibility_packages = [
                    'compat-openssl11', 'compat-openssl11-devel',
                    'libxcrypt-compat', 'libnsl'
                ]
                
                for package in compatibility_packages:
                    try:
                        subprocess.run(['dnf', 'install', '-y', package], check=True)
                    except subprocess.CalledProcessError:
                        self.logger.warning(f"Could not install compatibility package: {package}")
            
            elif os_id == 'rocky' and int(os_version.split('.')[0]) >= 9:
                # RockyLinux 9+ specific fixes
                self.logger.info("Applying RockyLinux 9+ specific fixes...")
                
                # Enable PowerTools repository
                try:
                    subprocess.run(['dnf', 'config-manager', '--set-enabled', 'powertools'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        subprocess.run(['dnf', 'config-manager', '--set-enabled', 'PowerTools'], check=True)
                    except subprocess.CalledProcessError:
                        self.logger.warning("Could not enable PowerTools repository")
            
            elif os_id == 'ubuntu' and os_version in ['24.04', '22.04']:
                # Ubuntu 24.04/22.04 specific fixes
                self.logger.info("Applying Ubuntu 24.04/22.04 specific fixes...")
                
                # Update package lists
                subprocess.run(['apt', 'update'], check=True)
                
                # Install additional packages
                additional_packages = [
                    'software-properties-common', 'apt-transport-https',
                    'ca-certificates', 'gnupg', 'lsb-release'
                ]
                
                self.install_packages(additional_packages)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply OS-specific fixes: {e}")
            return False
    
    def run_comprehensive_setup(self) -> bool:
        """Run comprehensive setup for all supported OS"""
        try:
            self.logger.info(f"Starting comprehensive setup for {self.os_info['name']} {self.os_info['version']}")
            
            # Check OS support
            if not self.is_os_supported():
                self.logger.error(f"OS {self.os_info['name']} {self.os_info['version']} is not supported")
                return False
            
            # Apply OS-specific fixes
            if not self.apply_os_specific_fixes():
                self.logger.error("Failed to apply OS-specific fixes")
                return False
            
            # Setup repositories
            if not self.setup_mariadb_repository():
                self.logger.error("Failed to setup MariaDB repository")
                return False
            
            if not self.setup_litespeed_repository():
                self.logger.error("Failed to setup LiteSpeed repository")
                return False
            
            # Install packages
            if not self.install_essential_packages():
                self.logger.error("Failed to install essential packages")
                return False
            
            if not self.install_mariadb():
                self.logger.error("Failed to install MariaDB")
                return False
            
            if not self.install_openlitespeed():
                self.logger.error("Failed to install OpenLiteSpeed")
                return False
            
            # Create services
            if not self.create_systemd_services():
                self.logger.error("Failed to create systemd services")
                return False
            
            self.logger.info("Comprehensive setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Comprehensive setup failed: {e}")
            return False

def main():
    """Main function"""
    fixes = UniversalOSFixes()
    
    print(f"CyberPanel Universal OS Compatibility Fixes")
    print(f"Detected OS: {fixes.os_info['name']} {fixes.os_info['version']}")
    print(f"OS ID: {fixes.os_info['id']}")
    
    if fixes.run_comprehensive_setup():
        print("✅ Setup completed successfully!")
        return 0
    else:
        print("❌ Setup failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
