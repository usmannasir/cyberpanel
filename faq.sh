#!/bin/bash


RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

#${RED}text${NC}
#${GREEN}  ${BLUE}


echo -e "Frequently Asked Question

${PURPLE}1.${NC} How to reset CyberPanel admin password?

execute command ${RED}adminPass YOUR_NEW_PASSWORD${NC}

${BLUE}------------------------------------------------------------${NC}

${PURPLE}2.${NC} How to reset LiteSpeed WebAdmin Console user/password ?

execute command ${RED}/usr/local/lsws/admin/misc/admpass.sh${NC}

${BLUE}------------------------------------------------------------${NC}

${PURPLE}3.${NC} How to access LiteSpeed webadmin console ?

Please check this post: ${GREEN}https://forums.cyberpanel.net/discussion/87/tutorial-how-to-setup-and-login-to-openlitespeed-webadmin-console/p1${NC}

${BLUE}------------------------------------------------------------${NC}

${PURPLE}4.${NC} What is MariaDB root password ?

execute command ${RED}cat /etc/cyberpanel/mysqlPassword${NC} will show you the root password

${BLUE}------------------------------------------------------------${NC}

${PURPLE}5.${NC} Can I change MariaDB root passwod ?

Yes , but after you changed , please make sure you have updated the password in following 2 files as well

${RED}/etc/cyberpanel/mysqlPassword${NC}

${RED}/usr/local/CyberCP/CyberCP/settings.py${NC}

otherwise CyberPanel will not have access to database.

${BLUE}------------------------------------------------------------${NC}

${PURPLE}6.${NC} How to raise upload limit for cyberpanel's phpMyAdmin and File Manager?

edit file ${RED}/usr/local/lsws/lsphp73/etc/php.ini${NC} for CentOS

${RED}/usr/local/lsws/lsphp73/etc/php/7.3/litespeed/php.ini${NC} for Ubbuntu

find 2 configurations:

${RED}post_max_size${NC} and ${RED}upload_max_filesize${NC} , change from to higher number, e.g. ${RED}100M${NC} (don't miss the M)

and then run ${RED}pkill lsphp${NC} to kill all current php process for new configuration to take effect.

${BLUE}------------------------------------------------------------${NC}

${PURPLE}7.${NC} How to add more IPs to my website(s) ?

For OpenLiteSpeed, please check this post: ${GREEN}https://forums.cyberpanel.net/discussion/126/tutorial-how-to-add-2nd-ip-for-websites/p1${NC}

For LiteSpeed Enterprise, please check this post: ${GREEN}https://forums.cyberpanel.net/discussion/3745/tutorial-how-to-add-2nd-ip-for-litespeed-enterprise/p1${NC}

${BLUE}------------------------------------------------------------${NC}

${PURPLE}8.${NC} How to remove 8090 port in CyberPanel URL ?

Please check this post ${GREEN}https://blog.cyberpanel.net/2018/12/25/how-to-remove-port-8090-from-cyberpanel/${NC}

${BLUE}------------------------------------------------------------${NC}

${PURPLE}9.${NC} How to enable Auto-Index for my site ?

Please check this post ${GREEN}https://forums.cyberpanel.net/discussion/3850/tutorial-how-to-enable-auto-index-on-openlitespeed-and-litespeed-enterprise${NC}
"
