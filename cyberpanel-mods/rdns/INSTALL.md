# Installation Guide - rDNS Fix for CyberPanel 2.4.4

## Quick Installation

### Option 1: One-Liner SSH Command (Easiest - Recommended)

Run this single command via SSH:

```bash
sh <(curl https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh || wget -O - https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh)
```

Or using bash:

```bash
bash <(curl -s https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh) || bash <(wget -O - https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh)
```

### Option 2: Local Installation

```bash
cd /path/to/cyberpanel/cyberpanel-mods/rdns
chmod +x rdns-fix.sh
sudo ./rdns-fix.sh
```

### Option 3: Manual Installation

Follow the step-by-step guide below.

## Manual Installation Steps

### Step 1: Backup Original Files

```bash
# Create backup directory
sudo mkdir -p /usr/local/CyberCP/backup_rdns_fix_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/usr/local/CyberCP/backup_rdns_fix_$(date +%Y%m%d_%H%M%S)"

# Backup files
sudo cp /usr/local/CyberCP/plogical/mailUtilities.py "$BACKUP_DIR/mailUtilities.py"
sudo cp /usr/local/CyberCP/plogical/virtualHostUtilities.py "$BACKUP_DIR/virtualHostUtilities.py"

echo "Backup created at: $BACKUP_DIR"
```

### Step 2: Apply Fix to mailUtilities.py

#### Method A: Using sed (Quick Fix for NameError only)

```bash
# Fix the critical NameError bug
sudo sed -i 's/str(msg)/str(e)/g' /usr/local/CyberCP/plogical/mailUtilities.py
```

#### Method B: Replace the entire function (Comprehensive Fix)

1. Locate the `reverse_dns_lookup` function in `/usr/local/CyberCP/plogical/mailUtilities.py` (around line 1637)

2. Replace the entire function with the content from `mailUtilities_fixed.py` in this mod directory

3. Or use Python to apply the fix:

```python
# Run as root
import re

file_path = '/usr/local/CyberCP/plogical/mailUtilities.py'

with open(file_path, 'r') as f:
    content = f.read()

# Find and replace the function
# (You'll need to manually copy the fixed function from mailUtilities_fixed.py)

with open(file_path, 'w') as f:
    f.write(content)
```

### Step 3: Apply Fix to virtualHostUtilities.py

1. Open `/usr/local/CyberCP/plogical/virtualHostUtilities.py`

2. Find the `OnBoardingHostName` function

3. Replace the rDNS lookup section (around lines 119-137) with Section 1 from `virtualHostUtilities_fixed.py`

4. Replace the domain validation section (around lines 333-343) with Section 2 from `virtualHostUtilities_fixed.py`

### Step 4: Verify Changes

```bash
# Check if NameError fix is applied
grep -n "str(e)" /usr/local/CyberCP/plogical/mailUtilities.py | grep "Error in fetch rDNS"

# Should show the fixed line, not "str(msg)"
```

### Step 5: Restart CyberPanel

```bash
sudo systemctl restart lscpd
```

### Step 6: Test

1. Access CyberPanel web interface
2. Go to Onboarding page
3. Try configuring a hostname
4. Check that error messages are more descriptive
5. Review logs: `tail -f /home/cyberpanel/cyberpanel.log`

## Verification Checklist

- [ ] Backup created successfully
- [ ] NameError bug fixed (no `str(msg)` in mailUtilities.py)
- [ ] Empty rDNS result handling added
- [ ] Error messages include IP and domain information
- [ ] CyberPanel restarted successfully
- [ ] Tested onboarding process
- [ ] Logs show improved error messages

## Rollback Instructions

If you need to rollback:

```bash
# Find your backup directory
ls -la /usr/local/CyberCP/backup_rdns_fix_*

# Restore files (replace YYYYMMDD_HHMMSS with your backup timestamp)
sudo cp /usr/local/CyberCP/backup_rdns_fix_YYYYMMDD_HHMMSS/mailUtilities.py /usr/local/CyberCP/plogical/mailUtilities.py
sudo cp /usr/local/CyberCP/backup_rdns_fix_YYYYMMDD_HHMMSS/virtualHostUtilities.py /usr/local/CyberCP/plogical/virtualHostUtilities.py

# Restart CyberPanel
sudo systemctl restart lscpd
```

## Troubleshooting

### Issue: Permission Denied

```bash
# Ensure you're running as root
sudo su -

# Check file ownership
ls -la /usr/local/CyberCP/plogical/mailUtilities.py
```

### Issue: Changes Not Applied

1. Verify file paths are correct
2. Check if files were modified: `stat /usr/local/CyberCP/plogical/mailUtilities.py`
3. Ensure CyberPanel was restarted
4. Check for syntax errors: `python3 -m py_compile /usr/local/CyberCP/plogical/mailUtilities.py`

### Issue: Still Getting Errors

1. Check logs: `tail -100 /home/cyberpanel/cyberpanel.log`
2. Verify DNS server availability: `curl https://cyberpanel.net/dnsServers.txt`
3. Test rDNS manually: `dig -x YOUR_IP_ADDRESS`

## Support

For issues or questions:
1. Check the README.md for detailed information
2. Review log files for specific error messages
3. Verify all steps were completed correctly

