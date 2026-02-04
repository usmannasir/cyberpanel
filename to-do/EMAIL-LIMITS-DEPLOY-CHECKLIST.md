# Email Limits Fix – Deploy Checklist

Use this after pulling the Email Limits fixes in this repo so that https://your-panel/email/EmailLimits works (controller registers, email list loads, configure section works).

## Files that are part of the fix

| File | Purpose |
|------|--------|
| `mailServer/mailserverManager.py` | Passes controller JS to template; allows getEmailsForDomain for emailForwarding |
| `mailServer/templates/mailServer/EmailLimits.html` | Inline controller in footer_scripts (no static file dependency) |
| `mailServer/static/mailServer/mailServer.js` | EmailLimitsNew controller + guard for `$scope.emails` |
| `mailServer/static/mailServer/emailLimitsController.js` | Standalone controller + PNotify check fix |

## Option A: Deploy script (recommended)

**Run from anywhere** (use the full path to the script so the shell can find it):

```bash
sudo bash /home/cyberpanel-repo/deploy-email-limits-fix.sh
```

Or from repo root:

```bash
cd /home/cyberpanel-repo && sudo bash deploy-email-limits-fix.sh
```

- Script auto-detects repo at `/home/cyberpanel-repo` if run from another directory.
- Default CyberPanel path: `/usr/local/CyberCP`.
- Override: `sudo bash /home/cyberpanel-repo/deploy-email-limits-fix.sh /path/to/repo /usr/local/CyberCP`.
- Skip restart: `sudo RESTART_LSCPD=0 bash /home/cyberpanel-repo/deploy-email-limits-fix.sh`.

## Option B: Manual copy + restart

On the server, from the repo root (e.g. `/home/cyberpanel-repo`):

```bash
CP_DIR=/usr/local/CyberCP

cp -f mailServer/mailserverManager.py "$CP_DIR/mailServer/"
cp -f mailServer/templates/mailServer/EmailLimits.html "$CP_DIR/mailServer/templates/mailServer/"
cp -f mailServer/static/mailServer/mailServer.js "$CP_DIR/mailServer/static/mailServer/"
cp -f mailServer/static/mailServer/emailLimitsController.js "$CP_DIR/mailServer/static/mailServer/"

sudo systemctl restart lscpd
```

## After deploy

1. Hard refresh the Email Limits page: **Ctrl+Shift+R** (or Cmd+Shift+R).
2. Open **Email Limits**, choose a **website**, then check that **email account** dropdown fills and **Configure Email Limits** appears and works.

## If it still fails

- Confirm the four files above are present under `$CP_DIR` and were updated (check timestamps).
- Check panel/Python logs and browser console for `[$controller:ctrlreg]` or JS errors.
- Ensure `lscpd` (or the process serving the panel) was restarted after copying.
