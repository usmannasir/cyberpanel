# Premium Plugin Example

An example paid plugin for CyberPanel that demonstrates how to implement Patreon subscription-based plugin access.

## Features

- Requires Patreon subscription to "CyberPanel Paid Plugin" tier
- Users can install the plugin without subscription
- Plugin functionality is locked until subscription is verified
- Shows subscription required page when accessed without subscription

## Installation

1. Upload the plugin ZIP file to CyberPanel
2. Install the plugin from the plugin manager
3. The plugin will appear in the installed plugins list

## Usage

### For Users Without Subscription

- Plugin can be installed
- When accessing the plugin, a subscription required page is shown
- Link to Patreon subscription page is provided

### For Users With Subscription

- Plugin works normally
- All features are accessible
- Settings page is available

## Configuration

The plugin checks for Patreon membership via the Patreon API. Make sure to configure:

1. Patreon Client ID
2. Patreon Client Secret
3. Patreon Creator ID

These should be set in CyberPanel environment variables or settings.

## Meta.xml Structure

The plugin uses the following meta.xml structure for paid plugins:

```xml
<paid>true</paid>
<patreon_tier>CyberPanel Paid Plugin</patreon_tier>
<patreon_url>https://www.patreon.com/c/newstargeted/membership</patreon_url>
```

## Author

master3395

## License

MIT
