#!/bin/bash
#systemctl stop firewalld

check_return() {
  #check previous command result , 0 = ok ,  non-0 = something wrong.
  if [[ $? -eq "0" ]]; then
    :
  else
    echo -e "\ncommand failed, exiting..."
    exit
  fi
}

echo 'backup configs'
cp /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf-bak_$(date '+%Y-%m-%d_%H_%M:%S')
cp /etc/postfix/master.cf /etc/postfix/master.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S')
cp /etc/postfix/main.cf /etc/postfix/main.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S')
cp /etc/dovecot/dovecot-sql.conf.ext /etc/dovecot/dovecot-sql.conf.ext-bak_$(date '+%Y-%m-%d_%H_%M:%S')

ZONE=$(firewall-cmd --get-default-zone)
firewall-cmd --zone=$ZONE --add-port=4190/tcp --permanent
systemctl stop firewalld

echo 'Stop CSF'
csf -x

MAILSCANNER=/etc/MailScanner

if [ -d $MAILSCANNER ]; then
  echo "MailScanner found. If you wish to reinstall then remove the package and revert"
  echo "Postfix back to its original config at /etc/postfix/main.cf and remove"
  echo "/etc/MailScanner and /usr/share/MailScanner directories"
  exit
fi

### Check SpamAssasin before moving forward

DIR=/etc/mail/spamassassin

if [ -d "$DIR" ]; then
  sa-update
else
  echo "Please install SpamAssasin through the CyberPanel interface before proceeding"
  exit
fi

### OS Detection
Server_OS=""
Server_OS_Version=""
if grep -q -E "CentOS Linux 7|CentOS Linux 8" /etc/os-release ; then
  Server_OS="CentOS"
elif grep -q "AlmaLinux-8" /etc/os-release ; then
  Server_OS="AlmaLinux"
elif grep -q -E "CloudLinux 7|CloudLinux 8" /etc/os-release ; then
  Server_OS="CloudLinux"
elif grep -q -E "Rocky Linux" /etc/os-release ; then
  Server_OS="RockyLinux"
elif grep -q -E "Ubuntu 18.04|Ubuntu 20.04|Ubuntu 20.10|Ubuntu 22.04" /etc/os-release ; then
  Server_OS="Ubuntu"
elif grep -q -E "openEuler 20.03|openEuler 22.03" /etc/os-release ; then
  Server_OS="openEuler"
else
  echo -e "Unable to detect your system..."
  echo -e "\nCyberPanel is supported on x86_64 based Ubuntu 18.04, Ubuntu 20.04, Ubuntu 20.10, Ubuntu 22.04, CentOS 7, CentOS 8, AlmaLinux 8, RockyLinux 8, CloudLinux 7, CloudLinux 8, openEuler 20.03, openEuler 22.03...\n"
  exit
fi

Server_OS_Version=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )

echo -e "System: $Server_OS $Server_OS_Version detected...\n"

if [[ $Server_OS = "CloudLinux" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]] ; then
  Server_OS="CentOS"
  #CloudLinux gives version id like 7.8, 7.9, so cut it to show first number only
  #treat CloudLinux, Rocky and Alma as CentOS
fi

if [[ $Server_OS = "CentOS" ]] && [[ "$Server_OS_Version" = "7" ]] ; then

  setenforce 0
  yum install -y perl yum-utils perl-CPAN
  yum install -y gcc cpp perl bzip2 zip make patch automake rpm-build perl-Archive-Zip perl-Filesys-Df perl-OLE-Storage_Lite perl-Sys-Hostname-Long perl-Sys-SigAction perl-Net-CIDR perl-DBI perl-MIME-tools perl-DBD-SQLite binutils glibc-devel perl-Filesys-Df zlib unzip zlib-devel wget mlocate clamav "perl(DBD::mysql)"

  rpm -Uvh https://forensics.cert.org/centos/cert/7/x86_64/unrar-5.4.0-1.el7.x86_64.rpm
  export PERL_MM_USE_DEFAULT=1
  curl -L https://cpanmin.us | perl - App::cpanminus
  perl -MCPAN -e 'install Encoding::FixLatin'
  perl -MCPAN -e 'install Digest::SHA1'
  perl -MCPAN -e 'install Geo::IP'
  perl -MCPAN -e 'install Razor2::Client::Agent'
  perl -MCPAN -e 'install Net::Patricia'

  freshclam -v

elif [[ $Server_OS = "CentOS" ]] && [[ "$Server_OS_Version" = "8" ]] ; then

  setenforce 0
  yum install -y perl yum-utils perl-CPAN
  dnf --enablerepo=powertools install -y perl-IO-stringy
  dnf --enablerepo=PowerTools install -y perl-IO-stringy
  yum install -y gcc cpp perl bzip2 zip make patch automake rpm-build perl-Archive-Zip perl-Filesys-Df perl-OLE-Storage_Lite perl-Net-CIDR perl-DBI perl-MIME-tools perl-DBD-SQLite binutils glibc-devel perl-Filesys-Df zlib unzip zlib-devel wget mlocate clamav clamav-update "perl(DBD::mysql)"

  rpm -Uvh https://forensics.cert.org/centos/cert/8/x86_64/unrar-5.4.0-1.el8.x86_64.rpm

  export PERL_MM_USE_DEFAULT=1
  curl -L https://cpanmin.us | perl - App::cpanminus

  perl -MCPAN -e 'install Encoding::FixLatin'
  perl -MCPAN -e 'install Digest::SHA1'
  perl -MCPAN -e 'install Geo::IP'
  perl -MCPAN -e 'install Razor2::Client::Agent'
  perl -MCPAN -e 'install Sys::Hostname::Long'
  perl -MCPAN -e 'install Sys::SigAction'

  freshclam -v

elif [ "$CLNVERSION" = "ID=\"cloudlinux\"" ]; then

  setenforce 0
  yum install -y perl yum-utils perl-CPAN
  yum install -y gcc cpp perl bzip2 zip make patch automake rpm-build perl-Archive-Zip perl-Filesys-Df perl-OLE-Storage_Lite perl-Sys-Hostname-Long perl-Sys-SigAction perl-Net-CIDR perl-DBI perl-MIME-tools perl-DBD-SQLite binutils glibc-devel perl-Filesys-Df zlib unzip zlib-devel wget mlocate clamav "perl(DBD::mysql)"

  rpm -Uvh https://forensics.cert.org/centos/cert/7/x86_64/unrar-5.4.0-1.el7.x86_64.rpm
  export PERL_MM_USE_DEFAULT=1
  curl -L https://cpanmin.us | perl - App::cpanminus
  perl -MCPAN -e 'install Encoding::FixLatin'
  perl -MCPAN -e 'install Digest::SHA1'
  perl -MCPAN -e 'install Geo::IP'
  perl -MCPAN -e 'install Razor2::Client::Agent'
  perl -MCPAN -e 'install Net::Patricia'

  freshclam -v

elif [[ $Server_OS = "Ubuntu" ]]; then

  apt-get install -y libmysqlclient-dev

  apt-get install -y cpanminus gcc perl bzip2 zip make patch automake rpm libarchive-zip-perl libfilesys-df-perl libole-storage-lite-perl libsys-hostname-long-perl libsys-sigaction-perl libregexp-common-net-cidr-perl libmime-tools-perl libdbd-sqlite3-perl binutils build-essential libfilesys-df-perl zlib1g unzip mlocate clamav libdbd-mysql-perl unrar libclamav-dev libclamav-client-perl libclamunrar9

  cpanm Encoding::FixLatin
  cpanm Digest::SHA1
  cpanm Geo::IP
  cpanm Razor2::Client::Agent
  cpanm Net::Patricia
  cpanm Net::CIDR

  sudo systemctl stop clamav-freshclam.service

  freshclam

  sudo systemctl start clamav-freshclam.service

fi

echo "header_checks = regexp:/etc/postfix/header_checks" >>/etc/postfix/main.cf
echo "/^Received:/ HOLD" >>/etc/postfix/header_checks

systemctl restart postfix

if [[ $Server_OS = "Ubuntu" ]]; then
  wget https://github.com/MailScanner/v5/releases/download/5.4.4-1/MailScanner-5.4.4-1.noarch.deb
  dpkg -i *.noarch.deb

  mkdir /var/run/MailScanner
  mkdir /var/lock/subsys
  mkdir /var/lock/subsys/MailScanner
  chown -R postfix:postfix /var/run/MailScanner
  chown -R postfix:postfix /var/lock/subsys/MailScanner
  chown -R postfix:postfix /var/spool/MailScanner

elif [[ $Server_OS = "CentOS" ]]; then
  wget https://github.com/MailScanner/v5/releases/download/5.4.4-1/MailScanner-5.4.4-1.rhel.noarch.rpm
  rpm -Uvh *.rhel.noarch.rpm
elif [ "$OS" = "NAME=\"CloudLinux\"" ]; then
  wget https://github.com/MailScanner/v5/releases/download/5.3.3-1/MailScanner-5.3.3-1.rhel.noarch.rpm
  rpm -Uvh *.rhel.noarch.rpm
fi

mkdir /var/spool/MailScanner/spamassassin

chown postfix.mtagroup /var/spool/MailScanner/spamassassin
chown root.mtagroup /var/spool/MailScanner/incoming/
chown postfix.mtagroup /var/spool/MailScanner/milterin
chown postfix.mtagroup /var/spool/MailScanner/milterout
chown postfix.mtagroup /var/spool/postfix/hold
chown postfix.mtagroup /var/spool/postfix/incoming
usermod -a -G mtagroup nobody

chmod g+rx /var/spool/postfix/incoming
chmod g+rx /var/spool/postfix/hold
chmod -R 0775 /var/spool/postfix/incoming
chmod -R 0775 /var/spool/postfix/hold

sed -i 's/^Run As User =.*/& postfix/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Run As Group =.*/& postfix/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Incoming Queue Dir =.*/Incoming Queue Dir = \/var\/spool\/postfix\/hold/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Outgoing Queue Dir =.*/Outgoing Queue Dir = \/var\/spool\/postfix\/incoming/' /etc/MailScanner/MailScanner.conf
sed -i 's/^MTA =.*/MTA = postfix/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Quarantine User =.*/& postfix/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Quarantine Group =.*/& mtagroup/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Quarantine Permissions =.*/Quarantine Permissions = 640/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Virus Scanners =.*/Virus Scanners = clamav/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Is Definitely Not Spam =.*/Is Definitely Not Spam = \&SQLWhitelist/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Is Definitely Spam =.*/Is Definitely Spam = \&SQLBlacklist/' /etc/MailScanner/MailScanner.conf
sed -i 's/^SpamAssassin User State Dir =.*/& \/var\/spool\/MailScanner\/spamassassin/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Always Looked Up Last =.*/Always Looked Up Last = \&MailWatchLogging/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Quarantine Whole Message =.*/Quarantine Whole Message = yes/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Spam List =.*/Spam List = SBL + XBL/' /etc/MailScanner/MailScanner.conf
sed -i 's/^Sign Clean Messages =.*/Sign Clean Messages = no/' /etc/MailScanner/MailScanner.conf

mkdir /usr/local/CyberCP/public/mailwatch

cd /usr/local/CyberCP/public/mailwatch

git clone --depth=1 https://github.com/mailwatch/MailWatch.git --branch 1.2 --single-branch

mv /usr/local/CyberCP/public/mailwatch/MailWatch/* /usr/local/CyberCP/public/mailwatch/

PASSWORD=$(cat /etc/cyberpanel/mysqlPassword)
USER=root
DATABASE=mailscanner
ADMINPASS=$(cat /etc/cyberpanel/adminPass)

### Fix a bug in MailWatch SQL File

sed -i 's/char(512)/char(255)/g' /usr/local/CyberCP/public/mailwatch/create.sql

##

mysql -u${USER} -p${PASSWORD} <"/usr/local/CyberCP/public/mailwatch/create.sql"
mysql -u${USER} -p${PASSWORD} -e "use mailscanner"
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "GRANT ALL ON mailscanner.* TO root@localhost IDENTIFIED BY '${PASSWORD}';"
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "FLUSH PRIVILEGES;"
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "INSERT INTO mailscanner.users SET username = 'admin', password = MD5('${ADMINPASS}'), fullname = 'admin', type = 'A';"

cp /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php.example /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php

sed -i "s/^define('DB_USER',.*/define('DB_USER','root');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php
sed -i "s/^define('DB_PASS',.*/define('DB_PASS','${PASSWORD}');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php
sed -i "s/^define('MAILWATCH_HOME',.*/define(\'MAILWATCH_HOME\', \'\/usr\/local\/CyberCP\/public\/mailwatch\/mailscanner');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php

MSDEFAULT=/etc/MailScanner/defaults
if [ -f "$MSDEFAULT" ]; then
  sed -i 's/^run_mailscanner=.*/run_mailscanner=1/' /etc/MailScanner/defaults
elif [ ! -f "$MSDEFAULT" ]; then
  touch /etc/MailScanner/defaults
  echo "run_mailscanner=1" >>/etc/MailScanner/defaults
fi

cp /usr/local/CyberCP/public/mailwatch/MailScanner_perl_scripts/MailWatchConf.pm /usr/share/MailScanner/perl/custom/
sed -i 's/^my (\$db_user) = .*/my (\$db_user) = \x27'${USER}'\x27;/' /usr/share/MailScanner/perl/custom/MailWatchConf.pm
sed -i 's/^my (\$db_pass) = .*/my (\$db_pass) = \x27'${PASSWORD}'\x27;/' /usr/share/MailScanner/perl/custom/MailWatchConf.pm
ln -s /usr/local/CyberCP/public/mailwatch/MailScanner_perl_scripts/MailWatch.pm /usr/share/MailScanner/perl/custom
ln -s /usr/local/CyberCP/public/mailwatch/MailScanner_perl_scripts/SQLBlackWhiteList.pm /usr/share/MailScanner/perl/custom
ln -s /usr/local/CyberCP/public/mailwatch/MailScanner_perl_scripts/SQLSpamSettings.pm /usr/share/MailScanner/perl/custom
sed -i "s/^\$pathToFunctions =.*/\$pathToFunctions = '\/usr\/local\/CyberCP\/public\/mailwatch\/mailscanner\/functions.php';/" /usr/local/CyberCP/public/mailwatch/upgrade.php

/usr/local/lsws/lsphp72/bin/php /usr/local/CyberCP/public/mailwatch/upgrade.php
systemctl enable mailscanner
systemctl restart mailscanner

IPADDRESS=$(cat /etc/cyberpanel/machineIP)

### Furhter onwards is sieve configurations

#echo 'Setting up spamassassin and sieve to deliver spam to Junk folder by default'
##echo "If you wish mailscanner/spamassassin to send spam email to a spam folder please follow the tutorial on the Cyberpanel Website"
#echo 'Fix protocols'
#sed -i 's/^protocols =.*/protocols = imap pop3 lmtp sieve/g' /etc/dovecot/dovecot.conf
#
#sed -i "s|^user_query.*|user_query = SELECT '5000' as uid, '5000' as gid, '/home/vmail/%d/%n' as home,mail FROM e_users WHERE email='%u';|g" /etc/dovecot/dovecot-sql.conf.ext
#
#if [ "$OS" = "NAME=\"Ubuntu\"" ]; then
#  if [ "$UBUNTUVERSION" = "VERSION_ID=\"18.04\"" ]; then
#    apt-get install -y dovecot-managesieved dovecot-sieve dovecot-lmtpd net-tools pflogsumm
#  elif [ "$UBUNTUVERSION" = "VERSION_ID=\"20.04\"" ]; then
#    apt-get install -y libmysqlclient-dev
#    sed -e '/deb/ s/^#*/#/' -i /etc/apt/sources.list.d/dovecot.list
#    apt install -y dovecot-lmtpd dovecot-managesieved dovecot-sieve net-tools pflogsumm
#  fi
#
#elif [ "$CENTOSVERSION" = "VERSION_ID=\"7\"" ]; then
#
#  yum install -y nano net-tools dovecot-pigeonhole postfix-perl-scripts
#
#elif [ "$CENTOSVERSION" = "VERSION_ID=\"8\"" ]; then
#
#  rpm -Uvh http://mirror.ghettoforge.org/distributions/gf/el/8/gf/x86_64/gf-release-8-11.gf.el8.noarch.rpm
#  dnf --enablerepo=gf-plus upgrade -y dovecot23*
#  dnf --enablerepo=gf-plus install -y dovecot23-pigeonhole
#  dnf install -y net-tools postfix-perl-scripts
#
#elif [ "$CLNVERSION" = "ID=\"cloudlinux\"" ]; then
#  yum install -y nano net-tools dovecot-pigeonhole postfix-perl-scripts
#fi
#
## Create Sieve files
#mkdir -p /etc/dovecot/sieve/global
#touch /var/log/{dovecot-lda-errors.log,dovecot-lda.log}
#touch /var/log/{dovecot-sieve-errors.log,dovecot-sieve.log}
#touch /var/log/{dovecot-lmtp-errors.log,dovecot-lmtp.log}
#touch /etc/dovecot/sieve/default.sieve
#chown vmail: -R /etc/dovecot/sieve
#chown vmail:mail /var/log/dovecot-*
#
#echo 'Create Sieve Default spam to Junk rule'
#cat >>/etc/dovecot/sieve/default.sieve <<EOL
#require "fileinto";
#if header :contains "X-Spam-Flag" "YES" {
#  fileinto "INBOX.Junk E-mail";
#}
#EOL
#
#echo "Adding Sieve to /etc/dovecot/dovecot.conf"
#cat >>/etc/dovecot/dovecot.conf <<EOL
#
#service managesieve-login {
#  inet_listener sieve {
#    port = 4190
#  }
#}
#service managesieve {
#}
#protocol sieve {
#    managesieve_max_line_length = 65536
#    managesieve_implementation_string = dovecot
#    log_path = /var/log/dovecot-sieve-errors.log
#    info_log_path = /var/log/dovecot-sieve.log
#}
#plugin {
#sieve = /home/vmail/%d/%n/dovecot.sieve
#sieve_global_path = /etc/dovecot/sieve/default.sieve
#sieve_dir = /home/vmail/%d/%n/sieve
#sieve_global_dir = /etc/dovecot/sieve/global/
#}
#protocol lda {
#    mail_plugins = $mail_plugins sieve quota
#    postmaster_address = postmaster@example.com
#    hostname = server.example.com
#    auth_socket_path = /var/run/dovecot/auth-master
#    log_path = /var/log/dovecot-lda-errors.log
#    info_log_path = /var/log/dovecot-lda.log
#}
#protocol lmtp {
#    mail_plugins = $mail_plugins sieve quota
#    log_path = /var/log/dovecot-lmtp-errors.log
#    info_log_path = /var/log/dovecot-lmtp.log
#}
#EOL
#
#hostname=$(hostname)
#
#echo 'Fix postmaster email in sieve'
#postmaster_address=$(grep postmaster_address /etc/dovecot/dovecot.conf | sed 's/.*=//' | sed -e 's/^[ \t]*//' | sort -u)
#
#sed -i "s|postmaster@example.com|$postmaster_address|g" /etc/dovecot/dovecot.conf
#sed -i "s|server.example.com|$hostname|g" /etc/dovecot/dovecot.conf
#sed -i "s|postmaster@example.com|$postmaster_address|g" /etc/dovecot/dovecot.conf
#
##Sieve the global spam filter
#sievec /etc/dovecot/sieve/default.sieve
#
##Sieve the global spam filter
#sievec /etc/dovecot/sieve/default.sieve
#
#if [ "$OS" = "NAME=\"Ubuntu\"" ]; then
#  sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/lib/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf
#
#elif [ "$OS" = "NAME=\"CentOS Linux\"" ]; then
#  sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/libexec/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf
#
#elif [ "$OS" = "NAME=\"CloudLinux\"" ]; then
#  sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/libexec/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf
#
#fi

echo 'Restart and check services are up'
systemctl restart dovecot && systemctl restart postfix && systemctl restart spamassassin && systemctl restart mailscanner

csf -e

echo "MailScanner successfully installed. MailWatch successfully installed."
echo "Visit https://${IPADDRESS}:8090/mailwatch/mailscanner"
echo "Username: admin"
echo "Password: ${ADMINPASS}"
#echo "If you wish mailscanner/spamassassin to send spam email to a spam folder please follow the tutorial on the Cyberpanel Website"
echo "Firewalld is stopped. Either enable, install CSF or use an alternative!"
echo "Optional cpan/cpanm modules are available for MailScanner. Cronjobs and further postfix tools are available for MailWatch"
echo "See https://www.mailwatch.org and https://docs.mailwatch.org/install/optional-setup.html"
exit
