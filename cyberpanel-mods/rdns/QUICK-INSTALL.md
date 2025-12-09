# Quick Install - rDNS Fix for CyberPanel 2.4.4

## One-Liner SSH Command

Copy and paste this command into your SSH terminal:

```bash
sh <(curl https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh || wget -O - https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh)
```

## Alternative: Using bash

```bash
bash <(curl -s https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh) || bash <(wget -O - https://raw.githubusercontent.com/master3395/cyberpanel-mods/main/rdns/rdns-fix.sh)
```

## What It Does

1. ✅ Creates automatic backups
2. ✅ Fixes NameError bug (`str(msg)` → `str(e)`)
3. ✅ Replaces `reverse_dns_lookup()` with improved version
4. ✅ Adds empty rDNS result validation
5. ✅ Improves error messages with debugging info
6. ✅ Restarts CyberPanel automatically

## Requirements

- Root/sudo access
- CyberPanel 2.4.4 installed
- Internet connection (to download script)

## After Installation

1. Test the onboarding process in CyberPanel
2. Check that error messages are more descriptive
3. Review logs if needed: `tail -f /home/cyberpanel/cyberpanel.log`

## Rollback

If needed, restore from backup:

```bash
# Find backup directory
ls -la /usr/local/CyberCP/backup_rdns_fix_*

# Restore (replace TIMESTAMP with actual backup timestamp)
sudo cp /usr/local/CyberCP/backup_rdns_fix_TIMESTAMP/mailUtilities.py /usr/local/CyberCP/plogical/mailUtilities.py
sudo cp /usr/local/CyberCP/backup_rdns_fix_TIMESTAMP/virtualHostUtilities.py /usr/local/CyberCP/plogical/virtualHostUtilities.py
sudo systemctl restart lscpd
```

