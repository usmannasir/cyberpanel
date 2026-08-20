#!/usr/bin/env bash
# CyberPanel upgrade – post-upgrade system tweaks (PHP, LSWS, SnappyMail, etc.). Sourced by cyberpanel_upgrade.sh.

Post_Upgrade_System_Tweak() {
  # Cron and upgrade helpers expect /usr/local/CyberCP/bin/python (legacy CyberPanel venv path may be missing).
  if [[ ! -x /usr/local/CyberCP/bin/python ]]; then
    mkdir -p /usr/local/CyberCP/bin
    _py="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
    if [[ -n "$_py" && -x "$_py" ]]; then
      ln -sfn "$_py" /usr/local/CyberCP/bin/python
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restored /usr/local/CyberCP/bin/python -> $_py" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
  fi

  if [[ "$Server_OS" = "CentOS" ]] ; then

  #for CentOS 8+
    if [[ "$Server_OS_Version" = "8" ]] ; then
    :
    #for centos 8
    fi
  fi

  if [[ "$Server_OS" = "Ubuntu" ]] ; then

  if ! dpkg -l lsphp74-dev >/dev/null 2>&1 ; then
    apt install -y lsphp74-dev
  fi

    if [[ ! -f /usr/sbin/ipset ]] ; then
    ln -s /sbin/ipset /usr/sbin/ipset
    fi

  #for ubuntu 18/20
    if [[ "$Server_OS_Version" = "18" ]] ; then
    :
    #for ubuntu 18
    elif [[ "$Server_OS_Version" = "20" ]] ; then
    :
    #for ubuntu 20
    fi
  fi

sed -i "s|lsws-5.3.8|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.4.2|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-5.3.5|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-6.0|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py
sed -i "s|lsws-6.3.4|lsws-$LSWS_Stable_Version|g" /usr/local/CyberCP/serverStatus/serverStatusUtil.py

if [[ "$Server_Country" = "CN" ]] ; then
  sed -i 's|https://www.litespeedtech.com/|https://cyberpanel.sh/www.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
  sed -i 's|http://license.litespeedtech.com/|https://cyberpanel.sh/license.litespeedtech.com/|g' /usr/local/CyberCP/serverStatus/serverStatusUtil.py
fi

# Admin CLI wrapper (password stored under /etc/cyberpanel/adminPass; do not sed a missing file).
cat >/usr/bin/adminPass <<'EOF'
/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py --password "$@"
systemctl restart lscpd
echo "$@" > /etc/cyberpanel/adminPass
EOF
chmod 700 /usr/bin/adminPass

# Point /usr/bin/php at an lsphp that is actually installed, preferring the
# default CLI version (8.3, matching upgrade.py/install.py) and falling back to
# whatever is present. This block previously hardcoded lsphp74 unconditionally,
# so on servers without PHP 7.4 it replaced a working symlink with a broken one
# and `php -v` failed with "command not found". (#1727)
rm -f /usr/bin/php
for _php_ver in 83 84 85 82 81 80 74; do
  if [ -x "/usr/local/lsws/lsphp${_php_ver}/bin/php" ]; then
    ln -s "/usr/local/lsws/lsphp${_php_ver}/bin/php" /usr/bin/php
    break
  fi
done

if [[ -f /etc/cyberpanel/webadmin_passwd ]]; then
  chmod 600 /etc/cyberpanel/webadmin_passwd
fi

chown lsadm:lsadm /usr/local/lsws/admin/conf/htpasswd
chmod 600 /usr/local/lsws/admin/conf/htpasswd

if [[ -f /etc/pure-ftpd/pure-ftpd.conf ]]; then
  sed -i 's|NoAnonymous                 no|NoAnonymous                 yes|g' /etc/pure-ftpd/pure-ftpd.conf
fi

Tmp_Output=$(timeout 3 openssl s_client -connect 127.0.0.1:8090 2>/dev/null)
if echo "$Tmp_Output" | grep -q "mail@example.com" ; then
  # it is using default installer generated cert
  Regenerate_Cert 8090
fi


Tmp_Output=$(timeout 3 openssl s_client -connect 127.0.0.1:7080 2>/dev/null)
if echo "$Tmp_Output" | grep -q "mail@example.com" ; then
  Regenerate_Cert 7080
fi

if [[ ! -f /usr/bin/cyberpanel_utility ]]; then
  wget -q -O /usr/bin/cyberpanel_utility https://cyberpanel.sh/misc/cyberpanel_utility.sh
  chmod 700 /usr/bin/cyberpanel_utility
fi

if [[ -f /usr/local/CyberCP/scripts/utils/cyberpanel-utils.sh ]]; then
  chmod 755 /usr/local/CyberCP/scripts/utils/cyberpanel-utils.sh 2>/dev/null || true
  ln -sf /usr/local/CyberCP/scripts/utils/cyberpanel-utils.sh /usr/local/bin/cyberpanel-utils 2>/dev/null || true
fi

if [[ -f /etc/cyberpanel/watchdog.sh ]] ; then
	watchdog kill
	rm -f /etc/cyberpanel/watchdog.sh
	rm -f /usr/local/bin/watchdog
	wget -O /etc/cyberpanel/watchdog.sh "${Git_Content_URL}/${Branch_Name}/CPScripts/watchdog.sh"
	chmod 700 /etc/cyberpanel/watchdog.sh
	ln -s /etc/cyberpanel/watchdog.sh /usr/local/bin/watchdog
	watchdog status
fi


rm -f /usr/local/composer.sh
if [[ -f /usr/local/requirments.txt ]]; then
  cp -f /usr/local/requirments.txt "/usr/local/requirments.txt.last_post_tweak.$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
fi

chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib64

# Fix missing lsphp binary in /usr/local/lscp/fcgi-bin/ after upgrade
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking and restoring lsphp binary if missing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp ]] || [[ ! -s /usr/local/lscp/fcgi-bin/lsphp ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary missing or empty, attempting to restore..." | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Ensure fcgi-bin directory exists
    mkdir -p /usr/local/lscp/fcgi-bin

    # Find the latest available PHP version and use it
    PHP_RESTORED=0
    
    # Try to find the latest lsphp version (check from newest to oldest)
    # Priority: 85 (beta), 84, 83, 82, 81, 80, 74
    for PHP_VER in 85 84 83 82 81 80 74; do
        if [[ -f /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp ]]; then
            # Try to create symlink first (preferred)
            if ln -sf /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp /usr/local/lscp/fcgi-bin/lsphp 2>/dev/null; then
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp symlink created from lsphp${PHP_VER}" | tee -a /var/log/cyberpanel_upgrade_debug.log
            else
                # If symlink fails, copy the file
                cp -f /usr/local/lsws/lsphp${PHP_VER}/bin/lsphp /usr/local/lscp/fcgi-bin/lsphp
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary copied from lsphp${PHP_VER}" | tee -a /var/log/cyberpanel_upgrade_debug.log
            fi
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            PHP_RESTORED=1
            break
        fi
    done

    # If no lsphp version found, try php binary as fallback
    if [[ $PHP_RESTORED -eq 0 ]]; then
        for PHP_VER in 83 82 81 80 74 73 72; do
            if [[ -f /usr/local/lsws/lsphp${PHP_VER}/bin/php ]]; then
                # Try to create symlink first (preferred)
                if ln -sf /usr/local/lsws/lsphp${PHP_VER}/bin/php /usr/local/lscp/fcgi-bin/lsphp 2>/dev/null; then
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp symlink created from php${PHP_VER} (lsphp fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
                else
                    # If symlink fails, copy the file
                    cp -f /usr/local/lsws/lsphp${PHP_VER}/bin/php /usr/local/lscp/fcgi-bin/lsphp
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary copied from php${PHP_VER} (lsphp fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
                fi
                chown root:root /usr/local/lscp/fcgi-bin/lsphp
                chmod 755 /usr/local/lscp/fcgi-bin/lsphp
                PHP_RESTORED=1
                break
            fi
        done
    fi
    
    # If no lsphp version found, try admin_php5 as fallback
    if [[ $PHP_RESTORED -eq 0 ]]; then
        if [[ -f /usr/local/lscp/admin/fcgi-bin/admin_php5 ]]; then
            cp -f /usr/local/lscp/admin/fcgi-bin/admin_php5 /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from admin_php5 (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        elif [[ -f /usr/local/lscp/admin/fcgi-bin/admin_php ]]; then
            cp -f /usr/local/lscp/admin/fcgi-bin/admin_php /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from admin_php (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        elif [[ -f /usr/local/lsws/admin/fcgi-bin/admin_php5 ]]; then
            cp -f /usr/local/lsws/admin/fcgi-bin/admin_php5 /usr/local/lscp/fcgi-bin/lsphp
            chown root:root /usr/local/lscp/fcgi-bin/lsphp
            chmod 755 /usr/local/lscp/fcgi-bin/lsphp
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lsphp binary restored from lsws admin_php5 (fallback)" | tee -a /var/log/cyberpanel_upgrade_debug.log
        else
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Could not find any PHP binary to restore lsphp" | tee -a /var/log/cyberpanel_upgrade_debug.log
        fi
    fi
    
    # Create symlinks if they don't exist
    if [[ -f /usr/local/lscp/fcgi-bin/lsphp ]]; then
        if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp4 ]]; then
            ln -sf ./lsphp /usr/local/lscp/fcgi-bin/lsphp4
        fi
        if [[ ! -f /usr/local/lscp/fcgi-bin/lsphp5 ]]; then
            ln -sf ./lsphp /usr/local/lscp/fcgi-bin/lsphp5
        fi
    fi
fi

# Fix missing lscpd binary in /usr/local/lscp/bin/ after upgrade
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking and restoring lscpd binary if missing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ ! -f /usr/local/lscp/bin/lscpd ]] || [[ ! -s /usr/local/lscp/bin/lscpd ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary missing or empty, attempting to restore..." | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Ensure lscp bin directory exists
    mkdir -p /usr/local/lscp/bin

    # Select the correct lscpd binary based on OS and version
    lscpd_selection='lscpd-0.3.1'

    # Check if this is an ARM system
    if uname -a | grep -q 'aarch64'; then
        lscpd_selection='lscpd.aarch64'
    else
        # For x86_64 systems, check Ubuntu version
        if [[ "$Server_OS" = "Ubuntu" ]] && [[ -f /etc/lsb-release ]]; then
            ubuntu_version=$(grep 'DISTRIB_RELEASE' /etc/lsb-release | cut -d'=' -f2 | cut -d'.' -f1)
            if [[ "$ubuntu_version" = "22" ]] || [[ "$ubuntu_version" = "24" ]] || [[ "$ubuntu_version" = "26" ]]; then
                lscpd_selection='lscpd.0.4.0'
            fi
        fi
    fi

    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Selected lscpd binary: $lscpd_selection" | tee -a /var/log/cyberpanel_upgrade_debug.log

    # Copy the selected binary from CyberCP to lscp bin
    if [[ -f /usr/local/CyberCP/${lscpd_selection} ]]; then
        cp -f /usr/local/CyberCP/${lscpd_selection} /usr/local/lscp/bin/${lscpd_selection}
        rm -f /usr/local/lscp/bin/lscpd
        mv /usr/local/lscp/bin/${lscpd_selection} /usr/local/lscp/bin/lscpd
        chmod 755 /usr/local/lscp/bin/lscpd
        chown root:root /usr/local/lscp/bin/lscpd
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary restored successfully from ${lscpd_selection}" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Could not find lscpd source binary ${lscpd_selection} in /usr/local/CyberCP/" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] lscpd binary exists and is valid" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] || [[ "$Server_OS_Version" = "18" ]] || [[ "$Server_OS_Version" = "8" ]] || [[ "$Server_OS_Version" = "20" ]] || [[ "$Server_OS_Version" = "24" ]] || [[ "$Server_OS_Version" = "26" ]]; then
    if declare -F CyberCP_Write_Lscp_Pythonenv_Conf >/dev/null 2>&1; then
      CyberCP_Write_Lscp_Pythonenv_Conf
    else
      echo "PYTHONHOME=/usr" > /usr/local/lscp/conf/pythonenv.conf
    fi
    # Mirror requirements into system Python for lswsgi (PEP 668 aware). The helper is defined in
    # upgrade_modules/08_main_upgrade.sh and is idempotent; pip --ignore-installed re-resolves
    # already-installed packages without harm. Backported from upstream cyberpanel 13c0697.
    if declare -F Install_CyberCP_Runtime_Python_Requirements >/dev/null 2>&1; then
        mkdir -p /etc/cyberpanel
        if [[ -f /usr/local/requirments.txt ]]; then
            cp -f /usr/local/requirments.txt /etc/cyberpanel/cyberpanel-requirments-runtime.txt 2>/dev/null || true
        fi
        Install_CyberCP_Runtime_Python_Requirements "/etc/cyberpanel/cyberpanel-requirments-runtime.txt" || true
    fi
  else
    # Uncomment and use the following lines if necessary for other OS versions
    # rsync -av --ignore-existing /usr/lib64/python3.9/ /usr/local/CyberCP/lib64/python3.9/
    # Check_Return
    :
fi

# Fix SnappyMail directory permissions for Ubuntu 24.04 and other systems
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking SnappyMail directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# If public web app is still named rainloop, rename to snappymail so /snappymail/ URL works
if [ -d "/usr/local/CyberCP/public/rainloop" ] && [ ! -d "/usr/local/CyberCP/public/snappymail" ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Renaming public/rainloop to public/snappymail..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    mv /usr/local/CyberCP/public/rainloop /usr/local/CyberCP/public/snappymail
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Renamed public/rainloop -> public/snappymail" | tee -a /var/log/cyberpanel_upgrade_debug.log
    # Update data path in app config so it uses snappymail data dir
    if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Updated include.php to use snappymail data path" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    # Update version-specific include.php (may be under snappymail/v/ or rainloop/v/ after rename)
    for inc in /usr/local/CyberCP/public/snappymail/snappymail/v/*/include.php /usr/local/CyberCP/public/snappymail/rainloop/v/*/include.php; do
        [ -f "$inc" ] && sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' "$inc" && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Updated $inc" | tee -a /var/log/cyberpanel_upgrade_debug.log && break
    done 2>/dev/null
fi

# Migrate data from old rainloop folder to new snappymail folder (2.4.4 -> 2.5.5 upgrade)
if [ -d "/usr/local/lscp/cyberpanel/rainloop/data" ] && [ "$(ls -A /usr/local/lscp/cyberpanel/rainloop/data 2>/dev/null)" ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Migrating rainloop data to snappymail..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Check if snappymail data already exists with content
    if [ -d "/usr/local/lscp/cyberpanel/snappymail/data" ] && [ -d "/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] SnappyMail data already exists, skipping migration" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        # Create SnappyMail data directories if they don't exist
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/
        mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/
        
        # Migrate data using rsync (preserves permissions and ownership)
        rsync -av --ignore-existing /usr/local/lscp/cyberpanel/rainloop/data/ /usr/local/lscp/cyberpanel/snappymail/data/ 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
        
        if [ $? -eq 0 ]; then
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Successfully migrated rainloop data to snappymail" | tee -a /var/log/cyberpanel_upgrade_debug.log
            
            # Update include.php to use snappymail path
            if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
                sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Updated include.php to use snappymail data path" | tee -a /var/log/cyberpanel_upgrade_debug.log
            fi
            
            # Replace ALL rainloop path/URL references in migrated SnappyMail data (configs, domains, plugins)
            if [ -d "/usr/local/lscp/cyberpanel/snappymail/data" ]; then
                find /usr/local/lscp/cyberpanel/snappymail/data -type f \( -name "*.ini" -o -name "*.json" -o -name "*.php" -o -name "*.cfg" \) -exec grep -l "rainloop" {} \; 2>/dev/null | while read -r f; do
                    sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g; s|/rainloop/|/snappymail/|g; s|rainloop/data|snappymail/data|g' "$f"
                done
                echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Replaced rainloop→snappymail links in SnappyMail data files" | tee -a /var/log/cyberpanel_upgrade_debug.log
            fi
        else
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Data migration completed with errors" | tee -a /var/log/cyberpanel_upgrade_debug.log
        fi
    fi
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] No old rainloop data found, creating new SnappyMail directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Create SnappyMail data directories if they don't exist
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/
    mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/
fi

# Ensure proper ownership for SnappyMail data directories (rainloop + snappymail)
ENSURE_SNAPPY="/usr/local/CyberCP/scripts/utils/ensure-snappymail-permissions.sh"
if [[ -x "$ENSURE_SNAPPY" ]]; then
    bash "$ENSURE_SNAPPY" || true
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ran ensure-snappymail-permissions.sh" | tee -a /var/log/cyberpanel_upgrade_debug.log
elif id -u lscpd >/dev/null 2>&1; then
    chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/ 2>/dev/null || true
    chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set SnappyMail ownership to lscpd:lscpd" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: lscpd user not found, skipping ownership change" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Remove leftover RainLoop-era domain .ini when a matching .json exists.
# Dual configs confuse operators; SnappyMail prefers .json (localhost:143 STARTTLS).
DOMAINS_DIR="/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains"
DOMAINS_BAK="/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains.bak"
if [ -d "$DOMAINS_DIR" ]; then
    mkdir -p "$DOMAINS_BAK"
    ts="$(date +%Y%m%d-%H%M%S)"
    for jsonf in "$DOMAINS_DIR"/*.json; do
        [ -f "$jsonf" ] || continue
        base="$(basename "$jsonf" .json)"
        inif="$DOMAINS_DIR/${base}.ini"
        if [ -f "$inif" ]; then
            cp -a "$inif" "$DOMAINS_BAK/${base}.ini.$ts"
            rm -f "$inif"
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removed conflicting SnappyMail domain .ini (backed up): ${base}.ini" | tee -a /var/log/cyberpanel_upgrade_debug.log
        fi
    done
fi

# Ensure /rainloop→/snappymail redirect exists (even when no migration ran)
HTACCESS="/usr/local/CyberCP/public/.htaccess"
if [ -d "/usr/local/CyberCP/public" ] && { [ ! -f "$HTACCESS" ] || ! grep -q "Redirect old RainLoop URL to SnappyMail" "$HTACCESS" 2>/dev/null; }; then
    {
        echo ""
        echo "# Redirect old RainLoop URL to SnappyMail (2.5.5 upgrade)"
        echo "<IfModule mod_rewrite.c>"
        echo "RewriteEngine On"
        echo "RewriteRule ^rainloop/?(.*)\$ /snappymail/\$1 [R=301,L]"
        echo "</IfModule>"
    } >> "$HTACCESS"
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Added /rainloop→/snappymail redirect to .htaccess" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Set proper permissions for SnappyMail data directories (group writable)
chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data/
chmod -R 775 /usr/local/lscp/cyberpanel/rainloop/data/ 2>/dev/null || true
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set SnappyMail data directory permissions to 775 (group writable)" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Ensure web server users are in the lscpd group for access
usermod -a -G lscpd nobody 2>/dev/null || true

# Fix SnappyMail public directory ownership (critical fix)
chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/data 2>/dev/null || true
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Added web server users to lscpd group and fixed SnappyMail ownership" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Force phpMyAdmin to use 127.0.0.1 (TCP) so it shows the same MariaDB version as CLI (main instance on 3306)
if [ -f /usr/local/CyberCP/public/phpmyadmin/config.inc.php ]; then
  if ! grep -q "\$cfg\['Servers'\]\[\$i\]\['host'\] = '127.0.0.1'" /usr/local/CyberCP/public/phpmyadmin/config.inc.php 2>/dev/null; then
    sed -i "/SignonURL/a \$cfg['Servers'][\$i]['host'] = '127.0.0.1';\n\$cfg['Servers'][\$i]['port'] = '3306';" /usr/local/CyberCP/public/phpmyadmin/config.inc.php 2>/dev/null || true
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set phpMyAdmin server host to 127.0.0.1" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
fi
if [ -f /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php ]; then
  sed -i "/trim.*\$_POST.*host.*localhost/s/'localhost'/'127.0.0.1'/g" /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php 2>/dev/null || true
  grep -q "127.0.0.1" /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php && echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] phpMyAdmin signon default host set to 127.0.0.1" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Validate phpMyAdmin web entrypoint after upgrade and self-heal if missing.
if [ ! -f /usr/local/CyberCP/public/phpmyadmin/index.php ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: phpMyAdmin index.php missing after upgrade, attempting repair..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  PMA_FIX="/usr/local/CyberCP/scripts/utils/fix-phpmyadmin.sh"
  [[ -x "$PMA_FIX" ]] || PMA_FIX="/usr/local/CyberCP/fix-phpmyadmin.sh"
  if [ -x "$PMA_FIX" ]; then
    bash "$PMA_FIX" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  elif [ -x /usr/local/CyberCP/bin/python ]; then
    export DJANGO_SETTINGS_MODULE=CyberCP.settings
    /usr/local/CyberCP/bin/python -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.upgrade import Upgrade; Upgrade.download_install_phpmyadmin()" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  else
    python3 -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.upgrade import Upgrade; Upgrade.download_install_phpmyadmin()" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  fi

  if [ -f /usr/local/CyberCP/public/phpmyadmin/index.php ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] phpMyAdmin repair completed successfully (index.php restored)." | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: phpMyAdmin repair did not restore index.php. Run: cyberpanel-utils.sh run fix-phpmyadmin (or /usr/local/CyberCP/scripts/utils/fix-phpmyadmin.sh)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
fi

# Validate SnappyMail web app after upgrade and self-heal if missing.
# OLS CyberPanel vhost uses restrained=1: a symlink from public/snappymail to
# /usr/local/lscp/... yields Not Found (request falls through to Django).
if [ -L /usr/local/CyberCP/public/snappymail ] || [ ! -f /usr/local/CyberCP/public/snappymail/index.php ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: SnappyMail app tree missing or symlinked outside vhRoot, attempting repair..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  SNAP_FIX="/usr/local/CyberCP/scripts/utils/fix-snappymail.sh"
  [[ -x "$SNAP_FIX" ]] || SNAP_FIX="/usr/local/CyberCP/fix-snappymail.sh"
  if [ -x "$SNAP_FIX" ]; then
    bash "$SNAP_FIX" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  elif [ -x /usr/local/CyberCP/bin/python ]; then
    export DJANGO_SETTINGS_MODULE=CyberCP.settings
    /usr/local/CyberCP/bin/python -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols; ensure_cyberpanel_phpmyadmin_ols(restart=True)" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
    /usr/local/CyberCP/bin/python -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.upgrade import Upgrade; Upgrade.downoad_and_install_raindloop()" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  else
    python3 -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols; ensure_cyberpanel_phpmyadmin_ols(restart=True)" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
    python3 -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.upgrade import Upgrade; Upgrade.downoad_and_install_raindloop()" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  fi

  if [ ! -L /usr/local/CyberCP/public/snappymail ] && [ -f /usr/local/CyberCP/public/snappymail/index.php ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] SnappyMail repair completed successfully (real index.php under public/)." | tee -a /var/log/cyberpanel_upgrade_debug.log
    chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail 2>/dev/null || true
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: SnappyMail repair did not restore a real public/snappymail tree. Run: bash /usr/local/CyberCP/scripts/utils/fix-snappymail.sh" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
fi

# Panel /webmail/ needs /static/webmail/webmail.js and webmail.css. If they are missing, Django serves HTML 404 as text/html and the Angular UI shows raw {$ ... $} placeholders.
if [ ! -f /usr/local/CyberCP/static/webmail/webmail.js ] || [ ! -f /usr/local/CyberCP/public/static/webmail/webmail.js ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Webmail static assets missing; checking Django before collectstatic..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  if [ -x /usr/local/CyberCP/bin/python ] && /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running collectstatic and panel_static_sync..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    (
      cd /usr/local/CyberCP && export DJANGO_SETTINGS_MODULE=CyberCP.settings
      /usr/local/CyberCP/bin/python manage.py collectstatic --noinput 2>&1
      /usr/local/CyberCP/bin/python -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.panel_static_sync import ensure_litespeed_panel_static_complete; ensure_litespeed_panel_static_complete()" 2>&1
    ) | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  elif command -v python3 >/dev/null 2>&1 && python3 -c "import django" 2>/dev/null; then
    (
      cd /usr/local/CyberCP && export DJANGO_SETTINGS_MODULE=CyberCP.settings
      python3 manage.py collectstatic --noinput 2>&1
      python3 -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.panel_static_sync import ensure_litespeed_panel_static_complete; ensure_litespeed_panel_static_complete()" 2>&1
    ) | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Skipping collectstatic: Django not importable yet. Run pip install -r /usr/local/requirments.txt then collectstatic." | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  if [ -f /usr/local/CyberCP/static/webmail/webmail.js ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Webmail static repair finished (STATIC_ROOT and public/static webmail present)." | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Webmail static repair failed. Run: cd /usr/local/CyberCP && DJANGO_SETTINGS_MODULE=CyberCP.settings python3 manage.py collectstatic --noinput" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
fi

# FTP users table: custom quota columns (fixes 1054 on Create FTP Account if schema predates model fields)
if [[ -f /usr/local/CyberCP/CPScripts/ensure_ftp_users_quota_columns.py ]]; then
  if [[ -x /usr/local/CyberCP/bin/python ]]; then
    CP_DIR=/usr/local/CyberCP /usr/local/CyberCP/bin/python /usr/local/CyberCP/CPScripts/ensure_ftp_users_quota_columns.py /usr/local/CyberCP 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  else
    CP_DIR=/usr/local/CyberCP python3 /usr/local/CyberCP/CPScripts/ensure_ftp_users_quota_columns.py /usr/local/CyberCP 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ran ensure_ftp_users_quota_columns (FTP users table custom quota columns)" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] INFO: ensure_ftp_users_quota_columns.py not in CyberCP yet; run: cyberpanel-utils.sh run deploy-ftp-users-custom-quota-columns" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Gunicorn timeout drop-in and backend restart so workers use the new venv (after pip in Main_Upgrade).
CyberPanel_Write_Cyberpanel_Gunicorn_Dropin() {
  local DROPIN_DIR=/etc/systemd/system/cyberpanel.service.d
  mkdir -p "$DROPIN_DIR"
  cat > "$DROPIN_DIR/timeout.conf" <<'EOF'
# Managed by CyberPanel upgrade (upgrade_modules/10_post_tweak.sh). Sane gunicorn timeouts.
[Service]
ExecStart=
ExecStart=/usr/local/CyberCP/bin/gunicorn \
          --pid /run/gunicorn/gucpid \
          --timeout 120 \
          --graceful-timeout 30 \
          --workers 2 \
          --bind 127.0.0.1:5003 \
          --access-logfile /var/log/gunicorn-access.log \
          --error-logfile  /var/log/gunicorn-error.log \
          CyberCP.wsgi
EOF
  systemctl daemon-reload 2>/dev/null || true
}

CyberPanel_Restart_Backend_And_Openlitespeed() {
  CyberPanel_Write_Cyberpanel_Gunicorn_Dropin
  systemctl daemon-reload 2>/dev/null || true
  if systemctl cat cyberpanel.service >/dev/null 2>&1; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restarting cyberpanel.service (gunicorn)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    systemctl restart cyberpanel.service 2>/dev/null || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: cyberpanel.service restart failed" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  if [[ -x /usr/local/lsws/bin/lswsctrl ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restarting OpenLiteSpeed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    /usr/local/lsws/bin/lswsctrl restart 2>/dev/null || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: lswsctrl restart returned non-zero" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
}

# OLS :8090 vhost — public/static path, phpMyAdmin, SnappyMail, Imunify UI contexts.
if [ -x /usr/local/CyberCP/CPScripts/fix-cyberpanel-phpmyadmin-ols.sh ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ensuring CyberPanel OLS vhost (static/phpmyadmin/imunify)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  bash /usr/local/CyberCP/CPScripts/fix-cyberpanel-phpmyadmin-ols.sh --restart 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
elif [ -x /usr/local/CyberCP/bin/python ]; then
  export DJANGO_SETTINGS_MODULE=CyberCP.settings
  /usr/local/CyberCP/bin/python -c "import sys; sys.path.insert(0, '/usr/local/CyberCP'); from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols; ensure_cyberpanel_phpmyadmin_ols(restart=True, verify=False)" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
fi

# ImunifyAV/360 — repair integration.conf when CLScript hooks are missing (GitHub #1825).
if [ -f /etc/sysconfig/imunify360/integration.conf ] && [ -x /usr/local/CyberCP/bin/python ]; then
  export DJANGO_SETTINGS_MODULE=CyberCP.settings
  /usr/local/CyberCP/bin/python -c "
import sys
sys.path.insert(0, '/usr/local/CyberCP')
from plogical.imunify_integration import (
    integration_conf_needs_repair, repair_integration_conf,
    ensure_install_status_file, ensure_clscripts_executable,
    chmod_imunify_execute_files, IMUNIFY_AV_UI, IMUNIFY_360_UI,
)
ensure_install_status_file()
ensure_clscripts_executable()
if integration_conf_needs_repair():
    repair_integration_conf()
chmod_imunify_execute_files(IMUNIFY_AV_UI)
chmod_imunify_execute_files(IMUNIFY_360_UI)
" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
fi

CyberPanel_Restart_Backend_And_Openlitespeed

# Harden lscpd sudo privileges (replace broad sudo access with allowlisted wrappers)
if declare -f Post_Upgrade_LSCPD_Sudo_Hardening >/dev/null 2>&1; then
  Post_Upgrade_LSCPD_Sudo_Hardening || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: LSCPD sudo hardening skipped (helpers missing on this branch)" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

if [[ -x /usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh ]]; then
  /usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: fastapi_ssh hardening verify failed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

if [[ -x /usr/local/CyberCP/scripts/security/harden-firewall-8888.sh ]]; then
  bash /usr/local/CyberCP/scripts/security/harden-firewall-8888.sh || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: harden-firewall-8888 failed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

if [[ -x /usr/local/CyberCP/CPScripts/ensure-cyberpanel-apache-permissions.sh ]]; then
  bash /usr/local/CyberCP/CPScripts/ensure-cyberpanel-apache-permissions.sh || echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARN: ensure-cyberpanel-apache-permissions failed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# Ensure dark-mode CSS stack and mailServer.js reach public/static after every upgrade
UI_SYNC="/usr/local/CyberCP/scripts/utils/sync-panel-ui-static.sh"
if [[ -x "$UI_SYNC" ]]; then
  bash "$UI_SYNC" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Post-upgrade UI static sync completed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

# OLS owns public :8090 and proxies to 127.0.0.1:5003. Stock bind.conf is *:8090,
# which makes lscpd race OLS for the same socket after upgrade.
if [[ -d /usr/local/lscp/conf ]]; then
  echo '127.0.0.1:5003' > /usr/local/lscp/conf/bind.conf
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Set lscpd bind.conf to 127.0.0.1:5003" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi
systemctl restart lscpd

}
