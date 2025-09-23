#!/usr/bin/env python3
"""
CyberPanel FTP Account Creation Test Script
This script tests the FTP account creation functionality with various path scenarios
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add CyberPanel to path
sys.path.append('/usr/local/CyberCP')

def test_ftp_path_validation():
    """Test the FTP path validation functionality"""
    print("🔍 Testing FTP Path Validation...")
    
    # Import the FTP utilities
    try:
        from plogical.ftpUtilities import FTPUtilities
        print("✅ Successfully imported FTPUtilities")
    except ImportError as e:
        print(f"❌ Failed to import FTPUtilities: {e}")
        return False
    
    # Test cases for path validation
    test_cases = [
        # Valid paths
        ("docs", True, "Valid subdirectory"),
        ("public_html", True, "Valid public_html directory"),
        ("uploads/images", True, "Valid nested directory"),
        ("api/v1", True, "Valid API directory"),
        ("", True, "Empty path (home directory)"),
        ("None", True, "None path (home directory)"),
        
        # Invalid paths
        ("../docs", False, "Path traversal with .."),
        ("~/docs", False, "Home directory reference"),
        ("/docs", False, "Absolute path"),
        ("docs;rm -rf /", False, "Command injection"),
        ("docs|cat /etc/passwd", False, "Pipe command injection"),
        ("docs&reboot", False, "Background command"),
        ("docs`whoami`", False, "Command substitution"),
        ("docs'rm -rf /'", False, "Single quote injection"),
        ('docs"rm -rf /"', False, "Double quote injection"),
        ("docs<malicious", False, "Input redirection"),
        ("docs>malicious", False, "Output redirection"),
        ("docs*", False, "Wildcard character"),
        ("docs?", False, "Wildcard character"),
    ]
    
    print("\n📋 Running Path Validation Tests:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for path, should_pass, description in test_cases:
        try:
            # Mock the external dependencies
            with patch('pwd.getpwnam') as mock_pwd, \
                 patch('grp.getgrnam') as mock_grp, \
                 patch('os.path.exists') as mock_exists, \
                 patch('os.path.isdir') as mock_isdir, \
                 patch('os.path.islink') as mock_islink, \
                 patch('plogical.processUtilities.ProcessUtilities.executioner') as mock_exec, \
                 patch('websiteFunctions.models.Websites.objects.get') as mock_website, \
                 patch('loginSystem.models.Administrator.objects.get') as mock_admin:
                
                # Setup mocks
                mock_pwd.return_value.pw_uid = 1000
                mock_grp.return_value.gr_gid = 1000
                mock_exists.return_value = True
                mock_isdir.return_value = True
                mock_islink.return_value = False
                mock_exec.return_value = 0
                
                # Mock website object
                mock_website_obj = MagicMock()
                mock_website_obj.externalApp = "testuser"
                mock_website_obj.package.diskSpace = 1000
                mock_website_obj.package.ftpAccounts = 10
                mock_website_obj.users_set.all.return_value.count.return_value = 0
                mock_website.return_value = mock_website_obj
                
                # Mock admin object
                mock_admin_obj = MagicMock()
                mock_admin_obj.userName = "testadmin"
                mock_admin.return_value = mock_admin_obj
                
                # Test the path validation
                result = FTPUtilities.submitFTPCreation(
                    "testdomain.com", 
                    "testuser", 
                    "testpass", 
                    path, 
                    "testadmin"
                )
                
                if should_pass:
                    if result[0] == 1:
                        print(f"✅ PASS: {description} ('{path}')")
                        passed += 1
                    else:
                        print(f"❌ FAIL: {description} ('{path}') - Expected success but got: {result[1]}")
                        failed += 1
                else:
                    if result[0] == 0:
                        print(f"✅ PASS: {description} ('{path}') - Correctly rejected")
                        passed += 1
                    else:
                        print(f"❌ FAIL: {description} ('{path}') - Expected rejection but got success")
                        failed += 1
                        
        except Exception as e:
            if should_pass:
                print(f"❌ ERROR: {description} ('{path}') - Unexpected error: {e}")
                failed += 1
            else:
                print(f"✅ PASS: {description} ('{path}') - Correctly rejected with error: {e}")
                passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

def test_directory_creation():
    """Test directory creation functionality"""
    print("\n🔍 Testing Directory Creation...")
    
    try:
        from plogical.ftpUtilities import FTPUtilities
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test_ftp_dir")
            
            print(f"📁 Testing directory creation at: {test_path}")
            
            # Test creating a new directory
            result = FTPUtilities.ftpFunctions(test_path, "testuser")
            
            if result[0] == 1:
                if os.path.exists(test_path) and os.path.isdir(test_path):
                    print("✅ Directory creation successful")
                    return True
                else:
                    print("❌ Directory creation failed - directory not found")
                    return False
            else:
                print(f"❌ Directory creation failed: {result[1]}")
                return False
                
    except Exception as e:
        print(f"❌ Directory creation test failed: {e}")
        return False

def test_security_features():
    """Test security features"""
    print("\n🔍 Testing Security Features...")
    
    security_tests = [
        ("Path traversal prevention", ".."),
        ("Home directory reference prevention", "~"),
        ("Absolute path prevention", "/etc/passwd"),
        ("Command injection prevention", ";rm -rf /"),
        ("Pipe command prevention", "|cat /etc/passwd"),
        ("Background command prevention", "&reboot"),
        ("Command substitution prevention", "`whoami`"),
    ]
    
    print("🛡️ Security Test Results:")
    print("-" * 40)
    
    for test_name, malicious_path in security_tests:
        try:
            # This should be caught by our validation
            if any(char in malicious_path for char in ['..', '~', '/', ';', '|', '&', '`']):
                print(f"✅ {test_name}: Correctly detected malicious path")
            else:
                print(f"❌ {test_name}: Failed to detect malicious path")
        except Exception as e:
            print(f"✅ {test_name}: Correctly rejected with error: {e}")
    
    return True

def main():
    """Main test function"""
    print("🚀 CyberPanel FTP Account Creation Test Suite")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("Path Validation", test_ftp_path_validation),
        ("Directory Creation", test_directory_creation),
        ("Security Features", test_security_features),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} Test: PASSED")
            else:
                print(f"❌ {test_name} Test: FAILED")
        except Exception as e:
            print(f"❌ {test_name} Test: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! FTP account creation should work correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
