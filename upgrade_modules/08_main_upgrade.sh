#!/usr/bin/env bash
# CyberPanel upgrade – main upgrade (Python, upgrade.py, venv, WSGI). Sourced by cyberpanel_upgrade.sh.

Main_Upgrade() {
echo -e "\n[$(date +"%Y-%m-%d %H:%M:%S")] Starting Main_Upgrade function..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Resolve Python for upgrade (avoid FileNotFoundError when /usr/local/CyberPanel/bin/python missing)
CP_PYTHON=""
for py in /usr/local/CyberPanel/bin/python /usr/local/CyberCP/bin/python /usr/bin/python3 /usr/local/bin/python3; do
  if [[ -x "$py" ]]; then CP_PYTHON="$py"; break; fi
done
if [[ -z "$CP_PYTHON" ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: No Python found for upgrade (tried CyberPanel, CyberCP, python3)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  exit 1
fi
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Using Python: $CP_PYTHON" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Ensure ols_binaries_config exists (required by upgrade.py; may be missing when upgrading from older versions)
mkdir -p /usr/local/CyberCP/install
if [[ ! -f /usr/local/CyberCP/install/ols_binaries_config.py ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading ols_binaries_config.py (required for upgrade)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  wget -q -O /usr/local/CyberCP/install/ols_binaries_config.py "${Git_Content_URL}/${Branch_Name}/install/ols_binaries_config.py" 2>/dev/null || \
  curl -sL -o /usr/local/CyberCP/install/ols_binaries_config.py "${Git_Content_URL}/${Branch_Name}/install/ols_binaries_config.py" 2>/dev/null || true
fi
if [[ ! -f /usr/local/CyberCP/install/ols_binaries_config.py ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: ols_binaries_config.py not found; upgrade.py may fail with ModuleNotFoundError" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running: $CP_PYTHON upgrade.py $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Run upgrade.py and capture output
upgrade_output=$("$CP_PYTHON" upgrade.py "$Branch_Name" 2>&1)
RETURN_CODE=$?
echo "$upgrade_output" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check for TypeError specifically
if echo "$upgrade_output" | grep -q "TypeError: expected string or bytes-like object"; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: TypeError detected in upgrade.py, but continuing..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    # Check if upgrade actually completed despite the error
    if echo "$upgrade_output" | grep -q "Upgrade Completed"; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Upgrade completed despite TypeError" | tee -a /var/log/cyberpanel_upgrade_debug.log
        RETURN_CODE=0
    fi
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Python upgrade.py returned code: $RETURN_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check if the command was successful (return code 0)
if [ $RETURN_CODE -eq 0 ]; then
    echo "Upgrade successful."
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] First upgrade attempt successful" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] First upgrade attempt failed with code $RETURN_CODE, starting fallback..." | tee -a /var/log/cyberpanel_upgrade_debug.log


    if [ -e /usr/bin/pip3 ]; then
    PIP3="/usr/bin/pip3"
  else
    PIP3="pip3.6"
  fi

  rm -rf /usr/local/CyberPanelTemp
  
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating temporary virtual environment for fallback upgrade..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Try python3 -m venv first (more reliable on Ubuntu 22.04)
  if python3 -m venv --system-site-packages /usr/local/CyberPanelTemp 2>/dev/null; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Temporary virtualenv created with python3 -m venv" | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    # Fallback to virtualenv command
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Trying virtualenv command for temporary environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanelTemp 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

# shellcheck disable=SC1091
. /usr/local/CyberPanelTemp/bin/activate

wget -O /usr/local/requirments-old.txt "${Git_Content_URL}/${Branch_Name}/requirments-old.txt"

    if [[ "$Server_OS" = "CentOS" ]] ; then
#  $PIP3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  $PIP3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberPanelTemp/bin/activate
    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
elif [[ "$Server_OS" = "openEuler" ]] ; then
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments-old.txt
    Check_Return
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running fallback: /usr/local/CyberPanelTemp/bin/python upgrade.py $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log
/usr/local/CyberPanelTemp/bin/python upgrade.py "$Branch_Name" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
FALLBACK_CODE=$?
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fallback upgrade returned code: $FALLBACK_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
Check_Return

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing temporary environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -rf /usr/local/CyberPanelTemp

fi

echo -e "\n[$(date +"%Y-%m-%d %H:%M:%S")] Starting post-upgrade cleanup..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Check if we need to recreate due to Python 2
NEEDS_RECREATE=0
if [[ -f /usr/local/CyberCP/bin/python2 ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Found Python 2 in CyberCP, will recreate with Python 3..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  NEEDS_RECREATE=1
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing old CyberCP virtual environment directories..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -rf /usr/local/CyberCP/bin
rm -rf /usr/local/CyberCP/lib
rm -rf /usr/local/CyberCP/lib64
rm -rf /usr/local/CyberCP/pyvenv.cfg

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking CyberCP virtual environment status after cleanup..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# After removing directories, we always need to recreate
if [[ $NEEDS_RECREATE -eq 1 ]] || [[ ! -d /usr/local/CyberCP/bin ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating/recreating CyberCP virtual environment with Python 3..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # First ensure the directory exists
  mkdir -p /usr/local/CyberCP
  
  # For Ubuntu 22.04+, we need to handle virtualenv differently
  VENV_SUCCESS=0
  
  # First try using python3 -m venv (more reliable on Ubuntu 22.04)
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Attempting to create virtual environment using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  virtualenv_output=$(python3 -m venv --system-site-packages /usr/local/CyberCP 2>&1)
  VENV_CODE=$?
  echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  if [[ $VENV_CODE -eq 0 ]] && [[ -f /usr/local/CyberCP/bin/activate ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtual environment created successfully using python3 -m venv" | tee -a /var/log/cyberpanel_upgrade_debug.log
    VENV_SUCCESS=1
  else
    # If that fails, try virtualenv command
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] python3 -m venv failed, trying virtualenv command..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # On Ubuntu 22.04, we need to ensure proper virtualenv installation
    if [[ "$Server_OS" = "Ubuntu" ]] && [[ "$Server_OS_Version" = "22" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 22.04 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  elif [[ "$Server_OS" = "CentOS" ]] && ([[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]); then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky Linux 9/10 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  elif [[ "$Server_OS" = "AlmaLinux9" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux 9 detected, ensuring virtualenv is properly installed..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    pip3 install --upgrade virtualenv 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    
    # Find the correct python3 path
    if [[ "$Server_OS" = "CentOS" ]] && ([[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]); then
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Using Python path: $PYTHON_PATH" | tee -a /var/log/cyberpanel_upgrade_debug.log
      virtualenv_output=$(virtualenv -p "$PYTHON_PATH" /usr/local/CyberCP 2>&1)
    elif [[ "$Server_OS" = "AlmaLinux9" ]]; then
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux 9 - Using Python path: $PYTHON_PATH" | tee -a /var/log/cyberpanel_upgrade_debug.log
      virtualenv_output=$(virtualenv -p "$PYTHON_PATH" /usr/local/CyberCP 2>&1)
    else
      virtualenv_output=$(virtualenv -p /usr/bin/python3 /usr/local/CyberCP 2>&1)
    fi
    VENV_CODE=$?
    echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Check if TypeError occurred (common on Ubuntu 22.04)
    if echo "$virtualenv_output" | grep -q "TypeError"; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: TypeError detected, attempting workaround..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      
      # Try alternative method using explicit system-site-packages
      virtualenv_output=$(virtualenv --python=/usr/bin/python3 --system-site-packages /usr/local/CyberCP 2>&1)
      VENV_CODE=$?
      echo "$virtualenv_output" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
    
    if [[ -f /usr/local/CyberCP/bin/activate ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtual environment created successfully" | tee -a /var/log/cyberpanel_upgrade_debug.log
      VENV_SUCCESS=1
      VENV_CODE=0
    fi
  fi
  
  if [[ $VENV_SUCCESS -eq 0 ]]; then
    VENV_CODE=1
  fi
  
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Virtualenv creation returned code: $VENV_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  if [[ $VENV_CODE -ne 0 ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] FATAL: Virtualenv creation failed with code $VENV_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo -e "Virtualenv creation failed. Please check the logs at /var/log/cyberpanel_upgrade_debug.log"
    exit $VENV_CODE
  fi
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] CyberCP virtualenv already exists, skipping recreation" | tee -a /var/log/cyberpanel_upgrade_debug.log
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberCP...\n"
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Removing old requirements file..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -f /usr/local/requirments.txt

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading new requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
Download_Requirement

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing Python packages..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [ "$Server_OS" = "Ubuntu" ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu detected, activating virtual environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  # shellcheck disable=SC1091
  . /usr/local/CyberCP/bin/activate 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  ACTIVATE_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Activate returned code: $ACTIVATE_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Upgrading setuptools and packaging..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip install --upgrade setuptools packaging 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  PIP_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pip install returned code: $PIP_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Non-Ubuntu OS, activating virtual environment..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  # shellcheck disable=SC1091
  source /usr/local/CyberCP/bin/activate 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  ACTIVATE_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Activate returned code: $ACTIVATE_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  /usr/local/CyberCP/bin/pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  PIP_CODE=$?
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Pip install returned code: $PIP_CODE" | tee -a /var/log/cyberpanel_upgrade_debug.log
  Check_Return
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Verifying Django installation..." | tee -a /var/log/cyberpanel_upgrade_debug.log
# Test if Django is installed
if ! /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Django not found, installing requirements again..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  
  # Re-activate virtual environment
  source /usr/local/CyberCP/bin/activate
  
  # Install MySQL/MariaDB development headers for mysqlclient Python package
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing MySQL/MariaDB development headers..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  if [[ "$Server_OS" = "Ubuntu" ]] || [[ "$Server_OS" = "Debian" ]]; then
    # Ubuntu/Debian
    apt-get update -y
    apt-get install -y libmariadb-dev libmariadb-dev-compat pkg-config build-essential
  elif [[ "$Server_OS" =~ ^(CentOS|RHEL|AlmaLinux|RockyLinux|CloudLinux) ]]; then
    # RHEL-based systems
    if command -v dnf >/dev/null 2>&1; then
      # Remove conflicting packages first
      dnf remove -y mariadb mariadb-client-utils mariadb-server || true
      dnf remove -y MariaDB-server MariaDB-client MariaDB-devel || true
      
      # Install development packages with conflict resolution
      dnf install -y --allowerasing --skip-broken --nobest mariadb-devel pkgconfig gcc python3-devel || \
      dnf install -y --allowerasing --skip-broken --nobest mysql-devel pkgconfig gcc python3-devel || \
      dnf install -y --allowerasing --skip-broken --nobest mariadb-devel mariadb-connector-c-devel pkgconfig gcc python3-devel
    else
      yum install -y mariadb-devel pkgconfig gcc python3-devel
    fi
  fi

  # Check if mysql.h is available and create symlink if needed
  if [[ ! -f "/usr/include/mysql/mysql.h" ]] && [[ -f "/usr/include/mariadb/mysql.h" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Creating mysql.h symlink for compatibility..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    mkdir -p /usr/include/mysql
    ln -sf /usr/include/mariadb/mysql.h /usr/include/mysql/mysql.h
  fi
  
  # Re-install requirements
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Re-installing Python requirements..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  pip install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Django is properly installed" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing WSGI-LSAPI with optimized compilation..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Save current directory
UPGRADE_CWD=$(pwd)

cd /tmp || exit
rm -rf wsgi-lsapi-2.1*

wget -q https://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
tar xf wsgi-lsapi-2.1.tgz
cd wsgi-lsapi-2.1 || exit

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Configuring WSGI..." | tee -a /var/log/cyberpanel_upgrade_debug.log
PYTHON_CFG="${CP_PYTHON:-/usr/bin/python3}"
[[ -x "$PYTHON_CFG" ]] || PYTHON_CFG="/usr/bin/python3"
"$PYTHON_CFG" ./configure.py 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log

# Fix Makefile to use proper optimization flags to avoid _FORTIFY_SOURCE warnings
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Optimizing Makefile for proper compilation..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if [[ -f Makefile ]]; then
    # Replace -O0 -g3 with -O2 -g to satisfy _FORTIFY_SOURCE
    sed -i 's/-O0 -g3/-O2 -g/g' Makefile
    # Ensure we have proper optimization flags
    if grep -q "CFLAGS" Makefile && ! grep -qF '-O2' Makefile; then
        sed -i 's/CFLAGS =/CFLAGS = -O2/' Makefile
    fi
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Makefile optimized for proper compilation" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Compiling WSGI with optimized flags..." | tee -a /var/log/cyberpanel_upgrade_debug.log
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] (Upstream WSGI source may show harmless strncpy/gstate warnings; build can still succeed.)" | tee -a /var/log/cyberpanel_upgrade_debug.log
make clean 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
make 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Installing lswsgi binary..." | tee -a /var/log/cyberpanel_upgrade_debug.log
rm -f /usr/local/CyberCP/bin/lswsgi
cp lswsgi /usr/local/CyberCP/bin/
chmod +x /usr/local/CyberCP/bin/lswsgi

# Return to original directory
cd "$UPGRADE_CWD" || cd /root

# Final verification
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Running final verification..." | tee -a /var/log/cyberpanel_upgrade_debug.log
if /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null && [[ -f /usr/local/CyberCP/bin/lswsgi ]]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] All components successfully installed!" | tee -a /var/log/cyberpanel_upgrade_debug.log
else
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Some components may be missing, check logs" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi

echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Main_Upgrade function completed" | tee -a /var/log/cyberpanel_upgrade_debug.log
}

# Sync /usr/local/CyberCP to the latest commit of the upgrade branch so Version Management
# page shows Current commit matching Latest (avoids "please upgrade" when upgrade already ran).
# Backs up and restores CyberCP/settings.py so production DB/config are not overwritten by the repo.
