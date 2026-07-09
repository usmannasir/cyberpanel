#!/bin/bash
# Test script to verify API key validation fix

# Configuration - adjust these values
# For remote testing, replace with your CyberPanel server URL
SERVER="${CYBERPANEL_SERVER:-http://localhost:8001}"
API_KEY="${CYBERPANEL_API_KEY:-cp_GrHf3ysP0SKhrEiazmqt3kRJA5KwOFQW8VJKcDQ8B5Bg}"  # Your actual API key
SCAN_ID="${CYBERPANEL_SCAN_ID:-550e8400-e29b-41d4-a716-446655440000}"  # A valid scan ID from your system

echo "Using server: $SERVER"
echo "Using API key: ${API_KEY:0:20}..."
echo "Using scan ID: $SCAN_ID"
echo ""

echo "=========================================="
echo "Testing CyberPanel API Key Validation Fix"
echo "=========================================="
echo ""

# Test 1: List API keys in the system
echo "1. Listing API keys in system..."
echo "---------------------------------"
curl -s "$SERVER/api/ai-scanner/list-api-keys/" | python3 -m json.tool
echo ""

# Test 2: Test authentication with X-API-Key header
echo "2. Testing X-API-Key authentication..."
echo "---------------------------------------"
curl -s -X POST "$SERVER/api/ai-scanner/test-auth/" \
     -H "X-API-Key: $API_KEY" \
     -H "X-Scan-ID: $SCAN_ID" \
     -H "Content-Type: application/json" \
     -d "{\"scan_id\": \"$SCAN_ID\"}" | python3 -m json.tool
echo ""

# Test 3: Test actual file operation with X-API-Key
echo "3. Testing file operation with X-API-Key..."
echo "--------------------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVER/api/scanner/get-file?file_path=wp-content/test.php" \
     -H "X-API-Key: $API_KEY" \
     -H "X-Scan-ID: $SCAN_ID")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

echo "HTTP Status: $HTTP_CODE"
echo "Response body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

# Test 4: Test with Bearer token (backward compatibility)
echo "4. Testing Bearer token (backward compatibility)..."
echo "----------------------------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVER/api/scanner/get-file?file_path=wp-content/test.php" \
     -H "Authorization: Bearer $API_KEY" \
     -H "X-Scan-ID: $SCAN_ID")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

echo "HTTP Status: $HTTP_CODE"
echo "Response body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

echo "=========================================="
echo "Test complete!"
echo ""
echo "Expected results:"
echo "- Test 1: Should show API keys in system"
echo "- Test 2: Should show validation success with detailed steps"
echo "- Test 3: Should return 200 or 404 (not 401)"
echo "- Test 4: Should also work with Bearer token"
echo "=========================================="