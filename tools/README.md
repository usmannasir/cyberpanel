# CyberPanel Installation Tools

This directory contains utility scripts for testing and validating CyberPanel installation fixes.

## Files

### `test_fixes.sh`
A comprehensive test script that validates all the installation fixes applied to CyberPanel.

**Purpose:**
- Validates that all critical installation issues have been resolved
- Tests requirements file fallback logic
- Verifies MariaDB version updates
- Checks GPG fix implementations
- Validates branch/commit existence verification

**Usage:**
```bash
# Run from the cyberpanel root directory
cd /path/to/cyberpanel
bash tools/test_fixes.sh
```

**Requirements:**
- Linux/Unix environment with bash
- curl command available
- Internet connectivity for API calls

**What it tests:**
1. Requirements file availability (404/200 responses)
2. Commit validation via GitHub API
3. Available branches listing
4. MariaDB repository accessibility
5. File modification verification
6. GPG fix implementation
7. Requirements fallback logic
8. Branch/commit validation

**Note:** This script is primarily for development and maintenance purposes. It's not required for normal CyberPanel installation.

## When to Use

- After modifying installation scripts
- When troubleshooting installation issues
- During development of new fixes
- For quality assurance validation

## Output

The script provides clear ✅/❌ indicators for each test, making it easy to identify any issues with the installation fixes.
