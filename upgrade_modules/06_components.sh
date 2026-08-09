#!/usr/bin/env bash
# CyberPanel upgrade – download requirements and required components (venv, pip, recovery). Sourced by cyberpanel_upgrade.sh.

Download_Requirement() {
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting Download_Requirement function..." | tee -a /var/log/cyberpanel_upgrade_debug.log
for i in {1..50};
  do
  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]] || [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
   echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading requirements.txt for OS version $Server_OS_Version" | tee -a /var/log/cyberpanel_upgrade_debug.log
   if command -v wget >/dev/null 2>&1; then wget -O /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log; else curl -sL -o /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log; fi
  else
   echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading requirements-old.txt for OS version $Server_OS_Version" | tee -a /var/log/cyberpanel_upgrade_debug.log
   if command -v wget >/dev/null 2>&1; then wget -O /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments-old.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log; else curl -sL -o /usr/local/requirments.txt "${Git_Content_URL}/${Branch_Name}/requirments-old.txt" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log; fi
  fi
  if grep -q "Django==" /usr/local/requirments.txt ; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Requirements file downloaded successfully" | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Fix pysftp dependency issue by removing it from requirements
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fixing pysftp dependency issue..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    sed -i 's/^pysftp$/# pysftp - deprecated, using paramiko instead/' /usr/local/requirments.txt
    sed -i 's/pysftp/# pysftp - deprecated, using paramiko instead/' /usr/local/requirments.txt
    
    break
  else
    echo -e "\n Requirement list has failed to download for $i times..."
    echo -e "Wait for 30 seconds and try again...\n"
    sleep 30
  fi
done
#special made function for Gitee.com, for whatever reason sometimes it fails to download this file
}



Pre_Upgrade_Required_Components() {

# Check if CyberCP directory exists but is incomplete/damaged
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checking CyberCP directory integrity..." | tee -a /var/log/cyberpanel_upgrade_debug.log

# Define essential CyberCP components (do not add /usr/local/CyberCP/manage - it does not exist; see usmannasir/cyberpanel#1721)
CYBERCP_ESSENTIAL_DIRS=(
    "/usr/local/CyberCP/CyberCP"
    "/usr/local/CyberCP/plogical"
    "/usr/local/CyberCP/websiteFunctions"
    "/usr/local/CyberCP/pluginHolder"
    "/usr/local/CyberCP/pluginInstaller"
)

CYBERCP_MISSING=0
for dir in "${CYBERCP_ESSENTIAL_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] INFO: Essential directory missing (will restore): $dir" | tee -a /var/log/cyberpanel_upgrade_debug.log
        CYBERCP_MISSING=1
    fi
done

# If essential directories are missing, perform automatic recovery (normal on some upgrade paths)
if [ $CYBERCP_MISSING -eq 1 ]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] INFO: Restoring missing CyberCP directories from repository..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    
    # Backup any remaining configuration files if they exist
    if [ -f "/usr/local/CyberCP/CyberCP/settings.py" ]; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backing up existing settings.py..." | tee -a /var/log/cyberpanel_upgrade_debug.log
        cp /usr/local/CyberCP/CyberCP/settings.py /tmp/cyberpanel_settings_backup.py
    fi
    
    # Clone fresh CyberPanel repository
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Cloning fresh CyberPanel repository for recovery..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    cd /usr/local
    rm -rf CyberCP_recovery_tmp
    
    if git clone "$Git_Clone_URL" CyberCP_recovery_tmp; then
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Repository cloned successfully for recovery" | tee -a /var/log/cyberpanel_upgrade_debug.log
        
        # Checkout the appropriate branch
        cd CyberCP_recovery_tmp
        git checkout "$Branch_Name" 2>/dev/null || git checkout stable
        
        # Copy missing components while preserving existing configurations
        for dir in "${CYBERCP_ESSENTIAL_DIRS[@]}"; do
            if [ ! -d "$dir" ]; then
                # Extract relative path after /usr/local/CyberCP/
                relative_path=${dir#/usr/local/CyberCP/}
                if [ -d "/usr/local/CyberCP_recovery_tmp/$relative_path" ]; then
                    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restoring missing directory: $dir" | tee -a /var/log/cyberpanel_upgrade_debug.log
                    mkdir -p "$(dirname "$dir")"
                    cp -r "/usr/local/CyberCP_recovery_tmp/$relative_path" "$dir"
                fi
            fi
        done
        
        # Restore settings.py if it was backed up
        if [ -f "/tmp/cyberpanel_settings_backup.py" ]; then
            echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restoring backed up settings.py..." | tee -a /var/log/cyberpanel_upgrade_debug.log
            cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
        fi
        
        # Clean up temporary clone
        rm -rf /usr/local/CyberCP_recovery_tmp
        
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Recovery completed. All essential CyberCP directories restored." | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Failed to clone repository for recovery" | tee -a /var/log/cyberpanel_upgrade_debug.log
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Please run full installation instead of upgrade" | tee -a /var/log/cyberpanel_upgrade_debug.log
        exit 1
    fi
    
    cd /root/cyberpanel_upgrade_tmp || cd /root
fi

if [ "$Server_OS" = "Ubuntu" ]; then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Preparing Ubuntu environment for virtualenv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  rm -rf /usr/local/CyberPanel
  
  # For Ubuntu 22.04 and 24.04, handle virtualenv installation properly
  if [[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]; then
    if [[ "$Server_OS_Version" = "24" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 24.04: Using apt for virtualenv installation (externally-managed-environment policy)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      # Ubuntu 24.04 has externally-managed-environment, use apt
      DEBIAN_FRONTEND=noninteractive apt-get install -y python3-virtualenv python3-venv
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu 22.04: Installing/upgrading virtualenv with proper dependencies..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      # Remove system virtualenv if it exists to avoid conflicts
      apt remove -y python3-virtualenv 2>/dev/null || true
      # Install latest virtualenv via pip
      pip3 install --upgrade pip setuptools wheel
      pip3 install --upgrade virtualenv
    fi
  else
    pip3 install --upgrade virtualenv
  fi
else
  # EL8–10: Python.h + mysql.h before any python3 -m venv under /usr/local/CyberPanel (see v2.5.5-dev hardening).
  if [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
    if [[ "$Server_OS_Version" = "8" ]] || [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      CyberCP_Upgrade_Ensure_Rhel_Venv_Build_Deps
    fi
  fi
  rm -rf /usr/local/CyberPanel
  # AlmaLinux 9/10, Rocky 9: use python3 -m venv (no virtualenv pkg needed)
  if [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version: will use python3 -m venv, skipping virtualenv package" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      if [ -e /usr/bin/pip3 ]; then PIP3="/usr/bin/pip3"; else PIP3="pip3.6"; fi
      $PIP3 install --default-timeout=3600 virtualenv
      Check_Return
    fi
  else
    if [ -e /usr/bin/pip3 ]; then PIP3="/usr/bin/pip3"; else PIP3="pip3.6"; fi
    $PIP3 install --default-timeout=3600 virtualenv
    Check_Return
  fi
fi

if [[ -f /usr/local/CyberPanel/bin/python2 ]]; then
  echo -e "\nPython 2 dectected, doing re-setup...\n"
  rm -rf /usr/local/CyberPanel/bin
  if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    python3 -m venv --system-site-packages /usr/local/CyberPanel
  elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
    if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
      python3 -m venv --system-site-packages /usr/local/CyberPanel
    else
      PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
      virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
    fi
  else
    virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
  fi
  Check_Return
elif [[ -d /usr/local/CyberPanel/bin/ ]]; then
  echo -e "\nNo need to re-setup virtualenv at /usr/local/CyberPanel...\n"
else
  #!/bin/bash

echo -e "\nNo existing virtualenv found; creating fresh Python environment...\n"

# Attempt to create a virtual environment
if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu $Server_OS_Version detected, using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
  python3 -m venv /usr/local/CyberPanel
elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
  if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] AlmaLinux/Rocky $Server_OS_Version: using python3 -m venv (no virtualenv pkg needed)..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    python3 -m venv --system-site-packages /usr/local/CyberPanel
  else
    PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
    virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
  fi
else
  virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
fi

# Check if the virtualenv/venv command failed
if [ $? -ne 0 ]; then
    echo "virtualenv command failed."

    # Check if the operating system is AlmaLinux
    if grep -q "AlmaLinux" /etc/os-release; then
        echo "Operating system is AlmaLinux."

        # Check if the 'packaging' module is installed via RPM
        if rpm -q python3-packaging >/dev/null 2>&1; then
            echo "'packaging' module installed via RPM. Proceeding with uninstallation."

            # Uninstall the 'packaging' module using RPM
            sudo dnf remove python3-packaging -y

            # Check if uninstallation was successful
            if [ $? -eq 0 ]; then
                echo "Successfully uninstalled 'packaging' module."

                # Install and upgrade 'packaging' using pip
                pip install --upgrade packaging

                # Verify the installation
                if [ $? -eq 0 ]; then
                    echo "'packaging' module reinstalled and upgraded successfully."
                    if [[ "$Server_OS" = "Ubuntu" ]] && ([[ "$Server_OS_Version" = "22" ]] || [[ "$Server_OS_Version" = "24" ]]); then
                        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Ubuntu: using python3 -m venv..." | tee -a /var/log/cyberpanel_upgrade_debug.log
                        python3 -m venv --system-site-packages /usr/local/CyberPanel
                    elif [[ "$Server_OS" = "CentOS" ]] || [[ "$Server_OS" = "AlmaLinux" ]] || [[ "$Server_OS" = "AlmaLinux9" ]] || [[ "$Server_OS" = "RockyLinux" ]]; then
                        if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]]; then
                          python3 -m venv --system-site-packages /usr/local/CyberPanel
                        else
                          PYTHON_PATH=$(which python3 2>/dev/null || which python3.9 2>/dev/null || echo "/usr/bin/python3")
                          virtualenv -p "$PYTHON_PATH" --system-site-packages /usr/local/CyberPanel
                        fi
                    else
                        virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
                    fi
                else
                    echo "Failed to install 'packaging' module using pip."
                fi
            else
                echo "Failed to uninstall 'packaging' module using RPM."
            fi
        else
            echo "'packaging' module is not installed via RPM. No action taken."
        fi
    else
        echo "Operating system is not AlmaLinux. No action taken."
    fi
else
    echo "virtualenv command executed successfully."
fi
fi

# shellcheck disable=SC1091
. /usr/local/CyberPanel/bin/activate
pip install --upgrade pip setuptools packaging

Download_Requirement

if [[ "$Server_OS" = "CentOS" ]] ; then
#  $PIP3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  $PIP3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "Ubuntu" ]] ; then
  # shellcheck disable=SC1091
  . /usr/local/CyberPanel/bin/activate
    Check_Return
#  pip3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
elif [[ "$Server_OS" = "openEuler" ]] ; then
#  pip3 install --default-timeout=3600 virtualenv==16.7.9
#    Check_Return
  pip3 install --default-timeout=3600 --ignore-installed -r /usr/local/requirments.txt
    Check_Return
fi

#virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberPanel
#  Check_Return

# raw.githubusercontent.com intermittently answers HTTP 429; validate before use (#1835).
# raw.githubusercontent.com intermittently answers HTTP 429; validate every staged source file.
Download_Upgrade_Source() {
  local Source_Path="$1"
  local Destination="$2"
  local Expected_Pattern="$3"

  for i in {1..3}; do
    rm -f "$Destination"
    wget -q -O "$Destination" "${Git_Content_URL}/${Branch_Name}/${Source_Path}"
    if grep -q -- "$Expected_Pattern" "$Destination" 2>/dev/null ; then
      return 0
    fi
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ${Destination} download failed or returned invalid content (attempt $i/3), GitHub may be rate limiting (HTTP 429). Retrying in 15 seconds..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    sleep 15
  done

  echo -e "\nFailed to download ${Destination} from ${Git_Content_URL}/${Branch_Name}/${Source_Path}"
  echo -e "This is usually a temporary GitHub rate limit (HTTP 429 Too Many Requests). Please retry the upgrade later.\n"
  return 1
}

Download_Upgrade_Source "plogical/upgrade.py" "upgrade.py" "^import " || exit 1
Download_Upgrade_Source "cyberpanel_version.py" "cyberpanel_version.py" "^VERSION" || exit 1

if [[ "$Server_Country" = "CN" ]] ; then
  sed -i 's|git clone https://github.com/usmannasir/cyberpanel|echo git cloned|g' upgrade.py

  Retry_Command "git clone ${Git_Clone_URL}"
    Check_Return "git clone ${Git_Clone_URL}"

  # shellcheck disable=SC2086
  sed -i 's|https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/install/litespeed/httpd_config.xml|'${Git_Content_URL}/${Branch_Name}'//install/litespeed/httpd_config.xml|g' upgrade.py
  sed -i 's|https://cyberpanel.sh/composer.sh|https://gitee.com/qtwrk/cyberpanel/raw/stable/install/composer_cn.sh|g' upgrade.py
fi

}

# (Pre_Upgrade_Setup_Git_URL is defined earlier; this duplicate removed so --repo is respected)

