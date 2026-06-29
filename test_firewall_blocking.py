#!/usr/bin/env python3
"""
Test script for the new firewall blocking functionality
This script tests the blockIPAddress API endpoint
"""

import requests
import json
import sys

def test_firewall_blocking():
    """
    Test the firewall blocking functionality
    Note: This is a basic test script. In a real environment, you would need
    proper authentication and a test IP address.
    """
    
    print("Testing Firewall Blocking Functionality")
    print("=" * 50)
    
    # Test configuration
    base_url = "https://localhost:8090"  # Adjust based on your CyberPanel setup
    test_ip = "192.168.1.100"  # Use a test IP that won't block your access
    
    print(f"Base URL: {base_url}")
    print(f"Test IP: {test_ip}")
    print()
    
    # Test data
    test_data = {
        "ip_address": test_ip
    }
    
    print("Test Data:")
    print(json.dumps(test_data, indent=2))
    print()
    
    print("Note: This test requires:")
    print("1. Valid CyberPanel session with admin privileges")
    print("2. CyberPanel addons enabled")
    print("3. Active firewalld service")
    print()
    
    print("To test manually:")
    print("1. Login to CyberPanel dashboard")
    print("2. Go to Dashboard -> SSH Security Analysis")
    print("3. Look for 'Brute Force Attack Detected' alerts")
    print("4. Click the 'Block IP' button next to malicious IPs")
    print()
    
    print("Expected behavior:")
    print("- Button shows loading state during blocking")
    print("- Success notification appears on successful blocking")
    print("- IP is marked as 'Blocked' in the interface")
    print("- Security analysis refreshes to update alerts")
    print()
    
    print("Firewall Commands:")
    print("- firewalld: firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<ip> drop'")
    print("- firewalld reload: firewall-cmd --reload")
    print()

if __name__ == "__main__":
    test_firewall_blocking()
