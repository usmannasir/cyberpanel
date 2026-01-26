# Paid Plugins Support for CyberPanel

## Overview

CyberPanel now supports paid plugins that require Patreon subscription. Users can install paid plugins, but they cannot run them without an active Patreon subscription to the specified tier.

## Features

- ✅ Paid plugin detection from `meta.xml`
- ✅ Patreon subscription verification
- ✅ Installable but non-functional without subscription
- ✅ Visual indicators (badges) for paid plugins in all views:
  - Grid View: Green "Free" or Yellow "Paid" badge next to version
  - Table View: Green "Free" or Yellow "Paid" badge next to version
  - Store View: Separate "Pricing" column with Free/Paid badges
- ✅ Subscription required page when accessing without subscription
- ✅ "Subscribe on Patreon" button in subscription warning
- ✅ API endpoint for checking subscription status

## Plugin Structure

### Meta.xml for Paid Plugins

Add the following fields to your plugin's `meta.xml`:

```xml
<paid>true</paid>
<patreon_tier>CyberPanel Paid Plugin</patreon_tier>
<patreon_url>https://www.patreon.com/membership/27789984</patreon_url>
```

### Example meta.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plugin>
    <name>Premium Plugin Example</name>
    <type>Utility</type>
    <version>1.0.0</version>
    <description>An example paid plugin</description>
    <author>master3395</author>
    <paid>true</paid>
    <patreon_tier>CyberPanel Paid Plugin</patreon_tier>
    <patreon_url>https://www.patreon.com/membership/27789984</patreon_url>
    <url>/plugins/premiumPlugin/</url>
    <settings_url>/plugins/premiumPlugin/settings/</settings_url>
</plugin>
```

## Implementation in Plugin Views

### Using the Premium Plugin Decorator

```python
from pluginHolder.plugin_access import check_plugin_access

def premium_plugin_required(view_func):
    """
    Decorator that checks if user has Patreon subscription
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check login first
        try:
            userID = request.session['userID']
        except KeyError:
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
        
        # Check plugin access
        plugin_meta = {
            'is_paid': True,
            'patreon_tier': 'CyberPanel Paid Plugin',
            'patreon_url': 'https://www.patreon.com/c/newstargeted/membership'
        }
        
        access_check = check_plugin_access(request, 'yourPluginName', plugin_meta)
        
        if not access_check['has_access']:
            # Show subscription required page
            context = {
                'plugin_name': 'Your Plugin Name',
                'is_paid': True,
                'patreon_tier': access_check.get('patreon_tier', 'CyberPanel Paid Plugin'),
                'patreon_url': access_check.get('patreon_url'),
                'message': access_check.get('message', 'Patreon subscription required')
            }
            proc = httpProc(request, 'yourPlugin/subscription_required.html', context, 'admin')
            return proc.render()
        
        # User has access - proceed
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

@cyberpanel_login_required
@premium_plugin_required
def your_view(request):
    # Your view code here
    pass
```

## Patreon Configuration

### Environment Variables

Set the following environment variables in CyberPanel:

```bash
export PATREON_CLIENT_ID="your_client_id"
export PATREON_CLIENT_SECRET="your_client_secret"
export PATREON_CREATOR_ID="your_creator_id"
```

Or add them to `/usr/local/CyberCP/CyberCP/settings.py`:

```python
import os

PATREON_CLIENT_ID = os.environ.get('PATREON_CLIENT_ID', '')
PATREON_CLIENT_SECRET = os.environ.get('PATREON_CLIENT_SECRET', '')
PATREON_CREATOR_ID = os.environ.get('PATREON_CREATOR_ID', '')
```

### User Token Storage

Users need to authorize CyberPanel to check their Patreon membership. Tokens are stored in:

```
/home/cyberpanel/patreon_tokens/{user_email}.token
```

## API Endpoints

### Check Subscription Status

```
GET /plugins/api/check-subscription/<plugin_name>/
```

Response:
```json
{
    "success": true,
    "has_access": true,
    "is_paid": true,
    "message": "Access granted",
    "patreon_url": null
}
```

## Example Plugin

A complete example paid plugin is available at:

```
/home/cyberpanel-plugins/premiumPlugin/
```

This plugin demonstrates:
- Paid plugin meta.xml structure
- Subscription verification
- Subscription required page
- Protected views

## User Experience

### For Users Without Subscription

1. Plugin appears in installed plugins list with "Premium" badge and "Paid" pricing badge
2. Plugin appears in CyberPanel Plugin Store with "Paid" badge in the Pricing column
3. Plugin can be installed
4. When accessing plugin, subscription required page is shown
5. Link to Patreon subscription page is provided with "Subscribe on Patreon" button

### For Users With Subscription

1. Plugin works normally
2. All features are accessible
3. Settings page is available
4. No restrictions

## Files Created/Modified

### New Files

- `/home/cyberpanel-repo/pluginHolder/patreon_verifier.py` - Patreon API integration
- `/home/cyberpanel-repo/pluginHolder/plugin_access.py` - Plugin access control
- `/home/cyberpanel-plugins/premiumPlugin/` - Example paid plugin

### Modified Files

- `/home/cyberpanel-repo/pluginHolder/views.py` - Added paid plugin parsing and subscription check API
- `/home/cyberpanel-repo/pluginHolder/templates/pluginHolder/plugins.html` - Added paid plugin badges and warnings
- `/home/cyberpanel-repo/pluginHolder/urls.py` - Added subscription check endpoint

## Testing

1. Install the example premium plugin
2. Try accessing it without subscription (should show subscription required page)
3. Subscribe to Patreon tier "CyberPanel Paid Plugin"
4. Authorize CyberPanel to check membership
5. Access plugin again (should work normally)

## Notes

- Subscription checks are cached for 5 minutes to reduce API calls
- Users must authorize CyberPanel to check their Patreon membership
- The system checks for the exact tier name specified in `patreon_tier`
- Free plugins work normally without any changes

## Author

master3395
