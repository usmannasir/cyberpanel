#!/bin/bash

###############################################################################
# CyberPanel rDNS System Fix for v2.4.4
# This script applies fixes to the rDNS validation system
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# CyberPanel paths
CYBERCP_PATH="/usr/local/CyberCP"
MAIL_UTILITIES="${CYBERCP_PATH}/plogical/mailUtilities.py"
VIRTUAL_HOST_UTILITIES="${CYBERCP_PATH}/plogical/virtualHostUtilities.py"

# Backup directory
BACKUP_DIR="${CYBERCP_PATH}/backup_rdns_fix_$(date +%Y%m%d_%H%M%S)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CyberPanel rDNS System Fix v1.0${NC}"
echo -e "${GREEN}For CyberPanel 2.4.4${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Check if CyberPanel is installed
if [ ! -d "$CYBERCP_PATH" ]; then
    echo -e "${RED}CyberPanel not found at ${CYBERCP_PATH}${NC}"
    exit 1
fi

# Check if files exist
if [ ! -f "$MAIL_UTILITIES" ]; then
    echo -e "${RED}File not found: ${MAIL_UTILITIES}${NC}"
    exit 1
fi

if [ ! -f "$VIRTUAL_HOST_UTILITIES" ]; then
    echo -e "${RED}File not found: ${VIRTUAL_HOST_UTILITIES}${NC}"
    exit 1
fi

# Create backup directory
echo -e "${YELLOW}Creating backup...${NC}"
mkdir -p "$BACKUP_DIR"
cp "$MAIL_UTILITIES" "${BACKUP_DIR}/mailUtilities.py"
cp "$VIRTUAL_HOST_UTILITIES" "${BACKUP_DIR}/virtualHostUtilities.py"
echo -e "${GREEN}Backup created at: ${BACKUP_DIR}${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if patch files exist
PATCH_MAIL="${SCRIPT_DIR}/mailUtilities.py.patch"
PATCH_VHOST="${SCRIPT_DIR}/virtualHostUtilities.py.patch"

# Function to apply Python code fix
apply_mail_utilities_fix() {
    echo -e "${YELLOW}Applying fix to mailUtilities.py...${NC}"
    
    # Create temporary Python script to apply the fix
    python3 << 'PYTHON_SCRIPT'
import re
import sys

file_path = sys.argv[1]

try:
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace str(msg) with str(e) in exception handler
    content = re.sub(
        r"logging\.CyberCPLogFileWriter\.writeToFile\(f'Error in fetch rDNS \{str\(msg\)\}'\)",
        "logging.CyberCPLogFileWriter.writeToFile(f'Error in fetch rDNS {str(e)}')",
        content
    )
    
    # Fix 2: Check if reverse_dns_lookup function needs comprehensive fix
    # This is a more complex fix that requires the full function replacement
    # We'll use a marker-based approach
    
    # Check if the old buggy version exists
    if "str(msg)" in content and "reverse_dns_lookup" in content:
        print("Found buggy version, applying comprehensive fix...")
        
        # Read the fixed version from a separate file or embed it
        # For now, we'll do a targeted fix
        pass
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fix applied successfully")
    
except Exception as e:
    print(f"Error applying fix: {e}")
    sys.exit(1)
PYTHON_SCRIPT
    "$MAIL_UTILITIES"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}mailUtilities.py fix applied${NC}"
    else
        echo -e "${RED}Failed to apply fix to mailUtilities.py${NC}"
        return 1
    fi
}

# Function to check if fix is already applied
check_if_fixed() {
    if grep -q "str(e)" "$MAIL_UTILITIES" && ! grep -q "str(msg)" "$MAIL_UTILITIES"; then
        return 0  # Fixed
    else
        return 1  # Not fixed
    fi
}

# Main installation
echo -e "${YELLOW}Checking current state...${NC}"

if check_if_fixed; then
    echo -e "${GREEN}Fix appears to already be applied${NC}"
    read -p "Do you want to reapply? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Aborted${NC}"
        exit 0
    fi
fi

# Apply fixes
echo ""
echo -e "${YELLOW}Applying fixes...${NC}"

# Fix 1: mailUtilities.py - NameError bug
if grep -q "str(msg)" "$MAIL_UTILITIES"; then
    sed -i 's/str(msg)/str(e)/g' "$MAIL_UTILITIES"
    echo -e "${GREEN}✓ Fixed NameError bug in mailUtilities.py${NC}"
else
    echo -e "${YELLOW}⚠ NameError fix not needed (may already be fixed)${NC}"
fi

# Note: The comprehensive fixes require full function replacement
# which is better done manually or with a proper patch file
echo ""
echo -e "${YELLOW}Note: This script applies the critical NameError fix.${NC}"
echo -e "${YELLOW}For comprehensive fixes (error handling improvements),${NC}"
echo -e "${YELLOW}please refer to the README.md for manual installation steps.${NC}"
echo ""

# Restart CyberPanel
echo -e "${YELLOW}Restarting CyberPanel...${NC}"
if systemctl is-active --quiet lscpd; then
    systemctl restart lscpd
    echo -e "${GREEN}CyberPanel restarted${NC}"
else
    echo -e "${YELLOW}CyberPanel service not running, skipping restart${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Fix applied successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Backup location: ${BACKUP_DIR}${NC}"
echo -e "${YELLOW}Please test the rDNS functionality and review logs if needed.${NC}"
echo ""

