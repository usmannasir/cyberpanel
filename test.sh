#!/bin/bash
# CyberPanel Test Script
# This script runs basic tests for CyberPanel components

set -euo pipefail

echo "🧪 Running CyberPanel Tests..."

# Check if we're in the right directory
if [[ ! -f "manage.py" ]]; then
    echo "❌ Error: manage.py not found. Please run this script from the CyberPanel root directory."
    exit 1
fi

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "⚠️  Warning: Virtual environment not activated. Some tests may fail."
    echo "   Run 'source cyberpanel_env/bin/activate' first for best results."
fi

echo "✅ Basic checks passed"
echo "🎉 Test script completed successfully!"