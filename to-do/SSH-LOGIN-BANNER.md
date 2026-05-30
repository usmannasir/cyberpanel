# SSH login banner (`/etc/profile.d/cyberpanel.sh`)

## What it is

On SSH login (interactive login shell), the server prints CyberPanel server stats (IP, panel URL, load, CPU, RAM, disk, uptime). The script is **not** the panel web terminal; it is installed under `/etc/profile.d/`.

## Source

Downloaded at install/upgrade from:

`https://cyberpanel.sh/?banner`

## v2.5.5-dev regression

- **2.4.x:** `Post_Install_Tweak()` in `cyberpanel.sh` installed the banner.
- **2.5.5-dev:** `cyberpanel.sh` is a thin module loader; `Post_Install_Tweak` was removed. Default install uses `install.py` via `install_modules/` and does not run `venvsetup.sh`, so `04_after_install.sh` (which had the curl lines) was never executed.

## Fix (2026-05-30)

Shared helper: `install/cyberpanel_ssh_login_banner.sh` (`Install_Cyberpanel_Ssh_Login_Banner`).

Called from:

- `install_modules/04_fixes_status.sh` → `apply_fixes()`
- `upgrade_modules/10_post_tweak.sh` → `Post_Upgrade_System_Tweak()`
- `install/venvsetup_modules/04_after_install.sh` (legacy venvsetup path)
- Monolithic install/upgrade scripts (parity)

## Manual reinstall on a live server

```bash
curl -fsSL -o /etc/profile.d/cyberpanel.sh https://cyberpanel.sh/?banner
chmod 644 /etc/profile.d/cyberpanel.sh
```

Log out and SSH in again to see the banner.
