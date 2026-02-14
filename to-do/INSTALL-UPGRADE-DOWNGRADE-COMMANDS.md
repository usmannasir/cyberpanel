# CyberPanel Install, Upgrade, and Downgrade Commands

Reference for all standard and branch-specific install/upgrade/downgrade commands (master3395 fork and upstream).

---

## Installation logs (v2.4.4 / v2.5.5-dev)

When you run the installer (cyberpanel.sh or install.py), logs are written to:

| Log | Location | Description |
|-----|----------|--------------|
| Installer script | `/var/log/CyberPanel/install.log` | Messages from cyberpanel.sh (print_status) |
| Installer output | `/var/log/CyberPanel/install_output.log` | Full stdout/stderr of the Python installer (tee) |
| Python installer | `/var/log/installLogs.txt` | Detailed log from install.py (installLog module) |

To inspect after a failed install:

```bash
tail -100 /var/log/CyberPanel/install_output.log
tail -100 /var/log/installLogs.txt
```

**If you see ERR_CONNECTION_TIMED_OUT** when opening the panel URL: the install may have failed before LiteSpeed was set up, or ports are blocked. Ensure ports **8090** (panel) and **7080** (LSWS admin) are open in the server firewall and in your cloud security group (e.g. AWS). Re-run the installer after pulling the latest fixes so the install can complete.

---

## Fresh install

### One-liner (official / upstream)

```bash
sh <(curl https://cyberpanel.net/install.sh)
```

### One-liner with sudo (if not root)

```bash
curl -sO https://cyberpanel.net/install.sh && sudo bash install.sh
# or
curl -sL https://cyberpanel.net/install.sh | sudo bash -s --
```

### Install from master3395 fork (this repo)

**Stable:**

```bash
curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel.sh | sudo bash -s --
```

**Development (v2.5.5-dev):**

```bash
curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel.sh | sudo bash -s -- -b v2.5.5-dev
```

### Install with branch/version options

```bash
# Download script first (recommended so -b/-v work reliably)
curl -sL -o cyberpanel.sh https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel.sh
chmod +x cyberpanel.sh
sudo bash cyberpanel.sh [OPTIONS]
```

**Options:**

| Option | Example | Description |
|--------|---------|-------------|
| `-b BRANCH` / `--branch BRANCH` | `-b v2.5.5-dev` | Install from branch or tag |
| `-v VER` / `--version VER` | `-v 2.5.5-dev` | Version (script adds `v` prefix as needed) |
| `--mariadb-version VER` | `--mariadb-version 10.11` | MariaDB: `10.11`, `11.8`, or `12.1` |
| `--auto` | `--auto` | Non-interactive (still asks MariaDB unless `--mariadb-version` is set) |
| `--debug` | `--debug` | Debug mode |

**Examples:**

```bash
sudo bash cyberpanel.sh                              # Interactive
sudo bash cyberpanel.sh -b v2.5.5-dev                # Development branch
sudo bash cyberpanel.sh -v 2.5.5-dev                 # Same as above (v prefix added)
sudo bash cyberpanel.sh -v 2.4.4                     # Install 2.4.4
sudo bash cyberpanel.sh -b main                      # From main branch
sudo bash cyberpanel.sh -b a1b2c3d4                  # From specific commit hash
sudo bash cyberpanel.sh --mariadb-version 10.11      # MariaDB 10.11
sudo bash cyberpanel.sh --mariadb-version 12.1       # MariaDB 12.1
sudo bash cyberpanel.sh --auto --mariadb-version 11.8   # Fully non-interactive, MariaDB 11.8
sudo bash cyberpanel.sh --debug                      # Debug
```

---

## Upgrade (existing CyberPanel)

### One-liner upgrade to latest stable

```bash
bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh)
```

### Upgrade to a specific branch/version (upstream)

```bash
bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b v2.5.5-dev
bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.4.4
```

### Upgrade using master3395 fork

```bash
sudo bash <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh) -b v2.5.5-dev
```

Or download then run:

```bash
curl -sL -o cyberpanel_upgrade.sh https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel_upgrade.sh
chmod +x cyberpanel_upgrade.sh
sudo bash cyberpanel_upgrade.sh -b v2.5.5-dev
```

**Upgrade options:**

| Option | Example | Description |
|--------|---------|-------------|
| `-b BRANCH` / `--branch BRANCH` | `-b v2.5.5-dev` | Upgrade to this branch/tag |
| `--no-system-update` | (optional) | Skip full `yum/dnf update -y` (faster if system is already updated) |

**Examples:**

```bash
sudo bash cyberpanel_upgrade.sh -b v2.5.5-dev
sudo bash cyberpanel_upgrade.sh -b 2.4.4
sudo bash cyberpanel_upgrade.sh -b stable
sudo bash cyberpanel_upgrade.sh -b v2.5.5-dev --no-system-update
```

---

## Downgrade

Downgrade is done by running the **upgrade** script with the **older** branch/version.

### Downgrade to 2.4.4 (or another older version)

```bash
sudo bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.4.4
```

Or with master3395 fork:

```bash
curl -sL -o cyberpanel_upgrade.sh https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh
chmod +x cyberpanel_upgrade.sh
sudo bash cyberpanel_upgrade.sh -b 2.4.4
```

### Downgrade from v2.5.5-dev to stable

```bash
sudo bash cyberpanel_upgrade.sh -b stable
```

---

## Pre-upgrade (download upgrade script only)

From the interactive menu: **Option 5 – Pre-Upgrade**.

Or manually:

```bash
# Download latest upgrade script to /usr/local/
curl -sL -o /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh
chmod 700 /usr/local/cyberpanel_upgrade.sh

# Run when ready
sudo /usr/local/cyberpanel_upgrade.sh -b v2.5.5-dev
```

---

## Quick reference

| Action | Command |
|--------|---------|
| **Install (official)** | `sh <(curl https://cyberpanel.net/install.sh)` |
| **Install stable (master3395)** | `curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel.sh \| sudo bash -s --` |
| **Install v2.5.5-dev** | `curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel.sh \| sudo bash -s -- -b v2.5.5-dev` |
| **Upgrade to v2.5.5-dev** | `sudo bash <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh) -b v2.5.5-dev` |
| **Upgrade to 2.4.4** | `sudo bash <(curl -sL .../cyberpanel_upgrade.sh) -b 2.4.4` |
| **Downgrade to 2.4.4** | Same as upgrade: `... cyberpanel_upgrade.sh -b 2.4.4` |

---

## Notes

- Run as **root** or with **sudo**; if using `curl | sudo bash`, use `bash -s --` and put branch/options after `--` so they are passed to the script.
- MariaDB version can be set at install with `--mariadb-version 10.11`, `11.8`, or `12.1`.
- Upgrade script branch: `-b v2.5.5-dev`, `-b 2.4.4`, `-b stable`, or `-b <commit-hash>`.
