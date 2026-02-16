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

def create_env_file(cyberpanel_path, mysql_root_password=None, cyberpanel_db_password=None):
    """
    Create .env file with generated secure credentials
    
    Args:
        cyberpanel_path: Path to CyberPanel installation directory
        mysql_root_password: Optional MySQL root password (will generate if None)
        cyberpanel_db_password: Optional CyberPanel DB password (will generate if None)
    """
    
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
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS={allowed_hosts_str}

# Database Configuration - CyberPanel Database
DB_NAME=cyberpanel
DB_USER=cyberpanel
DB_PASSWORD={cyberpanel_db_password}
DB_HOST=localhost
DB_PORT=3306

# Root Database Configuration - MySQL Root Access
ROOT_DB_NAME=mysql
ROOT_DB_USER=root
ROOT_DB_PASSWORD={mysql_root_password}
ROOT_DB_HOST=localhost
ROOT_DB_PORT=3306

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
    
    # Set secure permissions (owner read/write only)
    os.chmod(env_file_path, 0o600)
    
    print(f"✓ Generated secure .env file at: {env_file_path}")
    print(f"✓ MySQL Root Password: {mysql_root_password}")
    print(f"✓ CyberPanel DB Password: {cyberpanel_db_password}")
    print(f"✓ Django Secret Key: {secret_key[:20]}...")
    
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
