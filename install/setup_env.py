#!/usr/bin/env python3
"""
Environment setup script for CyberPanel
Automatically detects server IP and configures .env file
"""

import os
import socket
import urllib.request
import re
import shutil
from pathlib import Path

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
                    return ip
        except Exception:
            continue

    return None

def get_local_ip():
    """Get the local IP address of the server"""
    try:
        # Connect to a remote address to determine the local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None

def setup_env_file(cyberpanel_root="/usr/local/CyberCP"):
    """Set up the .env file with auto-detected IP addresses"""
    env_template_path = os.path.join(cyberpanel_root, ".env.template")
    env_path = os.path.join(cyberpanel_root, ".env")

    # Get IPs
    public_ip = get_public_ip()
    local_ip = get_local_ip()

    # Build ALLOWED_HOSTS list
    allowed_hosts = ['localhost', '127.0.0.1']

    if local_ip and local_ip not in allowed_hosts:
        allowed_hosts.append(local_ip)

    if public_ip and public_ip not in allowed_hosts:
        allowed_hosts.append(public_ip)

    # For maximum compatibility, also include wildcard
    # This ensures the server works regardless of how it's accessed
    allowed_hosts.append('*')

    allowed_hosts_str = ','.join(allowed_hosts)

    print(f"Auto-detected public IP: {public_ip}")
    print(f"Auto-detected local IP: {local_ip}")
    print(f"Setting ALLOWED_HOSTS to: {allowed_hosts_str}")

    # If .env doesn't exist, copy from template
    if not os.path.exists(env_path):
        if os.path.exists(env_template_path):
            shutil.copy2(env_template_path, env_path)
            print(f"Created .env file from template")
        else:
            print(f"Warning: Template file not found at {env_template_path}")
            return False

    # Update ALLOWED_HOSTS in .env file
    try:
        with open(env_path, 'r') as f:
            content = f.read()

        # Update ALLOWED_HOSTS line
        content = re.sub(
            r'^ALLOWED_HOSTS=.*$',
            f'ALLOWED_HOSTS={allowed_hosts_str}',
            content,
            flags=re.MULTILINE
        )

        with open(env_path, 'w') as f:
            f.write(content)

        print(f"Updated ALLOWED_HOSTS in {env_path}")
        return True

    except Exception as e:
        print(f"Error updating .env file: {e}")
        return False

if __name__ == "__main__":
    import sys

    # Allow custom path as argument
    cyberpanel_root = sys.argv[1] if len(sys.argv) > 1 else "/usr/local/CyberCP"

    success = setup_env_file(cyberpanel_root)
    sys.exit(0 if success else 1)