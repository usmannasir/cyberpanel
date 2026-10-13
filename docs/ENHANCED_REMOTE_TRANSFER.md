# Enhanced Remote Transfer System for CyberPanel

## Overview

The Enhanced Remote Transfer system improves CyberPanel's migration capabilities by providing intelligent transfer mode selection and better disk space management. This enhancement addresses the critical issue where the current migration system requires 50%+ free disk space to create compressed backups of all selected websites simultaneously.

## Key Improvements

### 1. **Multiple Transfer Modes**

#### **Sequential Transfer Mode**
- **Use Case**: Low disk space scenarios (< 50% free)
- **Process**: Transfers websites one by one, cleaning up each backup before starting the next
- **Disk Space**: Minimal additional space required (only one website at a time)
- **Speed**: Slower but very disk-efficient

#### **Rsync Transfer Mode**
- **Use Case**: Very low disk space (< 30% free) or incremental transfers
- **Process**: Direct file synchronization without compression
- **Disk Space**: Almost no additional space needed
- **Speed**: Fast for subsequent transfers, preserves file permissions

#### **Parallel Transfer Mode**
- **Use Case**: High disk space availability (> 50% free)
- **Process**: Current CyberPanel method - all websites at once
- **Disk Space**: Requires significant free space (50%+)
- **Speed**: Fastest overall transfer time

### 2. **Intelligent Mode Selection**

The system automatically analyzes:
- **Available disk space**
- **Total size of selected websites**
- **Rsync availability**
- **System resources**

And recommends the optimal transfer mode based on this analysis.

### 3. **Enhanced User Interface**

- **Real-time disk space analysis**
- **Transfer mode compatibility indicators**
- **Progress tracking with current website display**
- **Estimated space requirements**
- **Visual recommendations**

## Technical Implementation

### Backend Components

#### 1. `enhancedRemoteTransfer.py`
Core transfer engine with three transfer algorithms:

```python
# Sequential transfer with cleanup
def sequentialTransferProcess(ipAddress, dir, backupLogPath, folderNumber, accountsToTransfer)

# Direct rsync-based transfer
def rsyncTransferProcess(ipAddress, dir, backupLogPath, folderNumber, accountsToTransfer)

# Enhanced wrapper function
def enhancedRemoteTransfer(ipAddress, dir, accountsToTransfer, transferMode=None)
```

#### 2. `enhancedRemoteTransfer.html`
Modern, responsive frontend with:
- Disk space visualization
- Mode selection cards with compatibility indicators
- Real-time progress tracking
- Website selection interface

#### 3. `enhancedRemoteTransfer.js`
Angular.js controller providing:
- Disk space analysis
- Transfer mode recommendations
- Progress monitoring
- User interaction handling

#### 4. API Endpoints
- `/backup/diskAnalysis` - Disk space analysis
- `/backup/updateRecommendations` - Mode recommendations
- `/backup/startEnhancedTransfer` - Initiate transfer
- `/backup/transferProgress` - Real-time progress
- `/backup/cancelTransfer` - Cancel active transfer

### Disk Space Analysis Algorithm

```python
def recommendTransferMode(websites):
    disk_info = getDiskUsage()
    total_size = calculateWebsitesSize(websites)
    free_percent = (disk_info['free'] / disk_info['total']) * 100

    if rsync_available and free_percent < 30:
        return 'rsync'
    elif free_percent < 50:
        return 'sequential'
    else:
        return 'parallel'
```

## Installation and Setup

### 1. Install Dependencies

```bash
cd /usr/local/CyberCP
pip install -r backup/requirements_enhanced.txt
```

### 2. Add URL Configuration

Add to your main `urls.py`:

```python
from backup.urls import enhancedRemoteTransfer

urlpatterns += [
    path('backup/', include(enhancedRemoteTransfer.urlpatterns)),
]
```

### 3. Update Static Files

Ensure the enhanced JavaScript is included in your base template:

```html
<script src="{% static 'backup/enhancedRemoteTransfer.js' %}"></script>
```

## Usage Examples

### Scenario 1: Low Disk Space Server
- **Available Space**: 20GB (25% of 80GB)
- **Websites to Transfer**: 5 sites totaling 30GB
- **Recommended Mode**: Rsync
- **Result**: Transfer succeeds with minimal disk usage

### Scenario 2: Medium Disk Space Server
- **Available Space**: 40GB (50% of 80GB)
- **Websites to Transfer**: 3 sites totaling 25GB
- **Recommended Mode**: Sequential
- **Result**: Transfer succeeds with cleanup between sites

### Scenario 3: High Disk Space Server
- **Available Space**: 60GB (75% of 80GB)
- **Websites to Transfer**: 10 sites totaling 20GB
- **Recommended Mode**: Parallel
- **Result**: Fastest transfer using existing method

## Benefits

### For System Administrators
- **Reduced failed transfers** due to disk space issues
- **Better resource utilization** during migrations
- **Incremental transfer support** with rsync
- **Real-time progress monitoring**

### For End Users
- **Intelligent recommendations** take the guesswork out of migration
- **Clear disk space requirements** before starting transfers
- **Visual progress tracking** with current website status
- **Flexibility** to override recommendations when needed

### For Hosting Providers
- **Lower support tickets** related to migration failures
- **Improved customer satisfaction** with reliable transfers
- **Better server utilization** with multiple transfer options
- **Professional migration experience** with modern UI

## Security Considerations

- **SSH key authentication** maintained from existing system
- **Root access required** for file operations (unchanged)
- **Secure rsync connections** with SSH encryption
- **Audit logging** for all transfer operations

## Monitoring and Logging

### Transfer Logs
Location: `/home/backup/transfer-{id}/backup_log`

Contains:
- Disk space analysis
- Transfer mode selection
- Per-website progress
- Error messages and troubleshooting information

### Progress Tracking
- Real-time progress percentage
- Current website being processed
- Transferred/total website count
- Estimated completion time

## Troubleshooting

### Common Issues

1. **Rsync Not Available**
   - Install rsync: `sudo apt-get install rsync` (Ubuntu/Debian)
   - The system will fallback to sequential mode automatically

2. **Permission Denied**
   - Ensure SSH keys are properly configured
   - Verify root access on remote server

3. **Disk Space Still Insufficient**
   - Use rsync mode for minimal space usage
   - Consider transferring fewer websites at once

### Debug Mode

Enable debug logging by creating:
```bash
touch /usr/local/CyberCP/debug
```

This will provide detailed command execution logs.

## Future Enhancements

### Planned Features
- **Resume capability** for interrupted transfers
- **Bandwidth throttling** for network-constrained environments
- **Parallel rsync** for multiple websites simultaneously
- **Cross-platform support** (Windows servers)

### API Expansion
- **RESTful API** for external management tools
- **Webhook notifications** for transfer completion
- **Batch transfer scheduling**
- **Transfer templates** for common scenarios

## Contributing

To contribute to this enhancement:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit pull requests with documentation

## License

This enhancement follows the same license as CyberPanel.

---

**Version**: 1.0.0
**Compatibility**: CyberPanel 2.4+
**Last Updated**: 2024