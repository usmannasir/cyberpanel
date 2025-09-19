# Docker Container Update/Upgrade Features

## Overview
This implementation adds comprehensive Docker container update/upgrade functionality to CyberPanel with full data persistence using Docker volumes. The solution addresses the GitHub issue [#1174](https://github.com/usmannasir/cyberpanel/issues/1174) by providing safe container updates without data loss.

## Features Implemented

### 1. Container Update with Data Preservation
- **Function**: `updateContainer()`
- **Purpose**: Update container to new image while preserving all data
- **Data Safety**: Uses Docker volumes to ensure no data loss
- **Process**:
  1. Extracts current container configuration (volumes, environment, ports)
  2. Pulls new image if not available locally
  3. Creates new container with same configuration but new image
  4. Preserves all volumes and data
  5. Removes old container only after successful new container startup
  6. Updates database records

### 2. Delete Container + Data
- **Function**: `deleteContainerWithData()`
- **Purpose**: Permanently delete container and all associated data
- **Safety**: Includes strong confirmation dialogs
- **Process**:
  1. Identifies all volumes associated with container
  2. Stops and removes container
  3. Deletes all associated Docker volumes
  4. Removes database records
  5. Provides confirmation of deleted volumes

### 3. Delete Container (Keep Data)
- **Function**: `deleteContainerKeepData()`
- **Purpose**: Delete container but preserve data in volumes
- **Use Case**: When you want to remove container but keep data for future use
- **Process**:
  1. Identifies volumes to preserve
  2. Stops and removes container
  3. Keeps all volumes intact
  4. Reports preserved volumes to user

## Technical Implementation

### Backend Changes

#### Views (`views.py`)
- `updateContainer()` - Handles container updates
- `deleteContainerWithData()` - Handles destructive deletion
- `deleteContainerKeepData()` - Handles data-preserving deletion

#### URLs (`urls.py`)
- `/docker/updateContainer` - Update endpoint
- `/docker/deleteContainerWithData` - Delete with data endpoint
- `/docker/deleteContainerKeepData` - Delete keep data endpoint

#### Container Manager (`container.py`)
- `updateContainer()` - Core update logic with volume preservation
- `deleteContainerWithData()` - Complete data removal
- `deleteContainerKeepData()` - Container removal with data preservation

### Frontend Changes

#### Template (`listContainers.html`)
- New update button with sync icon
- Dropdown menu for delete options
- Update modal with image/tag selection
- Enhanced styling for new components

#### JavaScript (`dockerManager.js`)
- `showUpdateModal()` - Opens update dialog
- `performUpdate()` - Executes container update
- `deleteContainerWithData()` - Handles destructive deletion
- `deleteContainerKeepData()` - Handles data-preserving deletion
- Enhanced confirmation dialogs

## User Interface

### New Buttons
1. **Update Button** (🔄) - Orange button for container updates
2. **Delete Dropdown** (🗑️) - Red dropdown with two options:
   - Delete Container (Keep Data) - Preserves volumes
   - Delete Container + Data - Removes everything

### Update Modal
- Container name (read-only)
- Current image (read-only)
- New image input field
- New tag input field
- Data safety information
- Confirmation buttons

### Confirmation Dialogs
- **Update**: Confirms image/tag change with data preservation notice
- **Delete + Data**: Strong warning about permanent data loss
- **Delete Keep Data**: Confirms container removal with data preservation

## Data Safety Features

### Volume Management
- Automatic detection of container volumes
- Support for both named volumes and bind mounts
- Volume preservation during updates
- Volume cleanup during destructive deletion

### Error Handling
- Rollback capability if update fails
- Comprehensive error messages
- Operation logging for debugging
- Graceful failure handling

### Security
- ACL permission checks
- Container ownership verification
- Input validation
- Rate limiting (existing)

## Usage Examples

### Updating a Container
1. Click the update button (🔄) next to any container
2. Enter new image name (e.g., `nginx`, `mysql`)
3. Enter new tag (e.g., `latest`, `1.21`, `alpine`)
4. Click "Update Container"
5. Confirm the operation
6. Container updates with all data preserved

### Deleting with Data Preservation
1. Click the delete dropdown (🗑️) next to any container
2. Select "Delete Container (Keep Data)"
3. Confirm the operation
4. Container is removed but data remains in volumes

### Deleting Everything
1. Click the delete dropdown (🗑️) next to any container
2. Select "Delete Container + Data"
3. Read the warning carefully
4. Confirm the operation
5. Container and all data are permanently removed

## Benefits

### For Users
- **No Data Loss**: Updates preserve all container data
- **Easy Updates**: Simple interface for container updates
- **Flexible Deletion**: Choose between data preservation or complete removal
- **Clear Warnings**: Understand exactly what each operation does

### For Administrators
- **Safe Operations**: Built-in safety measures prevent accidental data loss
- **Audit Trail**: All operations are logged
- **Rollback Capability**: Failed updates can be rolled back
- **Volume Management**: Clear visibility into data storage

## Technical Requirements

### Docker Features Used
- Docker volumes for data persistence
- Container recreation with volume mounting
- Image pulling and management
- Volume cleanup and management

### Dependencies
- Docker Python SDK
- Existing CyberPanel ACL system
- PNotify for user notifications
- Bootstrap for UI components

## Testing

A test script is provided (`test_docker_update.py`) that verifies:
- All new methods are available
- Function signatures are correct
- Error handling is in place
- UI components are properly integrated

## Future Enhancements

### Potential Improvements
1. **Bulk Operations**: Update/delete multiple containers
2. **Scheduled Updates**: Automatic container updates
3. **Update History**: Track container update history
4. **Volume Management UI**: Direct volume management interface
5. **Backup Integration**: Automatic backups before updates

### Monitoring
1. **Update Notifications**: Email notifications for updates
2. **Health Checks**: Verify container health after updates
3. **Performance Metrics**: Track update performance
4. **Error Reporting**: Detailed error reporting and recovery

## Conclusion

This implementation provides a complete solution for Docker container updates in CyberPanel while ensuring data safety through Docker volumes. The user-friendly interface makes container management accessible while the robust backend ensures data integrity and system stability.

The solution addresses the original GitHub issue by providing:
- ✅ Safe container updates without data loss
- ✅ Clear separation between container and data deletion
- ✅ User-friendly interface with proper confirmations
- ✅ Comprehensive error handling and rollback capability
- ✅ Full integration with existing CyberPanel architecture
