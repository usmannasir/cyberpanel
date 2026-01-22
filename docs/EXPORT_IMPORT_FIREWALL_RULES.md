# Firewall Rules Export/Import Feature

## Overview

This feature allows CyberPanel administrators to export and import firewall rules between servers, making it easy to replicate security configurations across multiple servers.

## Features

### Export Functionality
- Exports all custom firewall rules to a JSON file
- Excludes default CyberPanel rules (CyberPanel Admin, SSHCustom) to prevent conflicts
- Includes metadata such as export timestamp and rule count
- Downloads file directly to the user's browser

### Import Functionality
- Imports firewall rules from a previously exported JSON file
- Validates file format before processing
- Skips duplicate rules (same name, protocol, port, and IP address)
- Excludes default CyberPanel rules from import
- Provides detailed import summary (imported, skipped, error counts)
- Shows specific error messages for failed imports

## Usage

### Exporting Rules
1. Navigate to the Firewall section in CyberPanel
2. Click the "Export Rules" button in the Firewall Rules panel header
3. The system will generate and download a JSON file containing your custom rules

### Importing Rules
1. Navigate to the Firewall section in CyberPanel
2. Click the "Import Rules" button in the Firewall Rules panel header
3. Select a previously exported JSON file
4. The system will process the import and show a summary of results

## File Format

The exported JSON file has the following structure:

```json
{
  "version": "1.0",
  "exported_at": "2024-01-15 14:30:25",
  "total_rules": 5,
  "rules": [
    {
      "name": "Custom Web Server",
      "proto": "tcp",
      "port": "8080",
      "ipAddress": "0.0.0.0/0"
    },
    {
      "name": "Database Access",
      "proto": "tcp", 
      "port": "3306",
      "ipAddress": "192.168.1.0/24"
    }
  ]
}
```

## Security Considerations

- Only administrators can export/import firewall rules
- Default CyberPanel rules are excluded to prevent system conflicts
- Import process validates file format and rule data
- Failed imports are logged for troubleshooting
- Duplicate rules are automatically skipped

## Error Handling

The system provides comprehensive error handling:
- Invalid file format detection
- Missing required fields validation
- Individual rule import error tracking
- Detailed error messages for troubleshooting
- Import summary with counts of successful, skipped, and failed imports

## Technical Implementation

### Backend Components
- `exportFirewallRules()` method in `FirewallManager`
- `importFirewallRules()` method in `FirewallManager`
- New URL patterns for export/import endpoints
- File upload handling for import functionality

### Frontend Components
- Export/Import buttons in firewall UI
- File download handling for exports
- File upload dialog for imports
- Progress indicators and error messaging
- Import summary display

### Database Integration
- Uses existing `FirewallRules` model
- Maintains referential integrity
- Preserves rule relationships and constraints

## Benefits

1. **Time Efficiency**: Significantly reduces time to replicate firewall rules across servers
2. **Error Reduction**: Minimizes human error in manual rule creation
3. **Consistency**: Ensures identical security policies across multiple servers
4. **Backup**: Provides a way to backup and restore firewall configurations
5. **Migration**: Simplifies server migration and setup processes

## Compatibility

- Compatible with CyberPanel's existing firewall system
- Works with both TCP and UDP protocols
- Supports all IP address formats (single IPs, CIDR ranges)
- Maintains compatibility with existing firewall utilities

## Future Enhancements

Potential future improvements could include:
- Rule conflict detection and resolution
- Selective rule import (choose specific rules)
- Rule templates and presets
- Bulk rule management
- Integration with configuration management tools
