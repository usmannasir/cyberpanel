#!/bin/bash

#EasyEngine to CyberPanel migration script

sudoer=""
server_port="22"
user_name="root"
RED='\033[0;31m'
NC='\033[0m'
DIR="/opt/easyengine"
DIR_SSL="/opt/easyengine/services/nginx-proxy/certs"
DIR_TMP="/opt/easyengine/tmp"
SSL="0"
owner_user=""
owner_group=""

set_header() {
if [[ -d /opt/easyengine/sites/${domains[$i]}/app/htdocs/wp-content ]] ; then
ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key "$sudoer wget -q -O /root/header.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/CPScripts/EasyEngine/header.sh ; $sudoer bash /root/header.sh ${domains[$i]}"
fi
}

fix_permission() {
ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
echo -e "\nget the user and group on remote CyberPanel server...."
owner_user=$(${ssh_v} stat -c '%U' /home/${domains[$i]})
owner_group=$(${ssh_v} stat -c '%G' /home/${domains[$i]})
#get user and group on remote server.
}


set_ssl_cyberpanel() {
if [[ $SSL == "1" ]] ; then
  echo -e "\nstarting certificate and private key transfer..."
ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
${ssh_v} "rm -f /etc/letsencrypt/live/${domains[$i]}/fullchain.pem"
${ssh_v} "rm -f /etc/letsencrypt/live/${domains[$i]}/privkey.pem"
#remove current self-signed cert

rsync --stats -av -e "ssh -o StrictHostKeyChecking=no -p $server_port -i /root/.ssh/cyberpanel_migration_key" $cert_file root@$server_ip:/etc/letsencrypt/live/${domains[$i]}/fullchain.pem
  if [[ $? == "0" ]] ; then
    echo -e "\ncert file transferred...\n"
  else
    echo -e "\ncert file trasnfer failed..."
    clean_up
    exit
  fi

rsync --stats -av -e "ssh -o StrictHostKeyChecking=no -p $server_port -i /root/.ssh/cyberpanel_migration_key" $key_file root@$server_ip:/etc/letsencrypt/live/${domains[$i]}/privkey.pem
    if [[ $? == "0" ]] ; then
      echo -e "\nkey file has been succesfully transferred to CyberPanel server...\n"
    else
      echo -e "\nkey file trasnfer failed..."
      clean_up
      exit
    fi
#rsync cert and key

echo -e "checking LiteSpeed status on remote Cyebrpanel server..."
${ssh_v} "/usr/local/lsws/bin/lswsctrl stop"
${ssh_v} "pkill lsphp"
${ssh_v} "systemctl stop lsws"
${ssh_v} "systemctl start lsws"
check_string=$(${ssh_v} "ps -aux | grep litespeed | grep -v grep")
  if echo $check_string | grep -q litespeed ; then
    echo -e "\nrestart LiteSpeed successful..."
  else
    echo -e "LiteSpeed start failed..."
  fi
fi
#restart LSWS to apply new cert

}

show_cyberpanel_site() {
  echo -e "\nchecking current websites on remote CyberPanel server..."
  ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
  $ssh_v "cyberpanel listWebsitesPretty"
}

create_database() {
  echo -e "\nstarting database creation on remote CyberPanel server..."
  ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"

  check_string=$(${ssh_v} "cyberpanel createDatabase --databaseWebsite  ${domains[$i]} --dbName $WPDBNAME --dbUsername $WPDBUSER --dbPassword $WPDBPASS")
  if echo $check_string | grep -q "None" ; then
    echo -e "\ndatabase successfully created..."
  else
    echo -e "\ndatabase failed to create..."
    clean_up
    exit
  fi

  check_string=$(${ssh_v} "mysql -u $WPDBUSER -p$WPDBPASS $WPDBNAME < /home/${domains[$i]}/$database_name ; if [ $? = 0 ] ; then echo "OK" ; fi")
  if echo $check_string | grep -q "OK" ; then
    echo -e "\nstarting  database import on remote CyberPanel..."
    echo -e "\ndatabase successfully imported..."
    ${ssh_v} rm -f /home/${domains[$i]}/$database_name
  else
    echo -e "\ndatabase import failed..."
    ${ssh_v} rm -f /home/${domains[$i]}/$database_name
    clean_up
    exit
  fi

#  ${ssh_v} sed -i 's|global-db:3306|localhost:3306|g' /home/${domains[$i]}/public_html/wp-config.php

  ${ssh_v} "sed -i 's|global-db:3306|/var/lib/mysql/mysql.sock|g' /home/${domains[$i]}/public_html/wp-config.php"
  #set DB HOST to local unix socket for better performance.

}

clean_up() {
#remove all the files created during operation
echo -e "\nstarting clean up process..."
ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key "$sudoer wget -q -O /root/key.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/CPScripts/EasyEngine/key.sh ; $sudoer bash /root/key.sh disable"
rm -f /root/.ssh/cyberpanel_migration_key
rm -rf /opt/easyengine/tmp
echo -e "\nclean up successful..."
}

create_site_cyberpanel() {
ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
echo -e "\nstarting to create ${domains[$i]} on remote CyberPanel server..."
echo -e "\nyou may see error message on acme.sh but this is normal as actual DNS is not pointed to remote server.\n\n\n"
check_string=$(${ssh_v} "cyberpanel createWebsite --package Default --owner admin --domainName ${domains[$i]} --email admin@${domains[$i]} --php 7.4 --ssl 1")
  if echo $check_string | grep -q "None" ; then
  echo -e "\nwebsite successfully created..."
    ${ssh_v} "rm -f /home/${domains[$i]}/public_html/index.html"
    ${ssh_v} "cat << EOF > /home/${domains[$i]}/public_html/.htaccess
RewriteCond %{REQUEST_URI} (wp-config|readme|license|example)\.(txt|html) [NC,OR]
RewriteCond %{REQUEST_URI} wp-content\/uploads\/.*php [NC,OR]
RewriteCond %{REQUEST_URI} (^\.|/\.) [NC]
RewriteRule .* - [F,L]
#EasyEnine converted equivalent rule.

<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
#WordPress default rule.
EOF"
#rewrite rule for similar effect on easyengine configuration.

  else
    echo -e "\nfailed to create website..."
    echo -e "\nplease check if ${domains[$i]} is already created on remote server, and delete it"
    clean_up
    exit
  fi
}

trasnfer_file() {
ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
if [[ -f /opt/easyengine/sites/${domains[$i]}/app/wp-config.php ]] ; then
  echo -e "\nstarting to transfer files..."
  echo -e "\ndepends on your files , this may take a while..."
  rsync --stats -av --chown=${owner_user}:${owner_group} -e "ssh -o StrictHostKeyChecking=no -p $server_port -i /root/.ssh/cyberpanel_migration_key" /opt/easyengine/sites/${domains[$i]}/app/wp-config.php root@$server_ip:/home/${domains[$i]}/public_html/wp-config.php
  if [[ $? == "0" ]] ; then
    echo -e "\nwp-config.php successfully transferred..."
  else
    echo -e "\nwp-config.php trasnfer failed..."
    clean_up
    exit
  fi

rsync --stats -av --chown=${owner_user}:${owner_group} -e "ssh -o StrictHostKeyChecking=no -p $server_port -i /root/.ssh/cyberpanel_migration_key" /opt/easyengine/sites/${domains[$i]}/app/htdocs/ root@$server_ip:/home/${domains[$i]}/public_html/
  if [[ $? == "0" ]] ; then
    echo -e "\nsite files succesfully transferred..."
  else
    echo -e "\nsite files trasnfer failed..."
    clean_up
    exit
  fi

rsync --stats -av -e "ssh -o StrictHostKeyChecking=no -p $server_port -i /root/.ssh/cyberpanel_migration_key" $OUTPUT/$database_name root@$server_ip:/home/${domains[$i]}/$database_name
  if [[ $? == "0" ]] ; then
    echo -e "\ndatabase dump successfully transferred..."
  else
    echo -e "\ndatabase dump trasnfer failed..."
    clean_up
    exit
  fi

else
  echo -e "\nthe script currently only works with Wordpress site..."
  clean_up
  exit
fi
}

export_cert() {
echo -e "\nstarting to search certificates and private keys..."
if [[ -f $DIR_SSL/${domains[$i]}.crt ]] && [[ -f $DIR_SSL/${domains[$i]}.key ]] ; then
  echo -e "\n${domains[$i]} cert detected..."
  echo -e "\n${domains[$i]} key detected..."
  SSL="1"
  cert_file="$DIR_SSL/${domains[$i]}.crt"
  key_file="$DIR_SSL/${domains[$i]}.key"
else
  SSL="0"
  echo -e "\n${domains[$i]} cert not found..."
  echo -e "\n${domains[$i]} key not found..."
fi
}


fetch_cyberpanel_key() {
if [[ ! -d /root/.ssh ]] ; then
  mkdir /root/.ssh
  chmod 700 /root/.ssh
fi
echo -e "\nPlease input your CyberPanel server address"
printf "%s" "Server Address: "
read server_ip
  if [[ $server_ip == "" ]] ; then
    echo -e "\nPlease enter a valid address"
    exit
  fi
echo -e "\nremote server is set to $server_ip..."
echo -e "\nPlease input your CyberPanel server SSH port"
echo -e "Press Enter key to use port 22 as default."
printf "%s" "SSH port: "
read server_port
  re='^[0-9]+$'
  if [[ $server_port == "" ]] ; then
    server_port="22"
  elif [[ ! $server_port =~ $re ]] ; then
   echo -e "\nPlease input a valid port number."
  fi
echo -e "\nSSH port is set to $server_port..."
echo -e "\nPlease input the user name , this must be root user or sudo user."
echo -e "Press Enter key to use root user as default."
printf "%s" "Username: "
read user_name
  if [[ $user_name == "" ]] ; then
    echo -e "\nset username to root..."
    user_name="root"
    sudoer=""
  elif [[ $user_name == "root" ]] ; then
    sudoer=""
  else
    sudoer="sudo -S"
  fi
#ask user to input server IP , port and user name

echo -e "\nlogin username is set to $user_name"
if grep -q "PRIVATE KEY" /root/.ssh/cyberpanel_migration_key 2>/dev/null ; then
  status=$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key echo ok 2>&1)
  if [[ $status == ok ]] ; then
    echo -e "\nvalid key detected..."
    return
  else
    echo -e "\nunable to connect to remote server..."
    clean_up
    exit
  fi
fi

echo -e "\nPlease input the password , if you are using public key authentication,please press Enter key."
printf "%s" "Password: "
stty -echo
read password
stty echo
echo ""

if [[ $password == "" ]] ; then
echo -e "\nPlease input the private key file with absolute path"
echo -e "\ne.g. /root/.ssh/id_rsa"
printf "%s" "key path: "
read password
fi

if [[ $password == "" ]] ; then
echo -e "Please enter a valid path."
exit
fi

if [[ -f $password ]] ; then
#check the input , if it's a file , consider it as key.
  ssh -o StrictHostKeyChecking=no $user_name@$server_ip -p$server_port -i $password "$sudoer wget -q -O /root/key.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/CPScripts/EasyEngine/key.sh ; $sudoer bash /root/key.sh enable"
  if [[ $? == "0" ]] ; then
    ssh -o StrictHostKeyChecking=no $user_name@$server_ip -p$server_port -i $password "$sudoer cat /root/.ssh/cyberpanel_migration_key" > /root/.ssh/cyberpanel_migration_key
      if [[ $? == "0" ]] ; then
        chmod 400 /root/.ssh/cyberpanel_migration_key
        status=$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key echo ok 2>&1)
        if [[ $status == ok ]] ; then
          echo -e "\nvalid key detected..."
        else
          echo -e "\nunabel to connect remote server..."
          clean_up
          exit
        fi
      else
        clean_up
        echo -e "\nunable to set remote key..."
        exit
      fi
  else
    echo -e "\nunable to set up the key, please manually set it up..."
    clean_up
    exit
  fi
else
#if it's not file , consider it as password
  sshpass -p "${password}" ssh -o StrictHostKeyChecking=no $user_name@$server_ip -p$server_port "$sudoer wget -q -O /root/key.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/CPScripts/EasyEngine/key.sh ; $sudoer bash /root/key.sh enable"
  if [[ $? == "0" ]] ; then
    sshpass -p "${password}" ssh -o StrictHostKeyChecking=no $user_name@$server_ip -p$server_port "$sudoer cat /root/.ssh/cyberpanel_migration_key" > /root/.ssh/cyberpanel_migration_key
    chmod 400 /root/.ssh/cyberpanel_migration_key
    status=$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key echo ok 2>&1)
    if [[ $status == ok ]] ; then
      echo -e "\nvalid key detected..."
    else
      echo -e "\nunabel to connect remote server..."
      clean_up
      exit
    fi
  else
    echo -e "\nunable to set up the key, please manually set it up..."
    clean_up
    exit
  fi
fi
}

install_lscwp() {
ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"

$ssh_v "ls -l /usr/bin/wp"
if [[ $? != "0" ]] ; then
  $ssh_v "$sudoer wget -O /usr/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar"
  $ssh_v "$sudoer chmod +x /usr/bin/wp"
fi
#install WP CLI if not yet installed.
$ssh_v "sudo -u $owner_user -i -- wp --path=/home/${domains[$i]}/public_html plugin install litespeed-cache"
echo -e "\nInstalling LiteSpeed Cache for WordPress..."

}

export_database() {
WPDBNAME=`cat /opt/easyengine/sites/${domains[$i]}/app/wp-config.php | grep DB_NAME | cut -d \' -f 4`
WPDBUSER=`cat /opt/easyengine/sites/${domains[$i]}/app/wp-config.php | grep DB_USER | cut -d \' -f 4`
WPDBPASS=`cat /opt/easyengine/sites/${domains[$i]}/app/wp-config.php | grep DB_PASSWORD | cut -d \' -f 4`
#get database name , user and password for mysqldump

echo -e "\nstarting to export database..."
USER="root"
PASSWORD=`cat /opt/easyengine/services/docker-compose.yml | grep MYSQL_ROOT_PASSWORD | awk -F'=' '{print $2}'`
OUTPUT="$DIR_TMP/database"
DOCKERDatabaseID=`docker ps | grep -e 'services_global-db' | cut -c1-12;`

databases=`docker exec $DOCKERDatabaseID bash -c "mysql -h localhost --user=$USER --password=$PASSWORD -e 'show databases;'" | tr -d "| " | grep -v Database`

for db in $databases; do
    if [[ $db == "$WPDBNAME" ]] ; then
    echo -e "\ndumping database for ${domains[$i]}..."
        sudo docker exec $DOCKERDatabaseID bash -c "/usr/bin/mysqldump -u $USER -p$PASSWORD --databases $db" > $OUTPUT/$db.sql
        database_name="$db.sql"
          if [[ $? == "0" ]] ; then
            echo -e "\ndatabase successfully exported..."
          else
            echo -e "\nfailed to export database..."
            clean_up
            exit
          fi
    fi
done
#credit to https://community.easyengine.io/t/cant-create-mysqldump/12306

}


check_dir () {
if [[ ! -d /opt/easyengine/sites ]] ; then
  echo -e "\ncan not detect sites directory..."
  exit
fi

if [[ -d $DIR_TMP ]] ; then
  rm -rf $DIR_TMP
fi
  mkdir $DIR_TMP
  mkdir $DIR_TMP/database
}

show_help() {
echo -e "\nEasyEngine to CyberPanel Migration Script"
echo -e "\nThis script will do:"
echo -e "\n1. Generate public key and private key for root user on remote CyberPanel server."
echo -e "2. Find the Wordpress sites hosting on this EasyEngine server"
echo -e "3. Export the site's database and its SSL cert/key if available and trasnfer to remote CyberPanel server."
echo -e "4. Create website with same domain on remote CyberPanel server and its related database."
echo -e "5. Import database dump and set up SSL cert/key if available"
echo -e "6. Download LiteSpeed Cache plugin for Wordpress, but it will not be enabled until you activate it."
echo -e "7. Install PHP extension sodium imagick redis and memcached."
echo -e "8. Once the migration process is completed, previously generated key will be removed on remote CyberPanel server."
echo -e "9. All the temporary generated files on this server will also be cleaned up."
echo -e "\nOnce migration is completed, you can use local host file to override the DNS record to test site on remote CyberPanel server"
echo -e "without effecting your live site"
echo -e "\nNo file on this server will be touched.\n"
read -rsn1 -p "Please press any key to continue..."
}

db_length_check() {
  ssh_v="ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key"
  output=$($ssh_v "$sudoer cat /usr/local/CyberCP/plogical/mysqlUtilities.py")
  if echo $output | grep -q "should be 16 at max" ; then
    echo -e "\nPlease upgrade your CyberPanel to latest first..."
    clean_up
    exit
  fi
}

check_dir
#check if this is an easyengine server and create a temp dir for storing files during the process.

show_help

declare -a domains

for i in $(ls /opt/easyengine/sites);
  do
    domains=("${domains[@]}" "$i")
  done

echo -e "\n\nsearching websites..."
echo -e "\ntotal number of domains: ${#domains[@]}"
echo -e "\ndomain list: ${domains[@]}"

dpkg -l sshpass > /dev/null
echo -e "\n\nchecking necessary package..."
  if [[ $? == "0" ]] ; then
    echo -e "\nsshpass package already installed...\n"
  else
    apt update
    DEBIAN_FRONTEND=noninteractive apt install -y sshpass
    if [[ $? == "0" ]] ; then
      echo -e "\nsshpass successfully installed...\n"
    else
      echo -e "\nunable to install sshpass...\n"
      exit
    fi
  fi

fetch_cyberpanel_key
#function to get cyberpanel server key so future SSH command won't require password input.

db_length_check

tLen=${#domains[@]}
#get the domain list and number of domains.

for (( i=0; i<${tLen}; i++ ));
  do
    # ${domains[$i]}  , domain name variable
    #create a file to save variable to source in cyberpanel server to read it.

    export_database
    #dump all sites' database

    export_cert
    #find the cert for this domain

    create_site_cyberpanel

    fix_permission

    trasnfer_file

    create_database

    set_header

    install_lscwp

    set_ssl_cyberpanel
  done
#for loop to run each function for each domain.

ssh -o StrictHostKeyChecking=no root@$server_ip -p$server_port -i /root/.ssh/cyberpanel_migration_key "$sudoer wget -q -O /root/ext.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/CPScripts/EasyEngine/ext.sh ; $sudoer bash /root/ext.sh"
#install some php ext

show_cyberpanel_site

clean_up
#remove all the files in tmp dir after script is done.
exit
