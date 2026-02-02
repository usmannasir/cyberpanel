#!/bin/bash
set -e

echo "=== Installing phpMyAdmin for CyberPanel ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit 1
fi

# Define constants
phpmyadmin_version="5.2.3"
dest_dir="/usr/local/CyberCP/public/phpmyadmin"
temp_dir="/tmp"
download_url="https://files.phpmyadmin.net/phpMyAdmin/${phpmyadmin_version}/phpMyAdmin-${phpmyadmin_version}-all-languages.tar.gz"

# Create public directory if it doesn't exist
if [ ! -d "/usr/local/CyberCP/public" ]; then
    mkdir -p "/usr/local/CyberCP/public"
fi

# Remove old installation if exists
if [ -d "$dest_dir" ]; then
    echo "Removing old phpMyAdmin installation..."
    rm -rf "$dest_dir"
fi

# Create phpMyAdmin directory
mkdir -p "$dest_dir"

echo "Downloading phpMyAdmin ${phpmyadmin_version}..."
if ! wget -q -O "${temp_dir}/phpmyadmin.tar.gz" "$download_url"; then
    echo "ERROR: Unable to download phpMyAdmin version ${phpmyadmin_version}"
    exit 1
fi

echo "Extracting phpMyAdmin..."
tar -xzf "${temp_dir}/phpmyadmin.tar.gz" -C "/usr/local/CyberCP/public/"

# Move extracted directory to phpmyadmin
extracted_dir=$(find /usr/local/CyberCP/public -maxdepth 1 -type d -name "phpMyAdmin-*-all-languages" | head -1)
if [ -n "$extracted_dir" ] && [ -d "$extracted_dir" ]; then
    echo "Moving files from $extracted_dir to $dest_dir..."
    mv "$extracted_dir"/* "$dest_dir/" 2>/dev/null || true
    mv "$extracted_dir"/.* "$dest_dir/" 2>/dev/null || true
    rm -rf "$extracted_dir"
fi

# Cleanup
rm -f "${temp_dir}/phpmyadmin.tar.gz"

echo "Configuring phpMyAdmin..."

# Generate random blowfish secret
blowfish_secret=$(openssl rand -hex 16)

# Read config.sample.inc.php and create config.inc.php
if [ ! -f "$dest_dir/config.sample.inc.php" ]; then
    echo "ERROR: config.sample.inc.php not found!"
    exit 1
fi

# Create config.inc.php
cat > "$dest_dir/config.inc.php" << 'EOF'
<?php
/**
 * phpMyAdmin sample configuration, you can use it as base for
 * manual configuration. For easier setup you can use setup.php.
 *
 * All directives are explained in documentation in the doc/ folder
 * or at <https://docs.phpmyadmin.net/>.
 *
 * @package PhpMyAdmin
 */

declare(strict_types=1);

/**
 * This is needed for cookie based authentication to encrypt password in
 * cookie. Needs to be 32 chars long.
 */
$cfg['blowfish_secret'] = 'BLOWFISH_SECRET_PLACEHOLDER'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */

/**
 * Servers configuration
 */
$i = 0;

/**
 * First server
 */
$i++;
/* Authentication type */
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'phpmyadminsignin.php';
$cfg['Servers'][$i]['LogoutURL'] = 'phpmyadminsignin.php?logout';

/* Server parameters */
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = false;

/* Temp directory */
$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';
EOF

# Replace blowfish secret
sed -i "s/BLOWFISH_SECRET_PLACEHOLDER/$blowfish_secret/g" "$dest_dir/config.inc.php"

# Create tmp directory
mkdir -p "$dest_dir/tmp"
mkdir -p "$dest_dir/tmp/twig"

# Copy phpmyadminsignin.php
if [ -f "/usr/local/CyberCP/plogical/phpmyadminsignin.php" ]; then
    cp /usr/local/CyberCP/plogical/phpmyadminsignin.php "$dest_dir/phpmyadminsignin.php"
    echo "Copied phpmyadminsignin.php"
else
    echo "WARNING: phpmyadminsignin.php not found at /usr/local/CyberCP/plogical/phpmyadminsignin.php"
fi

# Update mysqlhost if remote mysql is configured
if [ -f "/etc/cyberpanel/mysqlPassword" ]; then
    mysqlhost=$(python3 -c "import json; data=json.load(open('/etc/cyberpanel/mysqlPassword')); print(data.get('mysqlhost', 'localhost'))" 2>/dev/null || echo "localhost")
    if [ "$mysqlhost" != "localhost" ]; then
        sed -i "s|localhost|$mysqlhost|g" "$dest_dir/phpmyadminsignin.php"
        sed -i "s|'host' => 'localhost'|'host' => '$mysqlhost'|g" "$dest_dir/config.inc.php"
        echo "Updated MySQL host to: $mysqlhost"
    fi
fi

# Set permissions
echo "Setting permissions..."
chown -R lscpd:lscpd "$dest_dir"
find "$dest_dir" -type d -exec chmod 755 {} \;
find "$dest_dir" -type f -exec chmod 644 {} \;
chown -R lscpd:lscpd "$dest_dir/tmp"
chmod 755 "$dest_dir/tmp"

echo ""
echo "=== phpMyAdmin installation completed ==="
echo "Location: $dest_dir"
echo ""
