import os
import subprocess
import sys
sys.path.append('/usr/local/CyberCP')
from plogical.filesPermsUtilities import chown, chmod_digit, mkdir_p, touch, symlink, recursive_chown, recursive_permissions

mkdir_p('/etc/letsencrypt/live/')
mkdir_p('/usr/local/lscp/modsec')

mysql_my_root_cnf = '/root/.my.cnf'
chmod_digit(mysql_my_root_cnf, 600)
chown(mysql_my_root_cnf, 'root', 'root')

recursive_permissions('/usr/local/CyberCP', 755, 644)

recursive_permissions('/usr/local/CyberCP/bin', 755, 755)

## change owner

recursive_chown('/usr/local/CyberCP', 'root', 'root')

########### Fix LSCPD

recursive_permissions('/usr/local/lscp', 755, 644)
recursive_permissions('/usr/local/lscp/bin', 755, 755)
recursive_permissions('/usr/local/lscp/fcgi-bin', 755, 755)
recursive_chown('/usr/local/CyberCP/public/phpmyadmin/tmp', 'lscpd', 'lscpd')

## change owner
recursive_chown('/usr/local/lscp', 'root', 'root')
recursive_chown('/usr/local/lscp/cyberpanel/rainloop/data', 'lscpd', 'lscpd')

chmod_digit('/usr/local/CyberCP/cli/cyberPanel.py', 700)
chmod_digit('/usr/local/CyberCP/plogical/upgradeCritical.py', 700)
chmod_digit('/usr/local/CyberCP/postfixSenderPolicy/client.py', 755)
chmod_digit('/usr/local/CyberCP/CyberCP/settings.py', 640)
chown('/usr/local/CyberCP/CyberCP/settings.py', 'root', 'cyberpanel')

files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
         '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
         '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
         '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
         '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

for items in files:
    chmod_digit(items, 644)

impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
           '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
           '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
           '/etc/powerdns/pdns.conf']

for items in impFile:
    chmod_digit(items, 600)

# chmod_digit(items, 640) hmm looks like we need to glob for this?
command = 'chmod 640 /etc/postfix/*.cf'
subprocess.call(command, shell=True)

chmod_digit('/etc/postfix/main.cf', 644)

command = 'chmod 640 /etc/dovecot/*.conf'
subprocess.call(command, shell=True)

chmod_digit('/etc/dovecot/dovecot.conf', 644)
chmod_digit('/etc/dovecot/dovecot-sql.conf.ext', 640)
chmod_digit('/etc/postfix/dynamicmaps.cf', 644)

chmod_digit('/etc/pure-ftpd/', 755)
chmod_digit('/usr/local/CyberCP/plogical/renew.py', 775)
chmod_digit('/usr/local/CyberCP/CLManager/CLPackages.py', 775)

clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
             '/usr/local/CyberCP/CLScript/CloudLinuxDB.py',
             '/usr/local/CyberCP/CLScript/UserInfo.py']

for items in clScripts:
    chmod_digit(items, 775)

chmod_digit('/usr/local/CyberCP/plogical/adminPass.py', 600)
chmod_digit('/etc/cagefs/exclude/cyberpanelexclude', 600)

# if self.distro == cent8 or self.distro == centos:
#     chown('/etc/pdns/pdns.conf', 'root', 'pdns')
#     chmod_digit('/etc/pdns/pdns.conf', 640)

chmod_digit('/usr/local/lscp/cyberpanel/logs/access.log', 640)

mkdir_p('/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/')
rainloopinipath = '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/application.ini'

os.mkdir('/usr/local/CyberCP/public/phpmyadmin/tmp')

command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin'

# Create Sieve files and paths
os.makedirs("/etc/dovecot/sieve/global", exist_ok=True)

sievefiles = [
    '/var/log/dovecot-lda.log'
    '/var/log/dovecot-lda-errors.log',
    '/var/log/dovecot-sieve.log',
    '/var/log/dovecot-sieve-errors.log',
    '/var/log/dovecot-lmtp.log',
    '/var/log/dovecot-lmtp-errors.log',
]

for file in sievefiles:
    touch(file, 666)
    chown(file, 'vmail', 'mail')

recursive_chown('/etc/dovecot/sieve', 'vmail')

mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
main = "/etc/postfix/main.cf"
master = "/etc/postfix/master.cf"
dovecot = "/etc/dovecot/dovecot.conf"
dovecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"

email_configs = [
    mysql_virtual_domains,
    mysql_virtual_forwardings,
    mysql_virtual_mailboxes,
    mysql_virtual_email2email,
    main,
    master,
    dovecot,
    dovecotmysql,
]

######################################## Postfix Permissions/Ownership

postfix_configs = [
    mysql_virtual_domains,
    mysql_virtual_domains,
    mysql_virtual_forwardings,
    mysql_virtual_mailboxes,
    mysql_virtual_email2email,
    main,
    master,
]

for conf in postfix_configs:
    # Setting chmod o= aka 640
    chmod_digit(conf, 640)
    # We want to leave user untouched hence -1 and group to postfix
    chown(conf, -1, 'postfix')

######################################## Dovecot Permissions

# chgrp dovecot and set chmod o= /etc/dovecot/dovecot-sql.conf.ext
chmod_digit(dovecotmysql, 640)
chown(dovecotmysql, -1, 'dovecot')

rainloop_dir = '/usr/local/CyberCP/public/rainloop'

os.chdir("/usr/local/CyberCP/public/rainloop")

recursive_permissions(rainloop_dir, 755, 644)

recursive_chown('/usr/local/lscp/modsec', 'lscpd', 'lscpd')

chmod_digit('/usr/local/lscp/bin/lscpdctrl', 775)

##

mkdir_p('/usr/local/lscpd/admin/')
mkdir_p('/usr/local/CyberCP/conf/')

mkdir_p('/etc/opendkim/keys/')
chown('/etc/opendkim/keys/', 'opendkim', 'opendkim')

chmod_digit('/etc/opendkim/', 755)
chown('/etc/opendkim/', 'root', 'opendkim')

chmod_digit('/etc/opendkim.conf', 644)
chown('/etc/opendkim.conf', 'root', 'root')

command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"

# if self.distro == ubuntu:
#     if not os.access('/usr/local/lsws/lsphp70/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp70/bin/php7.0', os.R_OK):
#             symlink('/usr/local/lsws/lsphp70/bin/php7.0', '/usr/local/lsws/lsphp70/bin/php')
#     if not os.access('/usr/local/lsws/lsphp71/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp71/bin/php7.1', os.R_OK):
#             symlink('/usr/local/lsws/lsphp71/bin/php7.1', '/usr/local/lsws/lsphp71/bin/php')
#     if not os.access('/usr/local/lsws/lsphp72/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp72/bin/php7.2', os.R_OK):
#             symlink('/usr/local/lsws/lsphp72/bin/php7.2', '/usr/local/lsws/lsphp72/bin/php')
#     if not os.access('/usr/local/lsws/lsphp73/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp73/bin/php7.3', os.R_OK):
#             symlink('/usr/local/lsws/lsphp73/bin/php7.3', '/usr/local/lsws/lsphp73/bin/php')
#     if not os.access('/usr/local/lsws/lsphp74/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp74/bin/php7.4', os.R_OK):
#             symlink('/usr/local/lsws/lsphp74/bin/php7.4', '/usr/local/lsws/lsphp74/bin/php')
#     if not os.access('/usr/local/lsws/lsphp80/bin/php', os.R_OK):
#         if os.access('/usr/local/lsws/lsphp80/bin/php8.0', os.R_OK):
#             symlink('/usr/local/lsws/lsphp74/bin/php8.0', '/usr/local/lsws/lsphp80/bin/php')
#
# chmod_digit(os.path.join(self.cwd, 'composer.sh'), 775)

recursive_chown('/usr/local/lscp/cyberpanel/rainloop/data', 'lscpd', 'lscpd')
