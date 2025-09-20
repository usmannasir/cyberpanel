# Home Directory Management Guide for CyberPanel

## Overview

The Home Directory Management feature allows CyberPanel administrators to manage multiple home directories across different storage volumes (e.g., `/home`, `/home2`, `/home3`). This enables storage balancing, helps avoid upgrading main volume plans by utilizing cheaper additional volumes, and provides better resource distribution across your server.

## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Managing Home Directories](#managing-home-directories)
4. [User Management](#user-management)
5. [Website Management Integration](#website-management-integration)
6. [Storage Balancing](#storage-balancing)
7. [User Migration](#user-migration)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Advanced Configuration](#advanced-configuration)

## Features

### Core Capabilities
- **Multiple Home Directories**: Manage `/home`, `/home2`, `/home3`, etc.
- **Automatic Detection**: Auto-discover existing home directories
- **Storage Monitoring**: Real-time space usage and availability tracking
- **User Distribution**: Balance users across different storage volumes
- **Website Integration**: Manage home directories directly from website modification
- **User Migration**: Move users between home directories seamlessly
- **Storage Analytics**: Detailed usage statistics and recommendations

### Benefits
- **Cost Optimization**: Use cheaper additional volumes instead of upgrading main storage
- **Performance**: Distribute load across multiple storage devices
- **Scalability**: Easy expansion as your server grows
- **Flexibility**: Choose optimal storage for different user types
- **Monitoring**: Real-time visibility into storage usage

## Getting Started

### Prerequisites
- CyberPanel v2.5.5 or higher
- Administrator access
- Multiple storage volumes available (optional but recommended)
- Sufficient disk space for home directories

### Initial Setup

1. **Access Home Directory Management**
   - Log in to CyberPanel admin panel
   - Navigate to **User Management** → **Home Directory Management**

2. **Auto-Detect Existing Directories**
   - Click **"Detect Directories"** button
   - System will automatically find `/home`, `/home2`, `/home3`, etc.
   - Review detected directories and their status

3. **Configure Default Settings**
   - Set default home directory (usually `/home`)
   - Configure storage limits and user limits
   - Enable/disable directories as needed

### Database Migration (For Developers)
```bash
cd /usr/local/CyberCP
python manage.py makemigrations userManagment
python manage.py migrate
```

### Technical Implementation Details

#### Core Components
- **Models** (`models.py`): `HomeDirectory` and `UserHomeMapping` models
- **Management** (`homeDirectoryManager.py`): Core functionality for operations
- **Utilities** (`homeDirectoryUtils.py`): Helper functions for path resolution
- **Views** (`homeDirectoryViews.py`): Admin interface and API endpoints
- **Templates**: Management interfaces and user creation forms

#### File Structure
```
cyberpanel/userManagment/
├── models.py                    # Database models
├── homeDirectoryManager.py      # Core management logic
├── homeDirectoryUtils.py        # Utility functions
├── homeDirectoryViews.py        # API endpoints
├── templates/userManagment/
│   ├── homeDirectoryManagement.html
│   ├── userMigration.html
│   └── createUser.html (updated)
└── migrations/
    └── 0001_home_directories.py
```

## Managing Home Directories

### Adding New Home Directories

#### Method 1: Automatic Detection
```bash
# The system automatically detects directories matching pattern /home[0-9]*
# No manual intervention required
```

#### Method 2: Manual Creation
1. **Create Directory on Server**
   ```bash
   sudo mkdir /home2
   sudo chown root:root /home2
   sudo chmod 755 /home2
   ```

2. **Detect in CyberPanel**
   - Go to Home Directory Management
   - Click **"Detect Directories"**
   - New directory will appear in the list

### Configuring Home Directories

#### Basic Configuration
- **Name**: Display name for the directory
- **Path**: Full system path (e.g., `/home2`)
- **Description**: Optional description for identification
- **Status**: Active/Inactive
- **Default**: Set as default for new users

#### Advanced Settings
- **Maximum Users**: Limit number of users per directory
- **Storage Quota**: Set storage limits (if supported by filesystem)
- **Priority**: Directory selection priority for auto-assignment

### Directory Status Management

#### Active Directories
- Available for new user assignments
- Included in auto-selection algorithms
- Monitored for storage usage

#### Inactive Directories
- Not available for new users
- Existing users remain unaffected
- Useful for maintenance or decommissioning

## User Management

### Creating Users with Home Directory Selection

1. **Navigate to User Creation**
   - Go to **User Management** → **Create User**

2. **Select Home Directory**
   - Choose from dropdown list of available directories
   - View real-time storage information
   - Select "Auto-select" for automatic assignment

3. **Review Assignment**
   - System shows selected directory details
   - Displays available space and user count
   - Confirms assignment before creation

### Auto-Assignment Logic

The system automatically selects the best home directory based on:
- **Available Space**: Prioritizes directories with more free space
- **User Count**: Balances users across directories
- **Directory Status**: Only considers active directories
- **User Limits**: Respects maximum user limits per directory

### Manual User Assignment

1. **Access User Migration**
   - Go to **User Management** → **User Migration**

2. **Select User and Target Directory**
   - Choose user to migrate
   - Select destination home directory
   - Review migration details

3. **Execute Migration**
   - System moves user data
   - Updates all references
   - Verifies successful migration

## Website Management Integration

### Modifying Website Home Directory

1. **Access Website Modification**
   - Go to **Websites** → **Modify Website**
   - Select website to modify

2. **Change Home Directory**
   - Select new home directory from dropdown
   - View current and available options
   - See real-time storage information

3. **Save Changes**
   - System migrates website owner
   - Updates all website references
   - Maintains website functionality

### Website Owner Migration

When changing a website's home directory:
- **User Data**: Website owner is migrated to new directory
- **Website Files**: All website files are moved
- **Database References**: All database references updated
- **Permissions**: File permissions maintained
- **Services**: Email, FTP, and other services updated

## Storage Balancing

### Monitoring Storage Usage

#### Real-Time Statistics
- **Total Space**: Combined storage across all directories
- **Available Space**: Free space available
- **Usage Percentage**: Visual progress bars
- **User Distribution**: Users per directory

#### Storage Alerts
- **Low Space Warning**: When directory approaches capacity
- **Full Directory Alert**: When directory reaches maximum users
- **Performance Impact**: Storage performance recommendations

### Balancing Strategies

#### Automatic Balancing
- **New User Assignment**: Distributes users evenly
- **Space-Based Selection**: Prioritizes directories with more space
- **Load Distribution**: Spreads load across multiple volumes

#### Manual Balancing
- **User Migration**: Move users between directories
- **Directory Management**: Enable/disable directories
- **Capacity Planning**: Monitor and plan for growth

## User Migration

### Migration Process

1. **Pre-Migration Checks**
   - Verify source and destination directories
   - Check available space
   - Validate user permissions

2. **Data Migration**
   - Copy user home directory
   - Update system references
   - Verify data integrity

3. **Post-Migration Verification**
   - Test user access
   - Verify website functionality
   - Update service configurations

### Migration Safety

#### Backup Recommendations
```bash
# Always backup before migration
sudo tar -czf /backup/user-backup-$(date +%Y%m%d).tar.gz /home/username
```

#### Rollback Procedures
- Keep original data until migration verified
- Maintain backup of system configurations
- Document all changes made

### Migration Commands

#### Manual Migration (Advanced Users)
```bash
# Stop user services
sudo systemctl stop user@username

# Copy user data
sudo rsync -av /home/username/ /home2/username/

# Update user home in system
sudo usermod -d /home2/username username

# Update CyberPanel database
# (Use web interface for this)
```

## Troubleshooting

### Common Issues

#### 1. Directory Not Detected
**Problem**: New home directory not appearing in list
**Solution**:
```bash
# Check directory exists and has correct permissions
ls -la /home2
sudo chown root:root /home2
sudo chmod 755 /home2

# Refresh detection in CyberPanel
# Click "Detect Directories" button
```

#### 2. Migration Fails
**Problem**: User migration fails with errors
**Solution**:
- Check available space in destination
- Verify user permissions
- Review CyberPanel logs
- Ensure destination directory is active

#### 3. Website Access Issues
**Problem**: Website not accessible after migration
**Solution**:
- Check file permissions
- Verify web server configuration
- Update virtual host settings
- Restart web server services

#### 4. Storage Not Updating
**Problem**: Storage statistics not reflecting changes
**Solution**:
- Click "Refresh Stats" button
- Check filesystem mount status
- Verify directory accessibility
- Review system logs

### Diagnostic Commands

#### Check Directory Status
```bash
# List all home directories
ls -la /home*

# Check disk usage
df -h /home*

# Check permissions
ls -la /home*/username
```

#### Verify User Assignments
```bash
# Check user home directories
getent passwd | grep /home

# Check CyberPanel database
# (Use web interface or database tools)
```

#### Monitor Storage Usage
```bash
# Real-time disk usage
watch -n 5 'df -h /home*'

# Directory sizes
du -sh /home*

# User directory sizes
du -sh /home*/username
```

### Log Files

#### CyberPanel Logs
```bash
# Main CyberPanel log
tail -f /usr/local/CyberCP/logs/cyberpanel.log

# Home directory specific logs
grep "home.*directory" /usr/local/CyberCP/logs/cyberpanel.log
```

#### System Logs
```bash
# System messages
tail -f /var/log/messages

# Authentication logs
tail -f /var/log/auth.log
```

## Best Practices

### Storage Planning

#### Directory Organization
- **Primary Directory** (`/home`): Default for most users
- **Secondary Directories** (`/home2`, `/home3`): For specific user groups
- **Naming Convention**: Use descriptive names (e.g., `/home-ssd`, `/home-hdd`)

#### Capacity Management
- **Monitor Usage**: Regular storage monitoring
- **Set Alerts**: Configure low-space warnings
- **Plan Growth**: Anticipate future storage needs
- **Regular Cleanup**: Remove unused user data

### User Management

#### Assignment Strategy
- **New Users**: Use auto-assignment for balanced distribution
- **Special Cases**: Manually assign users with specific requirements
- **Regular Review**: Periodically review user distribution

#### Migration Planning
- **Schedule Migrations**: Plan during low-usage periods
- **Test First**: Verify migration process with test users
- **Communicate Changes**: Inform users of planned migrations

### Security Considerations

#### Access Control
- **Directory Permissions**: Maintain proper file permissions
- **User Isolation**: Ensure users can only access their directories
- **System Security**: Regular security updates and monitoring

#### Backup Strategy
- **Regular Backups**: Backup user data regularly
- **Migration Backups**: Always backup before migrations
- **Configuration Backups**: Backup CyberPanel configurations

## Advanced Configuration

### Custom Directory Paths

#### Non-Standard Paths
```bash
# Create custom home directory
sudo mkdir /var/home
sudo chown root:root /var/home
sudo chmod 755 /var/home

# Add to CyberPanel manually
# (Use web interface to add custom paths)
```

#### Network Storage
- **NFS Mounts**: Use NFS for network-attached storage
- **iSCSI**: Configure iSCSI for block-level storage
- **Cloud Storage**: Integrate with cloud storage solutions

### Performance Optimization

#### Storage Performance
- **SSD vs HDD**: Use SSDs for frequently accessed data
- **RAID Configuration**: Optimize RAID for performance
- **Caching**: Implement appropriate caching strategies

#### Load Balancing
- **User Distribution**: Balance users across storage devices
- **I/O Optimization**: Optimize I/O patterns
- **Monitoring**: Monitor performance metrics

### Integration with Other Features

#### Backup Integration
- **Automated Backups**: Include home directories in backup schedules
- **Incremental Backups**: Use incremental backup strategies
- **Restore Procedures**: Test restore procedures regularly

#### Monitoring Integration
- **Storage Monitoring**: Integrate with monitoring systems
- **Alerting**: Set up automated alerts
- **Reporting**: Generate regular usage reports

## API Reference

### Home Directory Management API

#### Get Home Directories
```bash
curl -X POST https://your-server:8090/userManagement/getUserHomeDirectories/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Update Home Directory
```bash
curl -X POST https://your-server:8090/userManagement/updateHomeDirectory/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "description": "Updated description",
    "max_users": 100,
    "is_active": true
  }'
```

#### Migrate User
```bash
curl -X POST https://your-server:8090/userManagement/migrateUser/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "new_home_directory_id": 2
  }'
```

### Complete API Endpoints

#### Home Directory Management
- `POST /userManagement/detectHomeDirectories/` - Detect new home directories
- `POST /userManagement/updateHomeDirectory/` - Update home directory settings
- `POST /userManagement/deleteHomeDirectory/` - Delete home directory
- `POST /userManagement/getHomeDirectoryStats/` - Get storage statistics

#### User Operations
- `POST /userManagement/getUserHomeDirectories/` - Get available home directories
- `POST /userManagement/migrateUser/` - Migrate user to different home directory

#### Website Integration
- `POST /websites/saveWebsiteChanges/` - Save website changes including home directory
- `POST /websites/getWebsiteDetails/` - Get website details including current home directory

## Support and Resources

### Documentation
- **CyberPanel Documentation**: https://cyberpanel.net/docs/
- **User Management Guide**: This guide
- **API Documentation**: Available in CyberPanel interface

### Community Support
- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

### Professional Support
- **CyberPanel Support**: Available through official channels
- **Custom Implementation**: Contact for enterprise solutions

---

**Note**: This guide covers the complete Home Directory Management feature in CyberPanel. For the latest updates and additional features, refer to the official CyberPanel documentation and community resources.

*Last updated: January 2025*
