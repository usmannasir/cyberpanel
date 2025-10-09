#!/bin/sh

# Simplified CyberPanel Installation Script
# Based on 2.4.4 approach with AlmaLinux 9 fixes

OUTPUT=$(cat /etc/*release)

# Detect OS and set appropriate variables
if echo $OUTPUT | grep -q "AlmaLinux 9" ; then
    echo -e "\nDetecting AlmaLinux 9...\n"
    SERVER_OS="AlmaLinux9"
    PKG_MGR="dnf"
elif echo $OUTPUT | grep -q "AlmaLinux 8" ; then
    echo -e "\nDetecting AlmaLinux 8...\n"
    SERVER_OS="AlmaLinux8"
    PKG_MGR="yum"
elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
    echo -e "\nDetecting Ubuntu 22.04...\n"
    SERVER_OS="Ubuntu2204"
    PKG_MGR="apt"
elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
    echo -e "\nDetecting Ubuntu 20.04...\n"
    SERVER_OS="Ubuntu2004"
    PKG_MGR="apt"
elif echo $OUTPUT | grep -q "CentOS Linux 8" ; then
    echo -e "\nDetecting CentOS 8...\n"
    SERVER_OS="CentOS8"
    PKG_MGR="yum"
else
    echo -e "\nUnsupported OS detected. This script supports:\n"
    echo -e "AlmaLinux: 8, 9\n"
    echo -e "Ubuntu: 20.04, 22.04\n"
    echo -e "CentOS: 8\n"
    exit 1
fi

echo "Installing basic dependencies..."

# Install basic packages
if [ "$PKG_MGR" = "dnf" ]; then
    dnf update -y
    dnf install -y epel-release
    dnf install -y wget curl unzip zip rsync firewalld git python3 python3-pip
    dnf install -y mariadb-server mariadb-client
    dnf install -y ImageMagick gd libicu oniguruma aspell libc-client
elif [ "$PKG_MGR" = "yum" ]; then
    yum update -y
    yum install -y epel-release
    yum install -y wget curl unzip zip rsync firewalld git python3 python3-pip
    yum install -y mariadb-server mariadb-client
    yum install -y ImageMagick gd libicu oniguruma aspell libc-client
elif [ "$PKG_MGR" = "apt" ]; then
    apt update -y
    apt install -y wget curl unzip zip rsync git python3 python3-pip
    apt install -y mariadb-server mariadb-client
    apt install -y imagemagick php-gd php-intl php-mbstring php-pspell
fi

# Start and enable MariaDB
echo "Starting MariaDB..."
systemctl enable mariadb
systemctl start mariadb

# Create MySQL password file
echo "Setting up MySQL..."
mkdir -p /etc/cyberpanel
echo "cyberpanel123" > /etc/cyberpanel/mysqlPassword
chmod 600 /etc/cyberpanel/mysqlPassword

# Secure MySQL installation
mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'cyberpanel123';" 2>/dev/null || true
mysql -u root -pcyberpanel123 -e "DELETE FROM mysql.user WHERE User='';" 2>/dev/null || true
mysql -u root -pcyberpanel123 -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');" 2>/dev/null || true
mysql -u root -pcyberpanel123 -e "DROP DATABASE IF EXISTS test;" 2>/dev/null || true
mysql -u root -pcyberpanel123 -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';" 2>/dev/null || true
mysql -u root -pcyberpanel123 -e "FLUSH PRIVILEGES;" 2>/dev/null || true

# Configure firewall
echo "Configuring firewall..."
if [ "$PKG_MGR" = "dnf" ] || [ "$PKG_MGR" = "yum" ]; then
    systemctl enable firewalld
    systemctl start firewalld
    firewall-cmd --permanent --add-port=8090/tcp
    firewall-cmd --permanent --add-port=7080/tcp
    firewall-cmd --permanent --add-port=80/tcp
    firewall-cmd --permanent --add-port=443/tcp
    firewall-cmd --permanent --add-port=21/tcp
    firewall-cmd --permanent --add-port=25/tcp
    firewall-cmd --permanent --add-port=587/tcp
    firewall-cmd --permanent --add-port=465/tcp
    firewall-cmd --permanent --add-port=110/tcp
    firewall-cmd --permanent --add-port=143/tcp
    firewall-cmd --permanent --add-port=993/tcp
    firewall-cmd --permanent --add-port=995/tcp
    firewall-cmd --permanent --add-port=53/tcp
    firewall-cmd --permanent --add-port=53/udp
    firewall-cmd --reload
fi

# Download and install CyberPanel
echo "Downloading CyberPanel..."
rm -f cyberpanel.sh
curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null

if [ -f "cyberpanel.sh" ]; then
    echo "Installing CyberPanel..."
    chmod +x cyberpanel.sh
    ./cyberpanel.sh
else
    echo "Failed to download CyberPanel installer!"
    exit 1
fi

echo "Installation completed!"
