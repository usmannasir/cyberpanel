# Branch Prefix Fix - v2.5.5-dev Issue Resolved

## Problem Identified

The user discovered that when trying to install `2.5.5-dev`, the installer was incorrectly trying to access:
```
https://raw.githubusercontent.com/usmannasir/cyberpanel/2.5.5-dev/requirments.txt
```

But the actual branch exists as `v2.5.5-dev` (with the `v` prefix):
```
https://github.com/usmannasir/cyberpanel/blob/v2.5.5-dev/requirments.txt
```

## Root Cause

The `Branch_Check()` function in `cyberpanel.sh` was not properly handling development version branch names. When a user entered `2.5.5-dev`, the code was setting `Branch_Name="2.5.5-dev"` instead of adding the required `v` prefix to make it `v2.5.5-dev`.

## Solution Applied

### 1. Enhanced Branch Name Logic
Updated the `Branch_Check()` function to automatically add the `v` prefix for development branches:

```bash
# Handle both stable and development versions
if [[ "$1" =~ -dev$ ]]; then
  # Add 'v' prefix for development branches if not already present
  if [[ "$1" =~ ^v.*-dev$ ]]; then
    Branch_Name="${1//[[:space:]]/}"
  else
    Branch_Name="v${1//[[:space:]]/}"
  fi
  echo -e "\nSet branch name to $Branch_Name (development version)..."
```

### 2. Updated User Guidance
Modified the version prompt to clarify that the `v` prefix will be automatically added:

```
2.5.5-dev (development version - will auto-add 'v' prefix)
v2.3.5-dev (development version with 'v' prefix)
```

## Verification

✅ **Confirmed**: The `v2.5.5-dev` branch exists and is accessible
✅ **Confirmed**: The requirements file is available at the correct URL
✅ **Confirmed**: The fix handles both formats (`2.5.5-dev` and `v2.5.5-dev`)

## Impact

- Users can now enter `2.5.5-dev` and it will automatically work as `v2.5.5-dev`
- Existing users who were already using `v2.5.5-dev` format continue to work
- No breaking changes to existing functionality
- Clearer user guidance about branch naming

## Files Modified

- `cyberpanel/cyberpanel.sh` - Enhanced `Branch_Check()` function
- `cyberpanel/tools/test_fixes.sh` - Updated test cases
- `cyberpanel/BRANCH_PREFIX_FIX.md` - This documentation

## Test Results

```bash
# Test 1: Non-existent branch (should fail)
curl -I https://raw.githubusercontent.com/usmannasir/cyberpanel/2.5.5-dev/requirments.txt
# Result: 404 Not Found ✅

# Test 2: Correct branch name (should work)
curl -I https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.5.5-dev/requirments.txt  
# Result: 200 OK ✅
```

## Installation Examples

### Now Works:
```bash
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
# When prompted, enter: 2.5.5-dev
# Will automatically use: v2.5.5-dev
```

### Still Works:
```bash
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
# When prompted, enter: v2.5.5-dev
# Will use: v2.5.5-dev (no change)
```

---

**Fix Applied**: September 24, 2025  
**Issue**: Branch prefix missing for development versions  
**Status**: ✅ Resolved
