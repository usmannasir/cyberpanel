#!/usr/local/CyberCP/bin/python
"""
Test script for SSL integration
This script tests the SSL reconciliation functionality
"""

import os
import sys
import django

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from plogical.sslReconcile import SSLReconcile
from plogical.sslUtilities import sslUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


def test_ssl_reconcile_module():
    """Test the SSL reconciliation module"""
    print("Testing SSL Reconciliation Module...")
    
    try:
        # Test 1: Check if module can be imported
        print("✓ SSLReconcile module imported successfully")
        
        # Test 2: Test utility functions
        print("Testing utility functions...")
        
        # Test trim function
        test_text = "  test text  "
        trimmed = SSLReconcile.trim(test_text)
        assert trimmed == "test text", f"Trim failed: '{trimmed}'"
        print("✓ trim() function works correctly")
        
        # Test 3: Test certificate fingerprint function
        print("Testing certificate functions...")
        
        # Test with non-existent file
        fp = SSLReconcile.sha256fp("/nonexistent/file.pem")
        assert fp == "", f"Expected empty string for non-existent file, got: '{fp}'"
        print("✓ sha256fp() handles non-existent files correctly")
        
        # Test issuer CN function
        issuer = SSLReconcile.issuer_cn("/nonexistent/file.pem")
        assert issuer == "", f"Expected empty string for non-existent file, got: '{issuer}'"
        print("✓ issuer_cn() handles non-existent files correctly")
        
        print("✓ All utility functions working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ SSL reconciliation module test failed: {str(e)}")
        return False


def test_ssl_utilities_integration():
    """Test the enhanced SSL utilities"""
    print("\nTesting Enhanced SSL Utilities...")
    
    try:
        # Test 1: Check if new methods exist
        assert hasattr(sslUtilities, 'reconcile_ssl_all'), "reconcile_ssl_all method not found"
        assert hasattr(sslUtilities, 'reconcile_ssl_domain'), "reconcile_ssl_domain method not found"
        assert hasattr(sslUtilities, 'fix_acme_challenge_context'), "fix_acme_challenge_context method not found"
        print("✓ All new SSL utility methods found")
        
        # Test 2: Test method signatures
        import inspect
        
        # Check reconcile_ssl_all signature
        sig = inspect.signature(sslUtilities.reconcile_ssl_all)
        assert len(sig.parameters) == 0, f"reconcile_ssl_all should have no parameters, got: {sig.parameters}"
        print("✓ reconcile_ssl_all signature correct")
        
        # Check reconcile_ssl_domain signature
        sig = inspect.signature(sslUtilities.reconcile_ssl_domain)
        assert 'domain' in sig.parameters, f"reconcile_ssl_domain should have 'domain' parameter, got: {sig.parameters}"
        print("✓ reconcile_ssl_domain signature correct")
        
        # Check fix_acme_challenge_context signature
        sig = inspect.signature(sslUtilities.fix_acme_challenge_context)
        assert 'virtualHostName' in sig.parameters, f"fix_acme_challenge_context should have 'virtualHostName' parameter, got: {sig.parameters}"
        print("✓ fix_acme_challenge_context signature correct")
        
        print("✓ All SSL utility method signatures correct")
        
        return True
        
    except Exception as e:
        print(f"✗ SSL utilities integration test failed: {str(e)}")
        return False


def test_vhost_configuration_fixes():
    """Test that vhost configuration fixes are applied"""
    print("\nTesting VHost Configuration Fixes...")
    
    try:
        from plogical.vhostConfs import vhostConfs
        
        # Test 1: Check that ACME challenge contexts use $VH_ROOT
        ols_master_conf = vhostConfs.olsMasterConf
        assert '$VH_ROOT/public_html/.well-known/acme-challenge' in ols_master_conf, "ACME challenge context not fixed in olsMasterConf"
        print("✓ olsMasterConf ACME challenge context fixed")
        
        # Test 2: Check child configuration
        ols_child_conf = vhostConfs.olsChildConf
        assert '$VH_ROOT/public_html/.well-known/acme-challenge' in ols_child_conf, "ACME challenge context not fixed in olsChildConf"
        print("✓ olsChildConf ACME challenge context fixed")
        
        # Test 3: Check Apache configurations
        apache_conf = vhostConfs.apacheConf
        assert '/home/{virtualHostName}/public_html/.well-known/acme-challenge' in apache_conf, "Apache ACME challenge alias not fixed"
        print("✓ Apache ACME challenge alias fixed")
        
        print("✓ All vhost configuration fixes applied correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ VHost configuration fixes test failed: {str(e)}")
        return False


def test_management_command():
    """Test the Django management command"""
    print("\nTesting Django Management Command...")
    
    try:
        import subprocess
        
        # Test 1: Check if management command exists
        result = subprocess.run([
            'python', 'manage.py', 'ssl_reconcile', '--help'
        ], capture_output=True, text=True, cwd='/usr/local/CyberCP')
        
        if result.returncode == 0:
            print("✓ SSL reconcile management command exists and responds to --help")
        else:
            print(f"✗ SSL reconcile management command failed: {result.stderr}")
            return False
        
        # Test 2: Check command options
        help_output = result.stdout
        assert '--all' in help_output, "--all option not found in help"
        assert '--domain' in help_output, "--domain option not found in help"
        assert '--fix-acme' in help_output, "--fix-acme option not found in help"
        print("✓ All management command options present")
        
        print("✓ Django management command working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Django management command test failed: {str(e)}")
        return False


def test_cron_integration():
    """Test that cron integration is properly configured"""
    print("\nTesting Cron Integration...")
    
    try:
        # Check if cron file exists and contains SSL reconciliation
        cron_paths = [
            '/var/spool/cron/crontabs/root',
            '/etc/crontab'
        ]
        
        ssl_reconcile_found = False
        
        for cron_path in cron_paths:
            if os.path.exists(cron_path):
                with open(cron_path, 'r') as f:
                    content = f.read()
                    if 'ssl_reconcile --all' in content:
                        ssl_reconcile_found = True
                        print(f"✓ SSL reconciliation cron job found in {cron_path}")
                        break
        
        if not ssl_reconcile_found:
            print("✗ SSL reconciliation cron job not found in any cron file")
            return False
        
        print("✓ Cron integration working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Cron integration test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("SSL Integration Test Suite")
    print("=" * 60)
    
    tests = [
        test_ssl_reconcile_module,
        test_ssl_utilities_integration,
        test_vhost_configuration_fixes,
        test_management_command,
        test_cron_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! SSL integration is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
