#!/bin/bash

# Test script for CyberPanel Modular Installer
# This script tests the installer without actually installing

echo "🧪 Testing CyberPanel Modular Installer..."

# Test 1: Check if all modules exist
echo "📋 Testing module structure..."

modules=(
    "modules/os/detect.sh"
    "modules/deps/manager.sh"
    "modules/deps/rhel_deps.sh"
    "modules/deps/debian_deps.sh"
    "modules/install/cyberpanel_installer.sh"
    "modules/fixes/cyberpanel_fixes.sh"
    "modules/utils/ui.sh"
    "modules/utils/menu.sh"
)

for module in "${modules[@]}"; do
    if [ -f "$module" ]; then
        echo "✅ $module exists"
    else
        echo "❌ $module missing"
    fi
done

# Test 2: Check if cyberpanel.sh is executable
echo ""
echo "📋 Testing main installer..."

if [ -f "cyberpanel.sh" ]; then
    echo "✅ cyberpanel.sh exists"
    if [ -x "cyberpanel.sh" ]; then
        echo "✅ cyberpanel.sh is executable"
    else
        echo "❌ cyberpanel.sh is not executable"
    fi
else
    echo "❌ cyberpanel.sh missing"
fi

# Test 3: Test help function
echo ""
echo "📋 Testing help function..."
if ./cyberpanel.sh --help > /dev/null 2>&1; then
    echo "✅ Help function works"
else
    echo "❌ Help function failed"
fi

# Test 4: Test module loading (dry run)
echo ""
echo "📋 Testing module loading..."

# Create a test script that loads modules
cat > test_modules.sh << 'EOF'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="$SCRIPT_DIR/modules"

# Test OS detection module
if [ -f "$MODULES_DIR/os/detect.sh" ]; then
    source "$MODULES_DIR/os/detect.sh"
    echo "✅ OS detection module loaded"
else
    echo "❌ OS detection module not found"
    exit 1
fi

# Test UI module
if [ -f "$MODULES_DIR/utils/ui.sh" ]; then
    source "$MODULES_DIR/utils/ui.sh"
    echo "✅ UI module loaded"
else
    echo "❌ UI module not found"
    exit 1
fi

echo "✅ All modules loaded successfully"
EOF

chmod +x test_modules.sh

if ./test_modules.sh; then
    echo "✅ Module loading test passed"
else
    echo "❌ Module loading test failed"
fi

# Cleanup
rm -f test_modules.sh

echo ""
echo "🎉 Test completed!"
echo ""
echo "To use the installer:"
echo "  bash cyberpanel.sh                    # Interactive mode"
echo "  bash cyberpanel.sh --debug            # Debug mode"
echo "  bash cyberpanel.sh --auto             # Auto mode"
echo "  bash cyberpanel.sh -b v2.5.5-dev      # Specific version"
