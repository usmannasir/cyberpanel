#!/usr/bin/env bash
## Author: Michael Ramsey
## Objective Fix session issues on CyberPanel and standardized session paths.
# Fixes #430
# https://github.com/usmannasir/cyberpanel/issues/430


# Create the session path directories and chmod it for security to 1733 like the existing one is.

for version in $(ls /usr/local/lsws|grep lsphp); 
  do
    mkdir -p "/var/lib/lsphp/session/$version"
    chmod -R 1733 "/var/lib/lsphp/session/$version"
done


YUM_CMD=$(which yum 2> /dev/null)
APT_GET_CMD=$(which apt-get 2> /dev/null)

if [[ -n $YUM_CMD ]]; then
	# Centos
	for version in $(ls /usr/local/lsws|grep lsphp); do echo ""; echo "PHP $version"; sed -i -e "s|^;session.save_path.*|session.save_path = '/var/lib/lsphp/session/${version}'|g" -e "s|^session.save_path.*|session.save_path = '/var/lib/lsphp/session/${version}'|g" /usr/local/lsws/${version}/etc/php.ini; /usr/local/lsws/${version}/bin/php -i |grep -Ei 'session.save_path' && echo "" ; done; service lsws restart; killall lsphp;



elif [[ -n $APT_GET_CMD ]]; then
	# Ubuntu
	for phpver in $(ls -1 /usr/local/lsws/ |grep lsphp | sed 's/lsphp//g') ; do echo ""; echo "LSPHP $phpver" ; lsphpver=$(echo $phpver | sed 's/^\(.\{1\}\)/\1./'); sed -i -e "s|^;session.save_path.*|session.save_path = '/var/lib/lsphp/session/lsphp${phpver}'|g" -e "s|^session.save_path.*|session.save_path = '/var/lib/lsphp/session/lsphp${phpver}'|g" /usr/local/lsws/lsphp${phpver}/etc/php/${lsphpver}/litespeed/php.ini ; /usr/local/lsws/lsphp${phpver}/bin/php -i |grep -Ei 'session.save_path' && echo "" ; done; service lsws restart; killall lsphp;

else
   echo "error can't install required packages. Unsupported OS"
   exit 1;
fi


# Setup a cron to clear stuff older then session.gc_maxlifetime currently set in the php.ini for each version

# Create cron file if missing.
if [[ ! -e /usr/local/CyberCP/bin/cleansessions ]]; then
	touch /usr/local/CyberCP/bin/cleansessions
	chmod +x /usr/local/CyberCP/bin/cleansessions
	cat >> /usr/local/CyberCP/bin/cleansessions <<"EOL"
#!/bin/bash
for version in $(ls /usr/local/lsws|grep lsphp); do echo ""; echo "PHP $version"; session_time=$(/usr/local/lsws/${version}/bin/php -i |grep -Ei 'session.gc_maxlifetime'| grep -Eo "[[:digit:]]+"|sort -u); find -O3 "/var/lib/lsphp/session/${version}" -ignore_readdir_race -depth -mindepth 1 -name 'sess_*' -type f -cmin 120 -delete; done
EOL

fi

# Create crontab only if not exist
echo "Installing PHP Session cleaning cron"
command="/usr/local/CyberCP/bin/cleansessions >/dev/null 2>&1"
job="09,39 * * * * $command"
cat <(grep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -

echo "Checking cleansessions file"
cat /usr/local/CyberCP/bin/cleansessions

# Set to a 4 hour default as the 24 min default is kinda low and logs people out too often and as a global default in shared scenario its hard for clients to know how to override this while working in their admin area backends etc.
grep -Eilr '^memory_limit' --include=\*php.ini /usr/local/lsws/lsphp* | xargs sed -i -e "s/^session.gc_maxlifetime.*/session.gc_maxlifetime = '14400'/g"
