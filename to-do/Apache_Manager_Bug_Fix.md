# Apache Manager Bug Fix - "must be str, not NoneType" Error

## Issue Description

**Bug Report**: [GitHub Issue #1257](https://github.com/usmannasir/cyberpanel/issues/1257) - "[BUG] apache manager after making subdomain"

**Problem**: When trying to switch a subdomain to Apache using the Apache Manager, users encountered the error:
- **Error Message**: "Operation Failed! must be str, not NoneType"
- **Scenario**: Subdomain created without Apache reverse proxy initially, then trying to switch to Apache later
- **Workaround**: Only worked if subdomain was created "With" Apache reverse proxy from the start

## Root Cause Analysis

The error occurred in the `switchServer` function in `plogical/virtualHostUtilities.py` at lines 1679-1681 and 1674-1676.

**Specific Issues:**
1. **Child Domains**: `website.master.adminEmail` and `website.master.externalApp` could be `None` (null) in the database
2. **Main Domains**: `website.adminEmail` and `website.externalApp` could be `None` (null) in the database
3. **String Operations**: The code tried to use these `None` values in string operations, causing the "must be str, not NoneType" error

## Technical Details

### Database Schema
```python
class Websites(models.Model):
    adminEmail = models.CharField(max_length=255)  # Can be None
    externalApp = models.CharField(max_length=30, default=None)  # Can be None

class ChildDomains(models.Model):
    master = models.ForeignKey(Websites, on_delete=models.CASCADE)  # References Websites
```

### Problematic Code (Before Fix)
```python
# Lines 1674-1676 - perHostVirtualConfOLS calls
if child:
    ApacheVhost.perHostVirtualConfOLS(completePathToConfigFile, website.master.adminEmail)  # Could be None
else:
    ApacheVhost.perHostVirtualConfOLS(completePathToConfigFile, website.adminEmail)  # Could be None

# Lines 1679-1681 - setupApacheVhostChild calls
if child:
    ApacheVhost.setupApacheVhostChild(website.master.adminEmail, website.master.externalApp,  # Could be None
                                      website.master.externalApp,  # Could be None
                                      phpVersion, virtualHostName, website.path)
```

## Solution Implemented

### 1. Added Null Value Handling
- **Admin Email**: Falls back to `website.master.admin.email` or `website.admin.email` if `adminEmail` is `None`
- **External App**: Generates a new external app name if `externalApp` is `None`

### 2. Fixed Code (After Fix)
```python
# Lines 1673-1680 - perHostVirtualConfOLS calls with null handling
if child:
    # Handle None values for child domains
    admin_email = website.master.adminEmail if website.master.adminEmail else website.master.admin.email
    ApacheVhost.perHostVirtualConfOLS(completePathToConfigFile, admin_email)
else:
    # Handle None values for main domains
    admin_email = website.adminEmail if website.adminEmail else website.admin.email
    ApacheVhost.perHostVirtualConfOLS(completePathToConfigFile, admin_email)

# Lines 1682-1692 - setupApacheVhostChild calls with null handling
if child:
    # Handle None values for child domains
    admin_email = website.master.adminEmail if website.master.adminEmail else website.master.admin.email
    external_app = website.master.externalApp if website.master.externalApp else "".join(re.findall("[a-zA-Z]+", virtualHostName))[:5] + str(randint(1000, 9999))
    
    ApacheVhost.setupApacheVhostChild(admin_email, external_app,
                                      external_app,
                                      phpVersion, virtualHostName, website.path)
else:
    # Handle None values for main domains
    admin_email = website.adminEmail if website.adminEmail else website.admin.email
    external_app = website.externalApp if website.externalApp else "".join(re.findall("[a-zA-Z]+", virtualHostName))[:5] + str(randint(1000, 9999))
    
    ApacheVhost.setupApacheVhost(admin_email, external_app, external_app,
                                 phpVersion, virtualHostName)
```

### 3. Added Required Import
```python
import re  # Added for external app name generation
```

## Fallback Logic

### Admin Email Fallback
1. **Primary**: Use `website.adminEmail` or `website.master.adminEmail`
2. **Fallback**: Use `website.admin.email` or `website.master.admin.email`

### External App Fallback
1. **Primary**: Use `website.externalApp` or `website.master.externalApp`
2. **Fallback**: Generate new external app name using domain name + random number

## Testing Scenarios

### Test Case 1: Child Domain with Null Values
- **Setup**: Create subdomain without Apache, ensure `adminEmail` and `externalApp` are `None`
- **Action**: Try to switch to Apache using Apache Manager
- **Expected**: Should work without "must be str, not NoneType" error

### Test Case 2: Main Domain with Null Values
- **Setup**: Create main domain without Apache, ensure `adminEmail` and `externalApp` are `None`
- **Action**: Try to switch to Apache using Apache Manager
- **Expected**: Should work without "must be str, not NoneType" error

### Test Case 3: Normal Operation
- **Setup**: Create domain with Apache from start
- **Action**: Switch between Apache and OpenLiteSpeed
- **Expected**: Should continue working as before

## Files Modified

1. **`cyberpanel/plogical/virtualHostUtilities.py`**
   - Added `import re`
   - Added null value handling in `switchServer` function
   - Added fallback logic for admin email and external app

## Benefits

✅ **Bug Fixed**: Resolves the "must be str, not NoneType" error  
✅ **Backward Compatible**: Existing functionality continues to work  
✅ **Robust**: Handles edge cases with null database values  
✅ **User Friendly**: Apache Manager now works for all subdomains  
✅ **No Data Loss**: Preserves existing configurations  

## Verification

To verify the fix:

1. **Create a subdomain** without Apache reverse proxy
2. **Access Apache Manager** for that subdomain
3. **Switch to Apache** - should work without errors
4. **Check configuration** - should be properly created

## Changelog

- **2025-01-21**: Fixed Apache Manager "must be str, not NoneType" error
  - Added null value handling for `adminEmail` and `externalApp` fields
  - Added fallback logic for child domains and main domains
  - Added required `re` import
  - Resolved GitHub issue #1257

This fix ensures that the Apache Manager works correctly for all subdomains, regardless of how they were initially created, eliminating the "must be str, not NoneType" error that users encountered in 2024.
