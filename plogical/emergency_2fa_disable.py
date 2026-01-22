#!/usr/bin/env python
"""
Emergency script to temporarily disable 2FA for a locked-out admin user.
Run this script from the command line with the username as an argument.

Usage: python emergency_2fa_disable.py <username>
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from loginSystem.models import Administrator


def disable_2fa(username):
    """Temporarily disable 2FA for the specified user"""
    try:
        admin = Administrator.objects.get(userName=username)
        if admin.twoFA:
            admin.twoFA = 0
            admin.save()
            print(f"2FA has been temporarily disabled for user: {username}")
            print("Please login and re-enable 2FA from your account settings.")
        else:
            print(f"2FA is already disabled for user: {username}")
    except Administrator.DoesNotExist:
        print(f"User not found: {username}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python emergency_2fa_disable.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    disable_2fa(username)