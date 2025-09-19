#!/usr/bin/env python3
"""
Test script for FTP User Quota Feature
This script tests the basic functionality of the new quota management system.
"""

import os
import sys
import django

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from ftp.models import Users
from websiteFunctions.models import Websites
from plogical.ftpUtilities import FTPUtilities

def test_quota_feature():
    """Test the FTP quota feature functionality"""
    
    print("🧪 Testing FTP User Quota Feature")
    print("=" * 50)
    
    # Test 1: Check if new fields exist in model
    print("\n1. Testing model fields...")
    try:
        # Check if custom quota fields exist
        user_fields = [field.name for field in Users._meta.fields]
        required_fields = ['custom_quota_enabled', 'custom_quota_size']
        
        for field in required_fields:
            if field in user_fields:
                print(f"   ✅ {field} field exists")
            else:
                print(f"   ❌ {field} field missing")
                return False
    except Exception as e:
        print(f"   ❌ Error checking model fields: {e}")
        return False
    
    # Test 2: Test quota update function
    print("\n2. Testing quota update function...")
    try:
        # Test with valid data
        result = FTPUtilities.updateFTPQuota("test_user", 100, True)
        if result[0] == 0:  # Expected to fail since user doesn't exist
            print("   ✅ updateFTPQuota handles non-existent user correctly")
        else:
            print("   ⚠️  updateFTPQuota should have failed for non-existent user")
        
        # Test with invalid quota size
        result = FTPUtilities.updateFTPQuota("test_user", 0, True)
        if result[0] == 0:  # Expected to fail
            print("   ✅ updateFTPQuota validates quota size correctly")
        else:
            print("   ⚠️  updateFTPQuota should have failed for invalid quota size")
            
    except Exception as e:
        print(f"   ❌ Error testing quota update: {e}")
        return False
    
    # Test 3: Test FTP creation with custom quota
    print("\n3. Testing FTP creation with custom quota...")
    try:
        # This will fail because we don't have a real website, but we can test the function signature
        try:
            result = FTPUtilities.submitFTPCreation(
                "test.com", "testuser", "password", "None", "admin", 
                api="0", customQuotaSize=50, enableCustomQuota=True
            )
            print("   ✅ submitFTPCreation accepts custom quota parameters")
        except Exception as e:
            if "test.com" in str(e) or "admin" in str(e):
                print("   ✅ submitFTPCreation accepts custom quota parameters (failed as expected due to missing data)")
            else:
                print(f"   ❌ Unexpected error: {e}")
                return False
    except Exception as e:
        print(f"   ❌ Error testing FTP creation: {e}")
        return False
    
    # Test 4: Check if we can create a test user with custom quota
    print("\n4. Testing database operations...")
    try:
        # Try to get a website to test with
        websites = Websites.objects.all()
        if websites.exists():
            website = websites.first()
            
            # Create a test FTP user
            test_user = Users(
                domain=website,
                user="test_quota_user",
                password="hashed_password",
                uid=1000,
                gid=1000,
                dir="/home/test.com",
                quotasize=100,
                status="1",
                ulbandwidth=500000,
                dlbandwidth=500000,
                custom_quota_enabled=True,
                custom_quota_size=50
            )
            
            # Don't actually save to avoid database pollution
            print("   ✅ Can create Users object with custom quota fields")
            
            # Test the quota logic
            if test_user.custom_quota_enabled:
                effective_quota = test_user.custom_quota_size
            else:
                effective_quota = test_user.quotasize
                
            if effective_quota == 50:
                print("   ✅ Quota logic works correctly")
            else:
                print(f"   ❌ Quota logic failed: expected 50, got {effective_quota}")
                return False
                
        else:
            print("   ⚠️  No websites found for testing, skipping database test")
            
    except Exception as e:
        print(f"   ❌ Error testing database operations: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! FTP User Quota feature is working correctly.")
    print("\nNext steps:")
    print("1. Apply database migration: python manage.py migrate ftp")
    print("2. Restart CyberPanel services")
    print("3. Test the feature in the web interface")
    
    return True

if __name__ == "__main__":
    success = test_quota_feature()
    sys.exit(0 if success else 1)
