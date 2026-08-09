#!/usr/bin/env bash
# CyberPanel upgrade – repository setup (CentOS/AlmaLinux/Ubuntu/openEuler). Sourced by cyberpanel_upgrade.sh.

Pre_Upgrade_Setup_Repository() {
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pre_Upgrade_Setup_Repository started for OS: $Server_OS" | tee -a /var/log/cyberpanel_upgrade_debug.log

if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] ; then
  # Reduce dnf/yum timeouts and mirror issues (e.g. ftp.lip6.fr connection timeout)
  for dnf_conf in /etc/dnf/dnf.conf /etc/yum.conf; do
    if [[ -f "$dnf_conf" ]]; then
      grep -q '^timeout=' "$dnf_conf" 2>/dev/null || echo 'timeout=120' >> "$dnf_conf"
      grep -q '^minrate=' "$dnf_conf" 2>/dev/null || echo 'minrate=1000' >> "$dnf_conf"
      grep -q '^retries=' "$dnf_conf" 2>/dev/null || echo 'retries=5' >> "$dnf_conf"
      break
    fi
  done
  # For AlmaLinux 9: switch to repo.almalinux.org baseurl to avoid "Cannot find valid baseurl for repo: appstream"
  if [[ "$Server_OS" = "AlmaLinux9" ]] && [[ -d /etc/yum.repos.d ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fixing AlmaLinux 9 repos (appstream/baseos) for reliable mirror access" | tee -a /var/log/cyberpanel_upgrade_debug.log
    ALMA_VER="${Server_OS_Version:-9}"
    ARCH="x86_64"
    ALMA_BASE="https://repo.almalinux.org/almalinux/${ALMA_VER}"
    for repo in /etc/yum.repos.d/almalinux*.repo /etc/yum.repos.d/AlmaLinux*.repo; do
      [[ ! -f "$repo" ]] && continue
      if grep -q '^mirrorlist=' "$repo" 2>/dev/null; then
        sed -i 's|^mirrorlist=|#mirrorlist=|g' "$repo"
        sed -i 's|^#\s*baseurl=\(.*repo\.almalinux\.org.*\)|baseurl=\1|' "$repo"
        sed -i 's|^#baseurl=\(.*repo\.almalinux\.org.*\)|baseurl=\1|' "$repo"
      fi
    done
    # Ensure appstream/baseos have explicit baseurl; support [appstream], [almalinux-appstream], etc.
    for repofile in /etc/yum.repos.d/almalinux.repo /etc/yum.repos.d/almalinux*.repo /etc/yum.repos.d/AlmaLinux*.repo; do
      [[ ! -f "$repofile" ]] && continue
      for section in appstream almalinux-appstream AppStream; do
        if grep -q "^\[${section}\]" "$repofile" 2>/dev/null; then
          sed -i "/^\[${section}\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=${ALMA_BASE}/AppStream/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
          if ! sed -n "/^\[${section}\]/,/^\[/p" "$repofile" | grep -q '^baseurl='; then
            sed -i "/^\[${section}\]/a baseurl=${ALMA_BASE}/AppStream/${ARCH}/os/" "$repofile"
          fi
        fi
      done
      for section in baseos almalinux-baseos BaseOS; do
        if grep -q "^\[${section}\]" "$repofile" 2>/dev/null; then
          sed -i "/^\[${section}\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=${ALMA_BASE}/BaseOS/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
          if ! sed -n "/^\[${section}\]/,/^\[/p" "$repofile" | grep -q '^baseurl='; then
            sed -i "/^\[${section}\]/a baseurl=${ALMA_BASE}/BaseOS/${ARCH}/os/" "$repofile"
          fi
        fi
      done
      for section in crb extras; do
        if grep -q "^\[${section}\]" "$repofile" 2>/dev/null; then
          [[ "$section" = "crb" ]] && path="CRB" || path="extras"
          sed -i "/^\[${section}\]/,/^\[/ { s|^#\?baseurl=.*|baseurl=${ALMA_BASE}/${path}/${ARCH}/os/|; s|^mirrorlist=.*|#mirrorlist=disabled| }" "$repofile"
          if ! sed -n "/^\[${section}\]/,/^\[/p" "$repofile" | grep -q '^baseurl='; then
            sed -i "/^\[${section}\]/a baseurl=${ALMA_BASE}/${path}/${ARCH}/os/" "$repofile"
          fi
        fi
      done
    done
    # Fallback: create override with same repo IDs (loads last via zz- prefix, overrides broken config)
    if ! dnf makecache --quiet 2>/dev/null; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] dnf makecache failed, creating AlmaLinux repo override" | tee -a /var/log/cyberpanel_upgrade_debug.log
      cat > /etc/yum.repos.d/zz-almalinux-cyberpanel-fix.repo << EOF
[baseos]
name=AlmaLinux ${ALMA_VER} - BaseOS
baseurl=${ALMA_BASE}/BaseOS/${ARCH}/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-AlmaLinux-9

[appstream]
name=AlmaLinux ${ALMA_VER} - AppStream
baseurl=${ALMA_BASE}/AppStream/${ARCH}/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-AlmaLinux-9

[extras]
name=AlmaLinux ${ALMA_VER} - Extras
baseurl=${ALMA_BASE}/extras/${ARCH}/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-AlmaLinux-9

[crb]
name=AlmaLinux ${ALMA_VER} - CRB
baseurl=${ALMA_BASE}/CRB/${ARCH}/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-AlmaLinux-9
EOF
      dnf makecache --quiet 2>/dev/null || true
    fi
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Setting up repositories for $Server_OS..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  rm -f /etc/yum.repos.d/CyberPanel.repo
  rm -f /etc/yum.repos.d/litespeed.repo
  if [[ "$Server_Country" = "CN" ]] ; then
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed_cn.repo
  else
    curl -o /etc/yum.repos.d/litespeed.repo https://cyberpanel.sh/litespeed/litespeed.repo
  fi
  yum clean all
  if [[ -z "$Skip_System_Update" ]]; then
    yum update -y
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M-%S")] Skipping yum update (--no-system-update)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  yum autoremove epel-release -y
  rm -f /etc/yum.repos.d/epel.repo
  rm -f /etc/yum.repos.d/epel.repo.rpmsave
  yum autoremove epel-release -y
#all pre-upgrade operation for CentOS 8+

  if [[ "$Server_OS_Version" = "8" ]] ; then
#    cat <<EOF >/etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo
#[powertools-for-cyberpanel]
#name=CentOS Linux \$releasever - PowerTools
#mirrorlist=http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=PowerTools&infra=\$infra
#baseurl=http://mirror.centos.org/\$contentdir/\$releasever/PowerTools/\$basearch/os/
#gpgcheck=1
#enabled=1
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
#EOF
  rm -f /etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo

  if [[ "$Server_Country" = "CN" ]] ; then
    dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  else
    dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el8.noarch.rpm
  fi

  dnf install epel-release -y

  dnf install -y wget strace htop net-tools telnet which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils 2>/dev/null || dnf install -y --allowerasing wget strace htop net-tools telnet which bc htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils
  dnf install gpgme-devel -y 2>/dev/null || true
  dnf install python3 -y

  elif [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] ; then
  rm -f /etc/yum.repos.d/CentOS-PowerTools-CyberPanel.repo

  if [[ "$Server_Country" = "CN" ]] ; then
    dnf --nogpg install -y https://cyberpanel.sh/mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el9.noarch.rpm
  else
    dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el9.noarch.rpm
  fi

  dnf install epel-release -y 2>/dev/null || {
    # Fallback when appstream was broken or epel-release not in repo (e.g. AlmaLinux 9)
    if [[ "$Server_OS_Version" = "9" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing EPEL from Fedora RPM (epel-release not in repo)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm 2>/dev/null || true
    fi
  }

  # MariaDB repo for EL8/EL9/EL10: MariaDB.org packages, DNF module handling, full RPM set (see 03_mariadb.sh).
  if [[ "$Server_OS_Version" = "8" ]] || [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
    CyberPanel_EL89_Apply_MariaDB_Repository_And_Packages
  fi

  # AlmaLinux 9 specific package installation (MariaDB handled above when Server_OS_Version is 9)
  if [[ "$Server_OS" = "AlmaLinux9" ]] ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing AlmaLinux 9 specific packages (Development Tools, PHP deps)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Install essential build tools
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running: dnf groupinstall -y 'Development Tools' (may take a few minutes)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    dnf groupinstall -y 'Development Tools'
    
    # Install PHP dependencies that are missing on AlmaLinux 9
    dnf install -y ImageMagick ImageMagick-devel gd gd-devel libicu libicu-devel \
                   oniguruma oniguruma-devel aspell aspell-devel libc-client libc-client-devel \
                   libmemcached libmemcached-devel freetype-devel libjpeg-turbo-devel \
                   libpng-devel libwebp-devel libXpm-devel libzip-devel openssl-devel \
                   sqlite-devel libxml2-devel libxslt-devel curl-devel libedit-devel \
                   readline-devel pkgconfig cmake gcc-c++

    # Install additional required packages (omit curl - AlmaLinux 9 has curl-minimal, avoid conflict)
    dnf install -y wget unzip zip rsync firewalld psmisc git python3 python3-pip python3-devel 2>/dev/null || dnf install -y --allowerasing wget unzip zip rsync firewalld psmisc git python3 python3-pip python3-devel
  fi

  # Omit curl to avoid conflict with curl-minimal on AlmaLinux 9; curl-devel for build is separate
  dnf install -y wget strace htop net-tools telnet which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils 2>/dev/null || dnf install -y --allowerasing wget strace htop net-tools telnet which bc htop libevent-devel gcc libattr-devel xz-devel mariadb-connector-c-devel curl-devel git platform-python-devel tar socat bind-utils
  dnf install gpgme-devel -y 2>/dev/null || true
  dnf install python3 -y
  fi
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Setting up Ubuntu repositories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Ensure nobody group exists (required for various operations)
  if ! getent group nobody > /dev/null 2>&1 ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating 'nobody' group..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    groupadd nobody
  fi

  apt update -y
  if [[ -z "$Skip_System_Update" ]]; then
    export DEBIAN_FRONTEND=noninteractive ; apt-get -o Dpkg::Options::="--force-confold" upgrade -y
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Skipping apt upgrade (--no-system-update)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

  # MariaDB: add official repo and install/upgrade to chosen version on Ubuntu/Debian (any version)
  if [[ -n "$MARIADB_VER_REPO" ]]; then
    Maybe_Backup_MariaDB_Before_Upgrade
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Configuring MariaDB $MARIADB_VER_REPO repo for Ubuntu/Debian (version $MARIADB_VER)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | bash -s -- --mariadb-server-version="$MARIADB_VER_REPO" 2>/dev/null || true
    # Must run apt-get update after adding repo so 11.8 packages are visible (otherwise apt keeps 10.11)
    apt-get update -qq 2>/dev/null || apt-get update
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y mariadb-server mariadb-client 2>/dev/null || true
    apt-get install -y -o Dpkg::Options::="--force-confold" mariadb-server mariadb-client 2>/dev/null || true
    systemctl restart mariadb 2>/dev/null || systemctl restart mysql 2>/dev/null || true
    if [[ "$Migrate_MariaDB_To_UTF8_Requested" = "yes" ]] && { [[ "$MARIADB_VER_REPO" =~ ^11\. ]] || [[ "$MARIADB_VER_REPO" =~ ^12\. ]]; }; then
      Migrate_MariaDB_To_UTF8
    fi
  fi

  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]] ; then
    if [[ "$Server_OS_Version" = "24" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Ubuntu 24.04 specific packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Ubuntu 22.04 specific packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    # Install Python development packages required for virtualenv on Ubuntu 22.04/24.04
    DEBIAN_FRONTEND=noninteractive apt install -y python3-dev python3-venv python3-pip python3-setuptools python3-wheel
    DEBIAN_FRONTEND=noninteractive apt install -y dnsutils net-tools htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev libidn2-0-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcomerr2 libldap2-dev virtualenv git socat vim unzip zip libmariadb-dev-compat libmariadb-dev

  else
    DEBIAN_FRONTEND=noninteractive apt install -y htop telnet libcurl4-gnutls-dev libgnutls28-dev libgcrypt20-dev libattr1 libattr1-dev liblzma-dev libgpgme-dev libmariadb-dev-compat libmariadb-dev libcurl4-gnutls-dev libssl-dev nghttp2 libnghttp2-dev idn2 libidn2-dev librtmp-dev libpsl-dev nettle-dev libgnutls28-dev libldap2-dev libgssapi-krb5-2 libk5crypto3 libkrb5-dev libcom-err2 libldap2-dev virtualenv git dnsutils
  fi
  DEBIAN_FRONTEND=noninteractive apt install -y python3-pip
  DEBIAN_FRONTEND=noninteractive apt install -y build-essential libssl-dev libffi-dev python3-dev
  DEBIAN_FRONTEND=noninteractive apt install -y python3-venv

  ### fix for pip issue on ubuntu 22 and 24

  apt-get remove --purge virtualenv -y
  # Handle Ubuntu 24.04's externally-managed-environment policy
  if [[ "$Server_OS_Version" = "24" ]]; then
    echo -e "Ubuntu 24.04 detected - using apt for virtualenv installation"
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-virtualenv
  else
    pip uninstall -y virtualenv 2>/dev/null || true
    rm -rf /usr/lib/python3/dist-packages/virtualenv*
    pip3 install --upgrade virtualenv
  fi


  if [[ "$Server_OS_Version" = "18" ]] ; then
    :
#all pre-upgrade operation for Ubuntu 18
  elif [[ "$Server_OS_Version" = "20" ]] ; then
#    if ! grep -q "focal" /etc/apt/sources.list.d/dovecot.list ; then
#      sed -i 's|ce-2.3-latest/ubuntu/bionic bionic main|ce-2.3-latest/ubuntu/focal focal main|g' /etc/apt/sources.list.d/dovecot.list
#      rm -rf /etc/dovecot-backup
#      cp -r /etc/dovecot /etc/dovecot-backup
#      apt update
#      DEBIAN_FRONTEND=noninteractive apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" remove -y dovecot-mysql dovecot-pop3d dovecot-imapd
#      DEBIAN_FRONTEND=noninteractive apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install -y dovecot-mysql dovecot-pop3d dovecot-imapd
#      systemctl restart dovecot
#    fi
    #fix ubuntu 20 webmail login issue

    rm -f /etc/apt/sources.list.d/dovecot.list
    apt update
    DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y
  fi
#all pre-upgrade operation for Ubuntu 20
fi
if [[ "$Server_OS" = "openEuler" ]] ; then
  rm -f /etc/yum.repos.d/CyberPanel.repo
  rm -f /etc/yum.repos.d/litespeed.repo

  yum clean all
  yum update -y

  dnf install -y wget strace htop net-tools telnet curl which bc telnet htop libevent-devel gcc libattr-devel xz-devel mariadb-devel curl-devel git python3-devel tar socat bind-utils
  dnf install gpgme-devel -y
  dnf install python3 -y
fi
#all pre-upgrade operation for openEuler

  # Ensure MariaDB client no-SSL on every upgrade path (install and upgrade; avoids ERROR 2026)
  Ensure_MariaDB_Client_No_SSL
}

