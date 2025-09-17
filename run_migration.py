#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script for UserNotificationPreferences model
Run this script to apply the database migration for notification preferences
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/usr/local/CyberCP')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Running migration for UserNotificationPreferences...")
    try:
        execute_from_command_line(['manage.py', 'migrate', 'baseTemplate'])
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
