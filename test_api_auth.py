#!/usr/bin/env python3
"""
Test script to verify both Bearer token and X-API-Key authentication work
for CyberPanel AI Scanner file operations.
"""

import requests
import json
import sys

# Test configuration
BASE_URL = "http://localhost:8001"  # Adjust if needed
SCAN_ID = "test-scan-123"
FILE_PATH = "wp-content/plugins/test.php"

def test_bearer_auth(token):
    """Test with Bearer token authentication"""
    print("Testing Bearer token authentication...")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Scan-ID": SCAN_ID,
        "Content-Type": "application/json"
    }

    # Test get-file endpoint
    url = f"{BASE_URL}/api/scanner/get-file"
    params = {"file_path": FILE_PATH}

    response = requests.get(url, params=params, headers=headers)
    print(f"Bearer auth response: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.text}")
    return response.status_code == 200 or response.status_code == 404  # 404 is ok if file doesn't exist


def test_api_key_auth(api_key):
    """Test with X-API-Key authentication"""
    print("\nTesting X-API-Key authentication...")

    headers = {
        "X-API-Key": api_key,
        "X-Scan-ID": SCAN_ID,
        "Content-Type": "application/json"
    }

    # Test get-file endpoint
    url = f"{BASE_URL}/api/scanner/get-file"
    params = {"file_path": FILE_PATH}

    response = requests.get(url, params=params, headers=headers)
    print(f"X-API-Key auth response: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.text}")
    return response.status_code == 200 or response.status_code == 404  # 404 is ok if file doesn't exist


def test_mixed_endpoints():
    """Test different endpoints with both authentication methods"""
    print("\n" + "="*50)
    print("Testing multiple endpoints with both auth methods")
    print("="*50)

    # You would need real tokens for this to work
    test_token = "cp_test_token_12345"
    test_api_key = "cp_test_api_key_67890"

    endpoints = [
        ("GET", "/api/ai-scanner/files/list", {"path": "wp-content"}),
        ("GET", "/api/ai-scanner/files/content", {"path": FILE_PATH}),
        ("GET", "/api/scanner/get-file", {"file_path": FILE_PATH}),
    ]

    for method, endpoint, params in endpoints:
        print(f"\nTesting {method} {endpoint}")

        # Test with Bearer token
        headers_bearer = {
            "Authorization": f"Bearer {test_token}",
            "X-Scan-ID": SCAN_ID
        }

        # Test with X-API-Key
        headers_api_key = {
            "X-API-Key": test_api_key,
            "X-Scan-ID": SCAN_ID
        }

        url = f"{BASE_URL}{endpoint}"

        # Make requests (will fail without valid tokens, but shows the headers work)
        if method == "GET":
            response_bearer = requests.get(url, params=params, headers=headers_bearer)
            response_api_key = requests.get(url, params=params, headers=headers_api_key)

        print(f"  Bearer auth: {response_bearer.status_code}")
        print(f"  X-API-Key auth: {response_api_key.status_code}")


def main():
    """Main test function"""
    print("CyberPanel AI Scanner Authentication Test")
    print("="*50)

    if len(sys.argv) > 1:
        # If token provided as argument, use it
        token = sys.argv[1]

        # Test both authentication methods with the same token
        # (assumes token is valid for both methods)
        bearer_success = test_bearer_auth(token)
        api_key_success = test_api_key_auth(token)

        print("\n" + "="*50)
        print("Test Results:")
        print(f"  Bearer authentication: {'✓ PASS' if bearer_success else '✗ FAIL'}")
        print(f"  X-API-Key authentication: {'✓ PASS' if api_key_success else '✗ FAIL'}")
        print("="*50)
    else:
        # Run mock tests to show the endpoints accept both header formats
        test_mixed_endpoints()

        print("\n" + "="*50)
        print("Note: To run real tests, provide a valid token:")
        print(f"  python {sys.argv[0]} cp_your_token_here")
        print("="*50)


if __name__ == "__main__":
    main()