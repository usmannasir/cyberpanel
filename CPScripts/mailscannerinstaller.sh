#!/bin/bash
#systemctl stop firewalld

check_return() {
#check previous command result , 0 = ok ,  non-0 = something wrong.
if [[ $? -eq "0" ]] ; then
	:
else
	echo -e "\ncommand failed, exiting..."
	exit
fi
}

echo 'backup configs';
cp /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/postfix/master.cf /etc/postfix/master.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/postfix/main.cf /etc/postfix/main.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/dovecot/dovecot-sql.conf.ext /etc/dovecot/dovecot-sql.conf.ext-bak_$(date '+%Y-%m-%d_%H_%M:%S')


ZONE=$(firewall-cmd --get-default-zone)
firewall-cmd --zone=$ZONE --add-port=4190/tcp --permanent
systemctl stop firewalld

echo 'Stop CSF'
csf -x

MAILSCANNER=/etc/MailScanner

if [ -d $MAILSCANNER ];then

echo "MailScanner found. If you wish to reinstall then remove the package and revert"
echo "Postfix back to its original config at /etc/postfix/main.cf and remove"
echo "/etc/MailScanner and /usr/share/MailScanner directories"
exit
fi

if [ -f /etc/os-release ];then
OS=$(head -1 /etc/os-release)
UBUNTUVERSION=$(sed '6q;d' /etc/os-release)
CENTOSVERSION=$(sed '5q;d' /etc/os-release)
CLNVERSION=$(sed '3q;d' /etc/os-release)
fi

if [ "$CENTOSVERSION" = "VERSION_ID=\"7\"" ];then

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
DIR=/etc/mail/spamassassin

if [ -d "$DIR" ];  then
sa-update

else

echo "Please install spamassassin through the CyberPanel interface before proceeding"

exit
fi

elif [ "$CENTOSVERSION" = "VERSION_ID=\"8\"" ];then

setenforce 0
yum install -y perl yum-utils perl-CPAN 
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

DIR=/etc/mail/spamassassin

if [ -d "$DIR" ];  then
sa-update

else

echo "Please install spamassassin through the CyberPanel interface before proceeding"

exit
fi

elif [ "$CLNVERSION" = "ID=\"cloudlinux\"" ];then

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
DIR=/etc/mail/spamassassin

if [ -d "$DIR" ];  then
sa-update

else

echo "Please install spamassassin through the CyberPanel interface before proceeding"

exit
fi

elif [ "$OS" = "NAME=\"Ubuntu\"" ];then

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

DIR=/etc/spamassassin
if [ -d "$DIR" ];  then

apt-get -y install razor pyzor libencode-detect-perl libgeo-ip-perl libnet-patricia-perl
sa-update
else
echo "Please install spamassassin through the CyberPanel interface before proceeding"
exit
fi

fi

echo "header_checks = regexp:/etc/postfix/header_checks" >> /etc/postfix/main.cf
echo "/^Received:/ HOLD" >> /etc/postfix/header_checks

systemctl restart postfix

if [ "$OS" = "NAME=\"Ubuntu\"" ];then
wget https://github.com/MailScanner/v5/releases/download/5.3.3-1/MailScanner-5.3.3-1.noarch.deb
dpkg -i *.noarch.deb

mkdir /var/run/MailScanner
mkdir /var/lock/subsys
mkdir /var/lock/subsys/MailScanner
chown -R postfix:postfix /var/run/MailScanner
chown -R postfix:postfix /var/lock/subsys/MailScanner
chown -R postfix:postfix /var/spool/MailScanner

elif [ "$OS" = "NAME=\"CentOS Linux\"" ];then
wget https://github.com/MailScanner/v5/releases/download/5.3.3-1/MailScanner-5.3.3-1.rhel.noarch.rpm
rpm -Uvh *.rhel.noarch.rpm

elif [ "$OS" = "NAME=\"CloudLinux\"" ];then
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

mkdir /usr/local/CyberCP/public/mailwatch

cd /usr/local/CyberCP/public/mailwatch

git clone --depth=1 https://github.com/mailwatch/MailWatch.git --branch 1.2 --single-branch

mv /usr/local/CyberCP/public/mailwatch/MailWatch/* /usr/local/CyberCP/public/mailwatch/

PASSWORD=$(cat /etc/cyberpanel/mysqlPassword)
USER=root
DATABASE=mailscanner
ADMINPASS=$(cat /etc/cyberpanel/adminPass)
mysql -u${USER} -p${PASSWORD} < "/usr/local/CyberCP/public/mailwatch/create.sql"
mysql -u${USER} -p${PASSWORD} -e "use mailscanner";
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "GRANT ALL ON mailscanner.* TO root@localhost IDENTIFIED BY '${PASSWORD}';"
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "FLUSH PRIVILEGES;"
mysql -u${USER} -D${DATABASE} -p${PASSWORD} -e "INSERT INTO mailscanner.users SET username = 'admin', password = MD5('${ADMINPASS}'), fullname = 'admin', type = 'A';"

cp /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php.example /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php

sed -i "s/^define('DB_USER',.*/define('DB_USER','root');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php
sed -i "s/^define('DB_PASS',.*/define('DB_PASS','${PASSWORD}');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php
sed -i "s/^define('MAILWATCH_HOME',.*/define(\'MAILWATCH_HOME\', \'\/usr\/local\/CyberCP\/public\/mailwatch\/mailscanner');/" /usr/local/CyberCP/public/mailwatch/mailscanner/conf.php

MSDEFAULT=/etc/MailScanner/defaults
if [ -f "$MSDEFAULT" ];then
sed -i 's/^run_mailscanner=.*/run_mailscanner=1/' /etc/MailScanner/defaults
elif [ ! -f "$MSDEFAULT" ];then
touch /etc/MailScanner/defaults
echo "run_mailscanner=1" >> /etc/MailScanner/defaults
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


echo 'Restart and check services are up'
systemctl restart dovecot && systemctl restart postfix && systemctl restart spamassassin && systemctl restart mailscanner;

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
