#!/usr/bin/env python3

"""
Test script for the dynamic version fetcher
"""

import sys
import os

# Add the plogical directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'plogical'))

try:
    from versionFetcher import VersionFetcher, get_latest_phpmyadmin_version, get_latest_snappymail_version
    
    print("=== Testing Dynamic Version Fetcher ===")
    print()
    
    # Test connectivity
    print("1. Testing GitHub API connectivity...")
    if VersionFetcher.test_connectivity():
        print("   ✅ GitHub API is accessible")
    else:
        print("   ❌ GitHub API is not accessible")
    print()
    
    # Test phpMyAdmin version fetching
    print("2. Testing phpMyAdmin version fetching...")
    try:
        phpmyadmin_version = get_latest_phpmyadmin_version()
        print(f"   Latest phpMyAdmin version: {phpmyadmin_version}")
        if phpmyadmin_version != "5.2.2":
            print("   ✅ Newer version found!")
        else:
            print("   ℹ️  Using fallback version (API may be unavailable)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test SnappyMail version fetching
    print("3. Testing SnappyMail version fetching...")
    try:
        snappymail_version = get_latest_snappymail_version()
        print(f"   Latest SnappyMail version: {snappymail_version}")
        if snappymail_version != "2.38.2":
            print("   ✅ Newer version found!")
        else:
            print("   ℹ️  Using fallback version (API may be unavailable)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test all versions
    print("4. Testing all versions...")
    try:
        all_versions = VersionFetcher.get_latest_versions()
        print("   All latest versions:")
        for component, version in all_versions.items():
            print(f"     {component}: {version}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("=== Test Complete ===")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the cyberpanel directory")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
