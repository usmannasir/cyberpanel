#!/usr/bin/env bash
wget -O composer-setup.php https://cyberpanel.sh/?composer
sed -i "s|'://getcomposer.org'|'://mirrors.aliyun.com/composer'|g" composer-setup.php
php composer-setup.php
php -r "unlink('composer-setup.php');"
mv composer.phar /usr/bin/composer
composer config -g repo.packagist composer https://mirrors.aliyun.com/composer/
composer clear-cache
