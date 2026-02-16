#!/bin/bash
# Install/fix phpMyAdmin under /usr/local/CyberCP/public/phpmyadmin (creates signin + full app)
set -e
PUBLIC=/usr/local/CyberCP/public
PMA_DIR=$PUBLIC/phpmyadmin
VERSION=5.2.3
TARBALL=$PUBLIC/phpmyadmin.tar.gz

echo "[$(date -Iseconds)] Installing phpMyAdmin to $PMA_DIR ..."
sudo mkdir -p "$PUBLIC"
sudo rm -rf "$PMA_DIR"
sudo wget -q -O "$TARBALL" "https://files.phpmyadmin.net/phpMyAdmin/${VERSION}/phpMyAdmin-${VERSION}-all-languages.tar.gz" || { echo "Download failed"; exit 1; }
[ -f "$TARBALL" ] && [ $(stat -c%s "$TARBALL") -gt 1000000 ] || { echo "Tarball missing or too small"; exit 1; }
sudo tar -xzf "$TARBALL" -C "$PUBLIC"
if [ -d "$PUBLIC/phpMyAdmin-${VERSION}-all-languages" ]; then
  sudo mv "$PUBLIC/phpMyAdmin-${VERSION}-all-languages" "$PMA_DIR"
else
  sudo mv "$PUBLIC/phpMyAdmin-"*"-all-languages" "$PMA_DIR" 2>/dev/null || true
fi
sudo rm -f "$TARBALL"

[ -d "$PMA_DIR" ] || { echo "phpmyadmin dir not created"; exit 1; }

# Config: use sample if present, then ensure signon block
BLOWFISH=$(openssl rand -hex 16)
if [ -f "$PMA_DIR/config.sample.inc.php" ]; then
  sudo cp "$PMA_DIR/config.sample.inc.php" "$PMA_DIR/config.inc.php"
  sudo sed -i "s|blowfish_secret.*|blowfish_secret'] = '${BLOWFISH}';|" "$PMA_DIR/config.inc.php" 2>/dev/null || true
fi
sudo bash -c 'cat >> '"$PMA_DIR"'/config.inc.php << "PMACONF"

$i = 0;
$i++;
$cfg["Servers"][$i]["AllowNoPassword"] = false;
$cfg["Servers"][$i]["auth_type"] = "signon";
$cfg["Servers"][$i]["SignonSession"] = "SignonSession";
$cfg["Servers"][$i]["SignonURL"] = "phpmyadminsignin.php";
$cfg["Servers"][$i]["LogoutURL"] = "phpmyadminsignin.php?logout";
$cfg["Servers"][$i]["host"] = "127.0.0.1";
$cfg["Servers"][$i]["port"] = "3306";
$cfg["TempDir"] = "/usr/local/CyberCP/public/phpmyadmin/tmp";
PMACONF'
sudo mkdir -p "$PMA_DIR/tmp"
sudo cp /usr/local/CyberCP/plogical/phpmyadminsignin.php "$PMA_DIR/phpmyadminsignin.php"
sudo chown -R lscpd:lscpd "$PMA_DIR"
echo "[$(date -Iseconds)] phpMyAdmin install done. Test: https://YOUR_IP:2087/phpmyadmin/phpmyadminsignin.php"
exit 0
