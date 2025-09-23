#!/usr/local/CyberCP/bin/python

import os
import sys
import argparse

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

import django
django.setup()

from repositorySync.repositorySyncManager import RepositorySyncManager
from plogical.upgrade import Upgrade

def main():
    parser = argparse.ArgumentParser(description='CyberPanel Repository Sync Tool')
    parser.add_argument('--force', action='store_true', help='Force sync even if conflicts exist')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--sync', action='store_true', help='Perform repository sync')
    
    args = parser.parse_args()
    
    if args.status:
        # Show sync status
        try:
            status = Upgrade.getRepositorySyncStatus()
            print("Repository Sync Status:")
            print(f"Last Sync: {status.get('last_sync', 'Never')}")
            print(f"Branches Synced: {status.get('branches_synced', [])}")
            print(f"Tags Synced: {status.get('tags_synced', False)}")
            if 'errors' in status:
                print(f"Errors: {status['errors']}")
        except Exception as e:
            print(f"Error getting status: {str(e)}")
            sys.exit(1)
    
    elif args.sync:
        # Perform sync
        try:
            print("Starting repository synchronization...")
            success, message = Upgrade.syncRepositoryToGitee(force_sync=args.force)
            if success:
                print(f"✓ {message}")
                sys.exit(0)
            else:
                print(f"✗ {message}")
                sys.exit(1)
        except Exception as e:
            print(f"Error during sync: {str(e)}")
            sys.exit(1)
    
    else:
        # Default action - perform sync
        try:
            print("Starting repository synchronization...")
            success, message = Upgrade.syncRepositoryToGitee(force_sync=args.force)
            if success:
                print(f"✓ {message}")
                sys.exit(0)
            else:
                print(f"✗ {message}")
                sys.exit(1)
        except Exception as e:
            print(f"Error during sync: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
