#!/bin/bash
# Setup script for OLS Feature Test Suite
# Creates the test data directory structure needed by ols_feature_tests.sh
# Run this once before running the test suite on a new server.

TEST_DIR="/tmp/apacheconf-test"
mkdir -p "$TEST_DIR/included"
mkdir -p "$TEST_DIR/docroot-main/subdir"
mkdir -p "$TEST_DIR/docroot-main/error_docs"
mkdir -p "$TEST_DIR/docroot-second"
mkdir -p "$TEST_DIR/docroot-alias"
mkdir -p "$TEST_DIR/cgi-bin"

# Included config files (for Include/IncludeOptional tests)
cat > "$TEST_DIR/included/tuning.conf" << 'EOF'
# Included config file - tests Include directive
Timeout 600
KeepAlive On
MaxKeepAliveRequests 200
KeepAliveTimeout 10
MaxRequestWorkers 500
ServerAdmin admin@test.example.com
EOF

cat > "$TEST_DIR/included/global-scripts.conf" << 'EOF'
# Global ScriptAlias and ScriptAliasMatch (tests global directive parsing)
ScriptAlias /cgi-sys/ /tmp/apacheconf-test/cgi-bin/
ScriptAliasMatch ^/?testredirect/?$ /tmp/apacheconf-test/cgi-bin/redirect.cgi
EOF

# Document roots
echo '<html><body>Main VHost Index</body></html>' > "$TEST_DIR/docroot-main/index.html"
echo '<html><body>Second VHost Index</body></html>' > "$TEST_DIR/docroot-second/index.html"
echo '<html><body>Aliased Content</body></html>' > "$TEST_DIR/docroot-alias/aliased.html"

echo "Test data created in $TEST_DIR"
echo "Now run: bash ols_feature_tests.sh"
