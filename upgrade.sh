python manage.py collectstatic --no-input
rm -rf /usr/local/CyberCP/public/static/*
cp -R  /usr/local/CyberCP/static/* /usr/local/CyberCP/public/static/
find /usr/local/CyberCP -type d -exec chmod 0755 {} \;
find /usr/local/CyberCP -type f -exec chmod 0644 {} \;
chmod -R 755 /usr/local/CyberCP/bin
chown -R root:root /usr/local/CyberCP
chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp
systemctl restart lscpd
