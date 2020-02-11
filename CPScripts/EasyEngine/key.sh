#!/bin/bash

# script to set up access key for non-interactive SSH login

check_root() {
  if [[ $(id -u) != 0 ]]  > /dev/null; then
  	echo -e "\nYou must use root permission...\n"
  	exit
  fi
}

key_generation() {
rm -f /root/.ssh/cyberpanel_migration_key
rm -f /root/.ssh/cyberpanel_migration_key.pub
ssh-keygen -t rsa -N "" -f /root/.ssh/cyberpanel_migration_key
if [[ -f /root/.ssh/authorized_keys ]] ; then
  cp /root/.ssh/authorized_keys /root/.ssh/authorized_keys_migration
  string=$(head -c 3 /root/.ssh/authorized_keys)
  if [[ $string != "ssh" ]] ; then
    #check if it's like AWS that prohibits direct root login.
    rm -f /root/.ssh/authorized_keys
    cat /root/.ssh/cyberpanel_migration_key.pub > /root/.ssh/authorized_keys
  else
    cat /root/.ssh/cyberpanel_migration_key.pub >> /root/.ssh/authorized_keys
  fi
else
    cat /root/.ssh/cyberpanel_migration_key.pub > /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi

echo -e "\nsuccessfully set up public key and private key for migration..."
# this function creates public key and private key
}

ssh_config() {
rm -f /etc/ssh/sshd_config_migration
cp /etc/ssh/sshd_config /etc/ssh/sshd_config_migration
if grep -q "#PubkeyAuthentication yes" /etc/ssh/sshd_config ; then
  sed -i 's|#PubkeyAuthentication yes|PubkeyAuthentication yes|g' /etc/ssh/sshd_config
fi
systemctl restart sshd
#this function will modify ssh configuration to allow public key login and root login
}


revert_change() {
  if [[ ! -f /etc/ssh/sshd_config_migration ]] ; then
  echo -e "You didn't enable it..."
  exit
  else
  rm -f /root/.ssh/authorized_keys
  rm -f /etc/ssh/sshd_config
  rm -f /root/.ssh/cyberpanel_migration_key
  rm -f /root/.ssh/cyberpanel_migration_key.pub
  cp /etc/ssh/sshd_config_migration /etc/ssh/sshd_config
  if [[ -f /root/.ssh/authorized_keys_migration ]] ; then
    cp /root/.ssh/authorized_keys_migration /root/.ssh/authorized_keys
    rm -f /root/.ssh/authorized_keys_migration
  fi
  systemctl restart sshd
  fi
echo -e "\nsuccessfully removed public key and private key for migration..."

#this function will revert the changes and restore backed up files.
}

check_root


if [[ $1 == "enable" ]] ; then
  ssh_config
  key_generation
elif [[ $1 == "disable" ]] ; then
  revert_change
else
  echo -e "\nPlease use argument enable or disable"
  echo -e "\ne.g. ./key.sh enable\n"
fi
