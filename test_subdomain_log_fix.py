#!/usr/local/CyberCP/bin/python
"""
Test script for subdomain log fix
This script tests the subdomain log fix functionality
"""

import os
import sys
import django

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from websiteFunctions.models import ChildDomains
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


def test_subdomain_log_configuration():
    """Test if subdomain log configurations are correct"""
    print("Testing subdomain log configurations...")
    
    issues_found = 0
    child_domains = ChildDomains.objects.all()
    
    if not child_domains:
        print("No child domains found.")
        return True
    
    for child_domain in child_domains:
        domain_name = child_domain.domain
        master_domain = child_domain.master.domain
        
        vhost_conf_path = f"/usr/local/lsws/conf/vhosts/{domain_name}/vhost.conf"
        
        if not os.path.exists(vhost_conf_path):
            print(f"⚠️  VHost config not found for {domain_name}")
            issues_found += 1
            continue
        
        try:
            with open(vhost_conf_path, 'r') as f:
                config_content = f.read()
            
            # Check for incorrect log paths
            if f'{master_domain}.error_log' in config_content:
                print(f"❌ {domain_name}: Using master domain error log")
                issues_found += 1
            else:
                print(f"✅ {domain_name}: Error log configuration OK")
            
            if f'{master_domain}.access_log' in config_content:
                print(f"❌ {domain_name}: Using master domain access log")
                issues_found += 1
            else:
                print(f"✅ {domain_name}: Access log configuration OK")
                
        except Exception as e:
            print(f"❌ {domain_name}: Error reading config - {str(e)}")
            issues_found += 1
    
    if issues_found == 0:
        print("\n🎉 All subdomain log configurations are correct!")
        return True
    else:
        print(f"\n⚠️  Found {issues_found} issues with subdomain log configurations")
        return False


def test_management_command():
    """Test the management command"""
    print("\nTesting management command...")
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Test dry run
        out = StringIO()
        call_command('fix_subdomain_logs', '--dry-run', stdout=out)
        print("✅ Management command dry run works")
        
        return True
    except Exception as e:
        print(f"❌ Management command test failed: {str(e)}")
        return False


def main():
    """Main test function"""
    print("=" * 60)
    print("SUBDOMAIN LOG FIX TEST")
    print("=" * 60)
    
    # Test 1: Check current configurations
    config_test = test_subdomain_log_configuration()
    
    # Test 2: Test management command
    cmd_test = test_management_command()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if config_test and cmd_test:
        print("🎉 All tests passed!")
        print("\nTo fix any issues found:")
        print("1. Via Web Interface: Websites > Fix Subdomain Logs")
        print("2. Via CLI: python manage.py fix_subdomain_logs --all")
        print("3. For specific domain: python manage.py fix_subdomain_logs --domain example.com")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
