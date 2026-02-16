# phpMyAdmin 404 After Upgrade

## Symptom

After upgrading with:

```bash
sh <(curl -s https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.5.5-dev/preUpgrade.sh ...) -b v2.5.5-dev --mariadb-version 11.8
```

opening **https://YOUR_IP:2087/phpmyadmin/** (or the panel’s “phpMyAdmin” link) returns **404 Not Found**.

## Cause

The upgrade step that installs phpMyAdmin (`download_install_phpmyadmin`) can fail without stopping the upgrade (e.g. network, or extract/mv path mismatch). The panel then has no `/usr/local/CyberCP/public/phpmyadmin/` directory, so the web server returns 404 for `/phpmyadmin/`.

## Fix on the server

Run the fix script **as root** on the panel server (e.g. 207.180.193.210):

```bash
# From the repo (if you have it on the server):
cd /home/cyberpanel-repo
sudo bash fix-phpmyadmin.sh

# Or one-liner (download and run from repo):
sudo bash -c 'curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/fix-phpmyadmin.sh | bash'
```

Or run the same logic via Python:

```bash
sudo /usr/local/CyberCP/bin/python -c "
import sys; sys.path.insert(0, '/usr/local/CyberCP')
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
from plogical.upgrade import Upgrade
Upgrade.download_install_phpmyadmin()
"
sudo chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin
```

Then reload **https://YOUR_IP:2087/phpmyadmin/** (or use Databases → phpMyAdmin in the panel).

## Repo changes

- **fix-phpmyadmin.sh** – Script to install/fix phpMyAdmin on the server (run as root).
- **plogical/upgrade.py** – `download_install_phpmyadmin()`:
  - Resolves extracted folder with `glob` (handles `phpMyAdmin-*-all-languages` or `phpMyAdmin-*`).
  - Verifies that `public/phpmyadmin` exists after install and raises if missing so the upgrade step is not silent.
