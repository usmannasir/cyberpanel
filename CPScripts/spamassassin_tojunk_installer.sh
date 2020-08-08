#!/bin/bash
# SpamAssassin Setup Spam to Junk folder. Should be called after the main SpamAssassin install part completes or mapped to an optional button to install. Personally think this should be a default part of the SpamAssassin installation.

echo 'backup configs';
cp /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/postfix/master.cf /etc/postfix/master.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/postfix/main.cf /etc/postfix/main.cf-bak_$(date '+%Y-%m-%d_%H_%M:%S');
cp /etc/dovecot/dovecot-sql.conf.ext /etc/dovecot/dovecot-sql.conf.ext-bak_$(date '+%Y-%m-%d_%H_%M:%S')


echo 'Setting up spamassassin and sieve to deliver spam to Junk folder by default'
echo 'Fix protocols'
sed -i 's/^protocols =.*/protocols = imap pop3 lmtp sieve/g' /etc/dovecot/dovecot.conf


sed -i "s|^user_query.*|user_query = SELECT '5000' as uid, '5000' as gid, '/home/vmail/%d/%n' as home,mail FROM e_users WHERE email='%u';|g" /etc/dovecot/dovecot-sql.conf.ext

if [ "$OS" = "NAME=\"Ubuntu\"" ];then
if [ "$UBUNTUVERSION" = "VERSION_ID=\"18.04\"" ];then
       apt-get install -y dovecot-managesieved dovecot-sieve dovecot-lmtpd net-tools pflogsumm
elif [ "$UBUNTUVERSION" = "VERSION_ID=\"20.04\"" ];then
           apt-get install -y libmysqlclient-dev
           sed -e '/deb/ s/^#*/#/' -i /etc/apt/sources.list.d/dovecot.list           
		   apt install -y dovecot-lmtpd dovecot-managesieved dovecot-sieve net-tools pflogsumm
fi

elif [ "$CENTOSVERSION" = "VERSION_ID=\"7\"" ];then

        yum install -y nano net-tools dovecot-pigeonhole postfix-perl-scripts
		
elif [ "$CENTOSVERSION" = "VERSION_ID=\"8\"" ];then

        rpm -Uvh http://mirror.ghettoforge.org/distributions/gf/el/8/gf/x86_64/gf-release-8-11.gf.el8.noarch.rpm
		dnf --enablerepo=gf-plus upgrade -y dovecot23*
		dnf --enablerepo=gf-plus install -y dovecot23-pigeonhole
		dnf install -y net-tools postfix-perl-scripts
        
elif [ "$CLNVERSION" = "ID=\"cloudlinux\"" ];then

        yum install -y nano net-tools dovecot-pigeonhole postfix-perl-scripts
fi


# Create Sieve files
mkdir -p /etc/dovecot/sieve/global
touch /var/log/{dovecot-lda-errors.log,dovecot-lda.log}
touch /var/log/{dovecot-sieve-errors.log,dovecot-sieve.log}
touch /var/log/{dovecot-lmtp-errors.log,dovecot-lmtp.log}
touch /etc/dovecot/sieve/default.sieve
chown vmail: -R /etc/dovecot/sieve
chown vmail:mail /var/log/dovecot-*

echo 'Create Sieve Default spam to Junk rule'
cat >> /etc/dovecot/sieve/default.sieve <<EOL
require "fileinto";
if header :contains "X-Spam-Flag" "YES" {
  fileinto "INBOX.Junk E-mail";
}
EOL


echo "Adding Sieve to /etc/dovecot/dovecot.conf"
cat >> /etc/dovecot/dovecot.conf <<EOL
service managesieve-login {
  inet_listener sieve {
    port = 4190
  }
}
service managesieve {
}
protocol sieve {
    managesieve_max_line_length = 65536
    managesieve_implementation_string = dovecot
    log_path = /var/log/dovecot-sieve-errors.log
    info_log_path = /var/log/dovecot-sieve.log
}
plugin {
sieve = /home/vmail/%d/%n/dovecot.sieve
sieve_global_path = /etc/dovecot/sieve/default.sieve
sieve_dir = /home/vmail/%d/%n/sieve
sieve_global_dir = /etc/dovecot/sieve/global/
}
protocol lda {
    mail_plugins = $mail_plugins sieve quota
    postmaster_address = postmaster@example.com
    hostname = server.example.com
    auth_socket_path = /var/run/dovecot/auth-master
    log_path = /var/log/dovecot-lda-errors.log
    info_log_path = /var/log/dovecot-lda.log
}
protocol lmtp {
    mail_plugins = $mail_plugins sieve quota
    log_path = /var/log/dovecot-lmtp-errors.log
    info_log_path = /var/log/dovecot-lmtp.log
}
EOL

hostname=$(hostname);

echo 'Fix postmaster email in sieve'
postmaster_address=$(grep postmaster_address /etc/dovecot/dovecot.conf |  sed 's/.*=//' |sed -e 's/^[ \t]*//'| sort -u)

sed -i "s|postmaster@example.com|$postmaster_address|g" /etc/dovecot/dovecot.conf
sed -i "s|server.example.com|$hostname|g" /etc/dovecot/dovecot.conf
sed -i "s|postmaster@example.com|$postmaster_address|g" /etc/dovecot/dovecot.conf

#Sieve the global spam filter
sievec /etc/dovecot/sieve/default.sieve

#Sieve the global spam filter
sievec /etc/dovecot/sieve/default.sieve

if [ "$OS" = "NAME=\"Ubuntu\"" ];then
	sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/lib/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf

elif [ "$OS" = "NAME=\"CentOS Linux\"" ];then
	sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/libexec/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf

elif [ "$OS" = "NAME=\"CloudLinux\"" ];then
        sed -i 's|^spamassassin.*|spamassassin unix -     n   n   -   -   pipe flags=DROhu user=vmail:vmail argv=/usr/bin/spamc -f -e  /usr/libexec/dovecot/deliver -f ${sender} -d ${user}@${nexthop}|g' /etc/postfix/master.cf

fi


echo 'Restart and check services are up'
systemctl restart dovecot && systemctl restart postfix && systemctl restart spamassassin
