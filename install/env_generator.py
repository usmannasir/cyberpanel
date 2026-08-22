#!/usr/bin/env python3
"""
CyberPanel Environment Configuration Generator
Generates secure .env file with random passwords during installation
"""

import os
import sys
import secrets
import string
import socket
import urllib.request
import re
from pathlib import Path

def generate_secure_password(length=24):
    """
    Generate a cryptographically secure password
    
    Args:
        length: Length of the password to generate (default 24)
    
    Returns:
        str: Random password containing uppercase, lowercase, digits and safe special chars
    """
    # Use safe characters that don't require escaping in most contexts
    safe_chars = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(safe_chars) for _ in range(length))

def generate_secret_key(length=64):
    """
    Generate a cryptographically secure Django secret key

    Args:
        length: Length of the secret key to generate (default 64)

    Returns:
        str: Random secret key
    """
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

def get_public_ip():
    """Get the public IP address of the server using multiple methods"""
    methods = [
        'https://ipv4.icanhazip.com',
        'https://api.ipify.org',
        'https://checkip.amazonaws.com',
        'https://ipecho.net/plain'
    ]

    for url in methods:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                ip = response.read().decode('utf-8').strip()
                # Validate IP format
                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                    print(f"✓ Detected public IP: {ip}")
                    return ip
        except Exception as e:
            print(f"Failed to get IP from {url}: {e}")
            continue

    print("⚠️  Could not detect public IP address")
    return None

def get_local_ip():
    """Get the local IP address of the server"""
    try:
        # Connect to a remote address to determine the local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            print(f"✓ Detected local IP: {local_ip}")
            return local_ip
    except Exception as e:
        print(f"Failed to detect local IP: {e}")
        return None

class DatabaseConfigError(ValueError):
    """Raised when the requested database endpoint cannot be represented."""


# Values used for a normal, single-server installation. A remote installation
# overrides them through build_database_config().
LOCAL_DATABASE_CONFIG = {
    'db_name': 'cyberpanel',
    'db_user': 'cyberpanel',
    'db_host': 'localhost',
    'db_port': '3306',
    'root_db_name': 'mysql',
    'root_db_user': 'root',
    'root_db_host': 'localhost',
    'root_db_port': '3306',
}


def build_database_config(remote=False, host=None, port=None, root_db=None,
                          root_user=None):
    """
    Build the validated database endpoint used to render .env.

    The application connection (DB_*) and the administrative connection
    (ROOT_DB_*) are different users on the same server, so a remote
    installation has to move both. Passwords are not part of this structure;
    they are passed separately to create_env_file() so they never end up in a
    repr() or a log line.

    Args:
        remote: True for a remote MySQL installation
        host: --mysqlhost, the server hosting both connections
        port: --mysqlport
        root_db: --mysqldb, the administrative database (normally 'mysql')
        root_user: --mysqluser, the administrative account

    Returns:
        dict: the eight endpoint values, defaulted for a local install

    Raises:
        DatabaseConfigError: if a remote install is missing a required value
                             or the port is not a usable TCP port
    """
    config = dict(LOCAL_DATABASE_CONFIG)

    if not remote:
        return config

    # Fail here, before any package or database is touched, rather than
    # part-way through an installation that cannot succeed.
    if not host or not str(host).strip():
        raise DatabaseConfigError('Remote MySQL requires a host (--mysqlhost)')
    if not root_user or not str(root_user).strip():
        raise DatabaseConfigError(
            'Remote MySQL requires an administrative user (--mysqluser)')
    if not root_db or not str(root_db).strip():
        raise DatabaseConfigError(
            'Remote MySQL requires an administrative database (--mysqldb)')

    host = str(host).strip()
    # A bracketed IPv6 literal is how the address is written in a URL, but
    # MySQLdb and Django both want the bare address plus a separate port.
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    if ':' in host:
        # Colons are valid only in an IPv6 literal. In particular, reject a
        # host with an appended port because every consumer receives the port
        # separately.
        import ipaddress
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            raise DatabaseConfigError(
                'Remote MySQL host must be a DNS name or IP address')
    elif not re.fullmatch(r'[A-Za-z0-9_.-]+', host):
        # Several legacy service writers still use fixed sed commands. Keep
        # their replacement value to hostname characters so a direct install
        # invocation cannot turn the host argument into shell syntax.
        raise DatabaseConfigError(
            'Remote MySQL host must be a DNS name or IP address')

    port = str(port).strip() if port is not None else ''
    if not port:
        port = LOCAL_DATABASE_CONFIG['db_port']
    if not port.isdigit() or not (1 <= int(port) <= 65535):
        raise DatabaseConfigError(
            'Remote MySQL port must be a number between 1 and 65535, got %r'
            % (port,))

    # The port stays a port. Appending it to the host is the mistake that
    # produces 'db.example.com:3306:3306' further down the stack.
    config.update({
        'db_host': host,
        'db_port': port,
        'root_db_name': str(root_db).strip(),
        'root_db_user': str(root_user).strip(),
        'root_db_host': host,
        'root_db_port': port,
    })
    return config


def _format_mysql_option_value(value):
    """Quote one value for a MySQL option file without creating new keys."""
    text = '' if value is None else str(value)
    if '\n' in text or '\r' in text:
        raise DatabaseConfigError(
            'MySQL option values must fit on a single line')
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def build_mysql_client_config(password, remote=False, host=None, port=None,
                              user=None):
    """Render the administrative /root/.my.cnf used after installation.

    Local installations deliberately omit host and port so the client keeps
    using the Unix socket. Remote installations must name the same TCP endpoint
    and administrative user supplied to the installer.
    """
    if not remote:
        return ('[client]\nuser=root\npassword=%s\n'
                % _format_mysql_option_value(password))

    config = build_database_config(
        remote=True, host=host, port=port, root_db='mysql', root_user=user)
    return (
        '[client]\n'
        'user=%s\n'
        'password=%s\n'
        'host=%s\n'
        'port=%s\n'
        'protocol=TCP\n'
        % (
            _format_mysql_option_value(config['root_db_user']),
            _format_mysql_option_value(password),
            _format_mysql_option_value(config['root_db_host']),
            config['root_db_port'],
        )
    )


def format_env_value(value):
    """
    Serialise a value for a python-dotenv .env file.

    Generated passwords may contain '#', '$', quotes, backslashes or spaces.
    Written bare, a '#' starts a comment and a space truncates the value, so
    the credential that reaches Django is not the one that was created. Values
    that need it are double-quoted with the escapes python-dotenv understands;
    simple values are written unquoted so a local install produces the same
    file it always did.
    """
    text = '' if value is None else str(value)
    needs_quotes = (
        text != text.strip()
        or any(c in text for c in ' \t"\'\\#$`')
        or '\n' in text
        or '\r' in text
    )
    if not needs_quotes:
        return text
    # python-dotenv expands ${NAME} even inside single quotes. Replace the
    # opening sequence with a one-pass default expansion that evaluates to a
    # literal dollar sign; interpolation is not recursive, so the original
    # ${NAME} survives as credential data rather than becoming an environment
    # lookup on the panel host.
    text = text.replace('${', '${CYBERPANEL_LITERAL_DOLLAR:-$}{')
    escaped = (
        text.replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
    )
    return '"%s"' % escaped


def create_env_file(cyberpanel_path, mysql_root_password=None, cyberpanel_db_password=None,
                    database_config=None):
    """
    Create .env file with generated secure credentials
    
    Args:
        cyberpanel_path: Path to CyberPanel installation directory
        mysql_root_password: Optional MySQL root password (will generate if None)
        cyberpanel_db_password: Optional CyberPanel DB password (will generate if None)
        database_config: Optional endpoint from build_database_config(). Omitted
                         means a local installation, which is what every
                         pre-existing caller wants.
    """

    if database_config is None:
        database_config = dict(LOCAL_DATABASE_CONFIG)
    else:
        missing = set(LOCAL_DATABASE_CONFIG) - set(database_config)
        if missing:
            raise DatabaseConfigError(
                'database_config is missing: %s' % ', '.join(sorted(missing)))

    # Generate secure passwords if not provided
    if not mysql_root_password:
        mysql_root_password = generate_secure_password(24)
    
    if not cyberpanel_db_password:
        cyberpanel_db_password = generate_secure_password(24)
    
    secret_key = generate_secret_key(64)
    
    # Auto-detect IP addresses for ALLOWED_HOSTS
    print("🔍 Auto-detecting server IP addresses...")

    # Get hostname and local hostname resolution
    try:
        hostname = socket.gethostname()
        hostname_ip = socket.gethostbyname(hostname)
    except:
        hostname = 'localhost'
        hostname_ip = '127.0.0.1'

    # Get actual local IP address
    local_ip = get_local_ip()

    # Get public IP address
    public_ip = get_public_ip()

    # Build ALLOWED_HOSTS list with all detected IPs
    allowed_hosts = ['localhost', '127.0.0.1']

    # Add hostname if different from localhost
    if hostname and hostname != 'localhost':
        allowed_hosts.append(hostname)

    # Add hostname IP if different from localhost
    if hostname_ip and hostname_ip not in allowed_hosts:
        allowed_hosts.append(hostname_ip)

    # Add local IP if detected and different
    if local_ip and local_ip not in allowed_hosts:
        allowed_hosts.append(local_ip)

    # Add public IP if detected and different
    if public_ip and public_ip not in allowed_hosts:
        allowed_hosts.append(public_ip)

    # Add wildcard for maximum compatibility (allows any host)
    # This ensures CyberPanel works regardless of how the server is accessed
    allowed_hosts.append('*')

    allowed_hosts_str = ','.join(allowed_hosts)
    print(f"✓ ALLOWED_HOSTS configured: {allowed_hosts_str}")

    # Create .env content
    env_content = f"""# CyberPanel Environment Configuration
# Generated automatically during installation - DO NOT EDIT MANUALLY
# Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Django Configuration
SECRET_KEY={format_env_value(secret_key)}
DEBUG=False
ALLOWED_HOSTS={allowed_hosts_str}

# Database Configuration - CyberPanel Database
DB_NAME={format_env_value(database_config['db_name'])}
DB_USER={format_env_value(database_config['db_user'])}
DB_PASSWORD={format_env_value(cyberpanel_db_password)}
DB_HOST={format_env_value(database_config['db_host'])}
DB_PORT={format_env_value(database_config['db_port'])}

# Root Database Configuration - MySQL Administrative Access
ROOT_DB_NAME={format_env_value(database_config['root_db_name'])}
ROOT_DB_USER={format_env_value(database_config['root_db_user'])}
ROOT_DB_PASSWORD={format_env_value(mysql_root_password)}
ROOT_DB_HOST={format_env_value(database_config['root_db_host'])}
ROOT_DB_PORT={format_env_value(database_config['root_db_port'])}

# Security Settings
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# File Upload Settings
DATA_UPLOAD_MAX_MEMORY_SIZE=2147483648

# Logging Configuration
LOG_LEVEL=INFO
"""
    
    # Write .env file
    env_file_path = os.path.join(cyberpanel_path, '.env')
    with open(env_file_path, 'w') as f:
        f.write(env_content)
    
    # The panel worker needs the environment while credentials remain hidden
    # from every unrelated system account.
    os.chmod(env_file_path, 0o640)
    try:
        import shutil
        shutil.chown(env_file_path, user='root', group='cyberpanel')
    except (AttributeError, LookupError, OSError, PermissionError):
        # Unit tests and non-root development environments may not provide the
        # production service account.
        pass
    
    print(f"✓ Generated secure .env file at: {env_file_path}")
    # Installation output is captured into /var/log and pasted into support
    # threads, so the credentials themselves are never printed. They are in
    # the .env file and in the .env.backup written next to it.
    print("✓ Database credentials written to .env (not echoed)")
    _shown_host = database_config['db_host']
    if ':' in _shown_host:  # IPv6 literal, bracket it so the port is readable
        _shown_host = '[%s]' % _shown_host
    print(f"✓ Database endpoint: {_shown_host}:{database_config['db_port']}")

    return {
        'mysql_root_password': mysql_root_password,
        'cyberpanel_db_password': cyberpanel_db_password,
        'secret_key': secret_key
    }

def create_env_backup(cyberpanel_path, credentials):
    """
    Create a secure backup of credentials for recovery purposes
    
    Args:
        cyberpanel_path: Path to CyberPanel installation directory
        credentials: Dictionary containing generated credentials
    """
    backup_content = f"""# CyberPanel Credentials Backup
# Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 
# IMPORTANT: Store this file securely and delete it after recording credentials
# These are your database passwords and should be kept confidential

MySQL Root Password: {credentials['mysql_root_password']}
CyberPanel Database Password: {credentials['cyberpanel_db_password']}
Django Secret Key: {credentials['secret_key']}

# To restore these credentials, copy them to your .env file
"""
    
    backup_file_path = os.path.join(cyberpanel_path, '.env.backup')
    with open(backup_file_path, 'w') as f:
        f.write(backup_content)
    
    # Set secure permissions (owner read/write only)
    os.chmod(backup_file_path, 0o600)
    
    print(f"✓ Created credentials backup at: {backup_file_path}")
    print("⚠️  IMPORTANT: Record these credentials and delete the backup file for security")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python env_generator.py <cyberpanel_path> [mysql_root_password] [cyberpanel_db_password]")
        sys.exit(1)
    
    cyberpanel_path = sys.argv[1]
    mysql_root_password = sys.argv[2] if len(sys.argv) > 2 else None
    cyberpanel_db_password = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(cyberpanel_path):
        print(f"Error: CyberPanel path does not exist: {cyberpanel_path}")
        sys.exit(1)
    
    try:
        credentials = create_env_file(cyberpanel_path, mysql_root_password, cyberpanel_db_password)
        create_env_backup(cyberpanel_path, credentials)
        print("\n✓ Environment configuration generated successfully!")
        print("✓ Remember to delete .env.backup after recording credentials")
    except Exception as e:
        print(f"Error generating environment configuration: {e}")
        sys.exit(1)
