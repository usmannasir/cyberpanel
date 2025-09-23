#!/usr/local/CyberCP/bin/python
"""
Quick IP blocking script for CyberPanel
Usage: python block_ip.py <ip_address> [reason]
"""

import sys
import os
import django

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

try:
    django.setup()
except:
    pass

from plogical.firewallUtilities import FirewallUtilities

def main():
    if len(sys.argv) < 2:
        print("Usage: python block_ip.py <ip_address> [reason]")
        print("Example: python block_ip.py 192.168.1.100 'Suspicious activity'")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    reason = sys.argv[2] if len(sys.argv) > 2 else "Manual block via CLI"
    
    print(f"Blocking IP address: {ip_address}")
    print(f"Reason: {reason}")
    
    success, message = FirewallUtilities.blockIP(ip_address, reason)
    
    if success:
        print(f"✅ {message}")
        sys.exit(0)
    else:
        print(f"❌ {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()
