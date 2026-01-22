# Resource Limits Guide for CyberPanel

## Overview

CyberPanel now supports comprehensive resource limits for shared hosting environments using OpenLiteSpeed's native cgroups v2 integration. This feature allows you to enforce CPU, memory, I/O, inode, process, and connection limits on a per-package basis.

## Features

- **Memory Limits**: Set RAM limits (in MB) for each hosting package
- **CPU Limits**: Allocate specific CPU cores to packages
- **I/O Limits**: Control disk I/O bandwidth (in MB/s)
- **Inode Limits**: Limit the number of files/directories
- **Process Limits**: Set soft and hard process count limits
- **Connection Limits**: Control maximum concurrent PHP connections

## Prerequisites

### System Requirements

1. **Linux Kernel**: 5.2+ (for native cgroups v2 support)
   - Ubuntu 20.04+, Debian 11+, CentOS Stream 9+, AlmaLinux 9+, Rocky Linux 9+
   - RHEL 8 family (RHEL 8, AlmaLinux 8, Rocky 8, CloudLinux 8) with cgroups v2 manually enabled

2. **CyberPanel Version**: v2.4.4-dev or later

3. **OpenLiteSpeed**: Installed and running

### Checking Kernel Support

To verify your system supports cgroups v2:

```bash
# Check if cgroups v2 is available
ls /sys/fs/cgroup/cgroup.controllers

# Check kernel version
uname -r
```

### Enabling cgroups v2 on RHEL 8 Family

If you're running RHEL 8, AlmaLinux 8, Rocky 8, or CloudLinux 8:

```bash
# Edit GRUB configuration
vi /etc/default/grub

# Add to GRUB_CMDLINE_LINUX:
systemd.unified_cgroup_hierarchy=1 cgroup_no_v1=all

# Update GRUB
grub2-mkconfig -o /boot/grub2/grub.cfg

# Reboot
reboot

# Verify after reboot
mount | grep cgroup2
```

## Using Resource Limits

### Step 1: Create a Package with Resource Limits

1. **Navigate to Packages**
   - Go to `Packages → Create Package`

2. **Basic Package Information**
   - Enter Package Name
   - Set Disk Space (MB)
   - Set Bandwidth (MB)
   - Configure Email Accounts, Databases, FTP Accounts, Allowed Domains

3. **Enable Resource Limits**
   - Check the **"Enforce Disk Limits"** checkbox
   - This enables all resource limit enforcement (not just disk)

4. **Configure Advanced Resource Limits**

   Under "Advanced Resource Limits" section:

   **CPU & Memory:**
   - **Memory Limit (MB)**: RAM limit (default: 1024 MB)
   - **CPU Cores**: Number of CPU cores (default: 1)

   **I/O & Storage:**
   - **I/O Limit (MB/s)**: Disk I/O bandwidth (default: 10 MB/s)
   - **Inode Limit**: Maximum files/directories (default: 400000)

   **Process & Connection Limits:**
   - **Max Connections**: Concurrent PHP connections (default: 10)
   - **Process Soft Limit**: Soft process count (default: 400)
   - **Process Hard Limit**: Hard process count (default: 500)

5. **Save Package**

### Step 2: Create a Website with Resource Limits

1. **Navigate to Websites**
   - Go to `Websites → Create Website`

2. **Website Configuration**
   - Enter Domain Name
   - Select the package you created (with resource limits)
   - Choose PHP version
   - Configure other settings as needed

3. **Create Website**
   - Click "Create Website"
   - CyberPanel will automatically:
     - Detect and configure OpenLiteSpeed cgroups (if needed)
     - Apply resource limits to the website's user
     - Set filesystem quotas

### Step 3: Verify Resource Limits

After creating a website, you can verify the limits are applied.

#### Check cgroups Configuration

```bash
# Check if OpenLiteSpeed cgroups are enabled
grep -A 5 "CGIRLimit" /usr/local/lsws/conf/httpd_config.conf

# Should show: cgroups 1
```

#### Check User Resource Limits

```bash
# List limits for a specific user
/usr/local/lsws/lsns/bin/lscgctl list-user <username>

# Example output:
# {
#     "1005": {
#         "name": "example1234",
#         "cpu": "200",      # 200% = 2 cores
#         "io": "20M",       # 20 MB/s
#         "mem": "2.0G",     # 2GB RAM
#         "tasks": "800"     # Max 800 processes
#     }
# }
```

#### Check Filesystem Quotas

```bash
# Check inode limit for user
quota -u <username>

# Example output:
# Disk quotas for user example1234 (uid 1005):
#      Filesystem  blocks   quota   limit   grace   files   quota   limit   grace
#       /dev/sda1     104       0       0              26  500000  500000
#                                                          ^^^^^^  ^^^^^^
#                                                          Inode limits
```

#### Check Kernel-Level cgroups

```bash
# Find the user ID
id -u <username>

# Check memory limit (in bytes)
cat /sys/fs/cgroup/user.slice/user-<UID>.slice/memory.max
# 2147483648 = 2GB

# Check process limit
cat /sys/fs/cgroup/user.slice/user-<UID>.slice/pids.max
# 800
```

## Testing Resource Limits

### Testing Memory Limits

Create a PHP script to test memory limits:

```php
<?php
// test-memory.php
ini_set('memory_limit', '-1'); // Remove PHP limit to test cgroup limit
ini_set('max_execution_time', '60');

echo "Testing memory limit...\n";
$data = [];

// Try to allocate more than the package limit
for ($i = 0; $i < 2000; $i++) { // Try 2GB
    $data[] = str_repeat('X', 1024 * 1024); // 1MB chunks

    if ($i % 100 == 0) {
        echo "Allocated: " . $i . " MB\n";
        flush();
    }
}

echo "Completed!\n";
?>
```

Access via web browser: `http://yourdomain.com/test-memory.php`

**Expected behavior**: Process should be terminated when exceeding the memory limit.

### Testing Process Limits

Create a PHP script to spawn processes:

```php
<?php
// test-processes.php
echo "Testing process limits...\n";

$processes = [];
$max = 1000; // Try to exceed limit

for ($i = 0; $i < $max; $i++) {
    $pid = pcntl_fork();

    if ($pid == -1) {
        echo "Failed to fork at process $i\n";
        break;
    } elseif ($pid) {
        $processes[] = $pid;
        echo "Created process $i (PID: $pid)\n";
        flush();
    } else {
        sleep(30);
        exit(0);
    }
}

echo "Created " . count($processes) . " processes\n";

// Clean up
foreach ($processes as $pid) {
    pcntl_waitpid($pid, $status);
}
?>
```

**Expected behavior**: Fork should fail when reaching the process hard limit.

## Automatic Setup

CyberPanel automatically handles OpenLiteSpeed cgroups setup:

1. **First-time Setup**: When you create a website with resource limits enabled:
   - Checks if cgroups v2 is available
   - Runs `lssetup` if LiteSpeed Containers not configured
   - Enables cgroups in OpenLiteSpeed config
   - Restarts OpenLiteSpeed
   - Applies resource limits

2. **Subsequent Websites**: Resource limits are applied instantly without restarting.

## Important Notes

### Resource Sharing

- **Subdomains and Addon Domains**: Share the same limits as the main domain
  - All domains under the same website use the same Linux user
  - Limits are enforced per-user, not per-domain

### I/O Limits Caveat

On some systems, the I/O controller may not be delegated to user slices by systemd. In this case:
- lscgctl will store the I/O configuration
- But kernel-level enforcement may not work
- CPU, Memory, and Process limits work on all supported systems

### Memory Limit Enforcement

Memory limits are enforced at the cgroup level:
- When limit is reached, processes are killed by the kernel
- Check `/sys/fs/cgroup/user.slice/user-<UID>.slice/memory.events` for OOM events

### Connection Limits

The "Max Connections" setting controls:
- Maximum concurrent PHP-FPM/LSPHP processes
- Configured in OpenLiteSpeed virtual host extprocessor settings

## Troubleshooting

### Resource Limits Not Working

1. **Check if enforcement is enabled**:
   ```bash
   mysql -u root -e "SELECT packageName, enforceDiskLimits FROM cyberpanel.packages_package;"
   ```
   Ensure `enforceDiskLimits` is `1` for your package.

2. **Check cgroups are enabled**:
   ```bash
   grep "cgroups" /usr/local/lsws/conf/httpd_config.conf
   ```
   Should show `cgroups 1`.

3. **Check lscgctl is configured**:
   ```bash
   /usr/local/lsws/lsns/bin/lscgctl list-all
   ```

4. **Check CyberPanel logs**:
   ```bash
   tail -100 /usr/local/CyberCP/logs/access.log
   ```

### RHEL 8 Family: cgroups v2 Not Available

If you see errors about cgroups v2 not being available on RHEL 8/AlmaLinux 8/Rocky 8:

1. Follow the [Enabling cgroups v2 on RHEL 8 Family](#enabling-cgroups-v2-on-rhel-8-family) steps
2. Reboot the server
3. Verify with `mount | grep cgroup2`

### LiteSpeed Containers Not Configured

If you see "You must configure LiteSpeed for LiteSpeed Containers":

1. CyberPanel should auto-run lssetup
2. If it doesn't work, manually run:
   ```bash
   /usr/local/lsws/lsns/bin/lssetup -c 2 -n 0 -s /usr/local/lsws
   ```
3. Restart OpenLiteSpeed:
   ```bash
   /usr/local/lsws/bin/lswsctrl restart
   ```

## Package Recommendations

Here are some example package configurations for different use cases:

### Basic Shared Hosting
- Memory: 512 MB
- CPU: 1 core
- I/O: 5 MB/s
- Inodes: 200,000
- Max Connections: 5
- Proc Soft/Hard: 200/300

### Standard Shared Hosting
- Memory: 1024 MB (1 GB)
- CPU: 1 core
- I/O: 10 MB/s
- Inodes: 400,000
- Max Connections: 10
- Proc Soft/Hard: 400/500

### Premium Shared Hosting
- Memory: 2048 MB (2 GB)
- CPU: 2 cores
- I/O: 20 MB/s
- Inodes: 800,000
- Max Connections: 20
- Proc Soft/Hard: 600/800

### Business Hosting
- Memory: 4096 MB (4 GB)
- CPU: 4 cores
- I/O: 50 MB/s
- Inodes: 1,000,000
- Max Connections: 50
- Proc Soft/Hard: 1000/1500

## FAQ

**Q: Do I need to restart OpenLiteSpeed after changing package limits?**
A: No, limits are applied immediately when you create a website or modify a package (though the website needs to be recreated for new limits to apply).

**Q: Can I change limits for existing websites?**
A: Yes, modify the package and then run:
```bash
/usr/local/lsws/lsns/bin/lscgctl set-user <username> --cpu <percent> --mem <size> --tasks <count>
```

**Q: Are limits enforced for email and FTP?**
A: The resource limits primarily apply to web processes (PHP). Email and FTP have separate process limits but share the same filesystem quotas (inodes).

**Q: What happens when a limit is reached?**
- **Memory**: Process is killed (OOM)
- **CPU**: Process is throttled
- **Processes**: Fork/exec fails
- **Inodes**: File creation fails
- **Connections**: New connections are queued or rejected

**Q: Can I disable resource limits after enabling them?**
A: Yes, uncheck "Enforce Disk Limits" in the package settings and recreate the website.

## Support

For issues or questions:
- GitHub: https://github.com/usmannasir/cyberpanel/issues
- Community Forum: https://community.cyberpanel.net
- Documentation: https://docs.cyberpanel.net
