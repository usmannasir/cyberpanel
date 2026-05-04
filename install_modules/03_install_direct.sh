#!/usr/bin/env bash
# CyberPanel install – install_cyberpanel_direct_cont (part 2). Sourced by cyberpanel.sh.

# Continuation of install_cyberpanel_direct (split for module size)
install_cyberpanel_direct_cont() {
    echo "  ✓ CyberPanel installation files downloaded"
    echo "  🔄 Starting CyberPanel installation..."
    echo ""
    echo "IMPORTANT: The installation is now running in the background."
    echo "You will see detailed output from the CyberPanel installer below."
    echo "This is normal and expected - the installation is proceeding!"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    # Run the installer with live progress monitoring
    echo "Starting CyberPanel installation process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Create log directory (same as v2.4.4: installer logs go here)
    mkdir -p /var/log/CyberPanel
    echo "  Installation logs:"
    echo "    • /var/log/CyberPanel/install.log       (installer script messages)"
    echo "    • /var/log/CyberPanel/install_output.log (Python installer stdout/stderr)"
    echo "    • /var/log/installLogs.txt              (install.py detailed log)"
    echo ""
    
    # Run the installer with live output monitoring
    echo "Starting CyberPanel installer with live progress monitoring..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    LIVE INSTALLATION PROGRESS"
    echo "==============================================================================================================="
    echo ""

    # Set branch environment variable for the installer
    if [ -n "$BRANCH_NAME" ]; then
        export CYBERPANEL_BRANCH="$BRANCH_NAME"
        echo "Setting installation branch to: $BRANCH_NAME"
    else
        export CYBERPANEL_BRANCH="stable"
        echo "Using default stable branch"
    fi
    echo ""

    # CRITICAL: Use install/install.py directly instead of cyberpanel_installer.sh
    # The cyberpanel_installer.sh is the old wrapper that doesn't support auto-install
    # install/install.py is the actual installer that we can control
    local installer_py="install/install.py"
    if [ -f "$installer_py" ]; then
        print_status "Using install/install.py directly for installation (non-interactive mode)"
        
        # NOTE: We do NOT patch install.py to add --exclude=MariaDB-server* to dnf install.
        # That would block the initial MariaDB-server install. install.py now clears dnf exclude
        # before installing MariaDB and uses official MariaDB-server packages.
        
        # Clear MariaDB-server from dnf/yum exclude so the installer can install or reinstall it
        # (cyberpanel.sh may have added it earlier when 10.x was detected; partial installs leave exclude in place)
        for conf in /etc/dnf/dnf.conf /etc/yum.conf; do
            if [ -f "$conf" ] && grep -q "exclude=.*MariaDB-server" "$conf" 2>/dev/null; then
                sed -i '/^exclude=/s/MariaDB-server\*\s*//g' "$conf"
                sed -i '/^exclude=/s/\s*MariaDB-server\*//g' "$conf"
                sed -i '/^exclude=/s/MariaDB-server\s*//g' "$conf"
                sed -i '/^exclude=\s*$/d' "$conf"
                sed -i '/^exclude=$/d' "$conf"
                print_status "Cleared MariaDB-server from exclude in $conf for installation"
            fi
        done
        
        # If MariaDB 10.x is installed, disable repositories right before running installer
        if [ -n "$MARIADB_VERSION" ] && [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
            # Call the disable function one more time before installer runs
            if type disable_mariadb_repos >/dev/null 2>&1; then
                disable_mariadb_repos
            fi
        fi
        
        # Get server IP address (required by install.py)
        local server_ip
        if command -v curl >/dev/null 2>&1; then
            server_ip=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://icanhazip.com 2>/dev/null || echo "")
        fi
        
        if [ -z "$server_ip" ]; then
            # Fallback: try to get IP from network interfaces
            server_ip=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || \
                       hostname -I 2>/dev/null | awk '{print $1}' || \
                       echo "127.0.0.1")
        fi
        
        if [ -z "$server_ip" ] || [ "$server_ip" = "127.0.0.1" ]; then
            print_status "WARNING: Could not detect public IP, using 127.0.0.1"
            server_ip="127.0.0.1"
        fi
        
        print_status "Detected server IP: $server_ip"

        # Python for mysqlclient bootstrap and install.py (CYBERCP_VENV_PYTHON from ensure_cybercp_system_python)
        if [[ -z "${CYBERCP_VENV_PYTHON:-}" ]] && type ensure_cybercp_system_python >/dev/null 2>&1; then
            ensure_cybercp_system_python
        fi
        local CP_INSTALL_PY="${CYBERCP_VENV_PYTHON:-}"
        if [[ -z "$CP_INSTALL_PY" || ! -x "$CP_INSTALL_PY" ]]; then
            CP_INSTALL_PY="$(command -v python3 2>/dev/null || echo /usr/bin/python3)"
        fi
        export CYBERCP_VENV_PYTHON="$CP_INSTALL_PY"
        print_status "Running installer with Python: $CP_INSTALL_PY (CyberCP venv will match when created by install.py)"
        
        # CRITICAL: Install Python MySQL dependencies before running install.py
        # installCyberPanel.py requires MySQLdb (mysqlclient) which needs development headers
        echo ""
        echo "==============================================================================================================="
        echo "Installing Python MySQL dependencies (required for installCyberPanel.py)..."
        echo "==============================================================================================================="
        print_status "Installing Python MySQL dependencies..."
        
        # Detect OS for package installation
        local os_family=""
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            case "$ID" in
                almalinux|rocky|centos|rhel|fedora)
                    os_family="rhel"
                    print_status "Detected RHEL-based OS: $ID"
                    ;;
                ubuntu|debian)
                    os_family="debian"
                    print_status "Detected Debian-based OS: $ID"
                    ;;
                *)
                    print_status "Unknown OS ID: $ID, defaulting to RHEL-based"
                    os_family="rhel"
                    ;;
            esac
        else
            print_status "WARNING: /etc/os-release not found, defaulting to RHEL-based"
            os_family="rhel"
        fi
        
        # Install MariaDB/MySQL development headers and Python mysqlclient
        if [ "$os_family" = "rhel" ]; then
            # RHEL-based (AlmaLinux, Rocky, CentOS, RHEL)
            print_status "Installing MariaDB development headers for RHEL-based system..."
            
            # Try to install mariadb-devel (works with MariaDB 10.x and 12.x)
            # NOTE: We need mariadb-devel even if we excluded MariaDB-server
            # The exclude only applies to MariaDB-server, not development packages
            if command -v dnf >/dev/null 2>&1; then
                # For AlmaLinux 9/10 and newer - show output for debugging
                print_status "Attempting to install mariadb-devel (development headers only, not server)..."
                # Temporarily remove exclude for devel packages if needed
                local dnf_exclude_backup=""
                if [ -f /etc/dnf/dnf.conf ] && grep -q "exclude=.*MariaDB" /etc/dnf/dnf.conf; then
                    # Check if exclude is too broad
                    if grep -q "exclude=.*MariaDB-server.*MariaDB-devel" /etc/dnf/dnf.conf || \
                       grep -q "exclude=.*MariaDB\*" /etc/dnf/dnf.conf; then
                        print_status "Temporarily adjusting dnf exclude to allow mariadb-devel installation..."
                        # We only want to exclude MariaDB-server, not devel packages
                        sed -i 's/exclude=\(.*\)MariaDB-server\(.*\)MariaDB-devel\(.*\)/exclude=\1MariaDB-server\2\3/' /etc/dnf/dnf.conf 2>/dev/null || true
                        sed -i 's/exclude=\(.*\)MariaDB\*\(.*\)/exclude=\1MariaDB-server*\2/' /etc/dnf/dnf.conf 2>/dev/null || true
                    fi
                fi

                local _pydev="python3-devel"
                local _pypip="python3-pip"
                case "$CP_INSTALL_PY" in
                    *python3.11*) _pydev="python3.11-devel"; _pypip="python3.11-pip" ;;
                esac
                
                if dnf install -y --allowerasing --skip-broken --nobest \
                    mariadb-devel pkgconfig gcc "${_pydev}" "${_pypip}"; then
                    print_status "✓ Successfully installed mariadb-devel"
                elif dnf install -y --allowerasing --skip-broken --nobest \
                    mysql-devel pkgconfig gcc "${_pydev}" "${_pypip}"; then
                    print_status "✓ Successfully installed mysql-devel"
                elif dnf install -y --allowerasing --skip-broken --nobest \
                    mariadb-connector-c-devel pkgconfig gcc "${_pydev}" "${_pypip}"; then
                    print_status "✓ Successfully installed mariadb-connector-c-devel"
                else
                    print_status "⚠️  WARNING: Failed to install MariaDB development headers"
                    print_status "This may cause MySQLdb installation to fail"
                fi
            else
                # For older systems with yum
                print_status "Using yum to install mariadb-devel..."
                local _pydevy="python3-devel"
                local _pypipy="python3-pip"
                case "$CP_INSTALL_PY" in
                    *python3.11*) _pydevy="python3.11-devel"; _pypipy="python3.11-pip" ;;
                esac
                if yum install -y mariadb-devel pkgconfig gcc "${_pydevy}" "${_pypipy}"; then
                    print_status "✓ Successfully installed mariadb-devel"
                elif yum install -y mysql-devel pkgconfig gcc "${_pydevy}" "${_pypipy}"; then
                    print_status "✓ Successfully installed mysql-devel"
                else
                    print_status "⚠️  WARNING: Failed to install MariaDB development headers"
                fi
            fi
            
            # Install mysqlclient Python package
            print_status "Installing mysqlclient Python package..."
            "$CP_INSTALL_PY" -m pip install --upgrade pip setuptools wheel 2>&1 | grep -v "already satisfied" || true
            if "$CP_INSTALL_PY" -m pip install mysqlclient 2>&1; then
                print_status "✓ Successfully installed mysqlclient"
            else
                # If pip install fails, try with build dependencies
                print_status "Retrying mysqlclient installation with build dependencies..."
                "$CP_INSTALL_PY" -m pip install --no-cache-dir mysqlclient 2>&1 || {
                    print_status "⚠️  WARNING: Failed to install mysqlclient, trying alternative method..."
                    # Try installing from source
                    "$CP_INSTALL_PY" -m pip install --no-binary mysqlclient mysqlclient 2>&1 || true
                }
            fi
            
        elif [ "$os_family" = "debian" ]; then
            # Debian-based (Ubuntu, Debian)
            print_status "Installing MariaDB development headers for Debian-based system..."
            apt-get update -y
            local _aptpydev="python3-dev"
            local _aptpyextras=""
            case "$CP_INSTALL_PY" in
                *python3.11*)
                    _aptpydev="python3.11-dev"
                    _aptpyextras="python3.11-venv"
                    ;;
            esac
            if apt-get install -y libmariadb-dev libmariadb-dev-compat pkg-config build-essential ${_aptpyextras} "${_aptpydev}" python3-pip; then
                print_status "✓ Successfully installed MariaDB development headers"
            elif apt-get install -y default-libmysqlclient-dev pkg-config build-essential ${_aptpyextras} "${_aptpydev}" python3-pip; then
                print_status "✓ Successfully installed MySQL development headers"
            else
                print_status "⚠️  WARNING: Failed to install MariaDB/MySQL development headers"
            fi
            
            # Install mysqlclient Python package
            print_status "Installing mysqlclient Python package..."
            "$CP_INSTALL_PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
            "$CP_INSTALL_PY" -m pip install --upgrade pip setuptools wheel 2>&1 | grep -v "already satisfied" || true
            if "$CP_INSTALL_PY" -m pip install mysqlclient 2>&1; then
                print_status "✓ Successfully installed mysqlclient"
            else
                print_status "Retrying mysqlclient installation with build dependencies..."
                "$CP_INSTALL_PY" -m pip install --no-cache-dir mysqlclient 2>&1 || true
            fi
        fi
        
        # Verify MySQLdb is available (mysqlclient; some builds lack __version__)
        print_status "Verifying MySQLdb module availability..."
        if "$CP_INSTALL_PY" -c "import MySQLdb; getattr(MySQLdb, '__version__', 'ok'); print('MySQLdb OK')" 2>/dev/null || \
           "$CP_INSTALL_PY" -c "import MySQLdb; MySQLdb; print('MySQLdb OK')" 2>/dev/null; then
            print_status "✓ MySQLdb module is available and working"
        else
            print_status "⚠️  WARNING: MySQLdb module not available"
            print_status "Attempting to diagnose the issue..."
            "$CP_INSTALL_PY" -c "import sys; print('Python path:', sys.path)" 2>&1 || true
            "$CP_INSTALL_PY" -m pip list | grep -i mysql || print_status "No MySQL-related packages found in pip list"
            print_status "Attempting to continue anyway, but installation may fail..."
        fi
        echo ""
        
        # Build installer arguments based on user preferences
        # install.py requires publicip as first positional argument
        local install_args=("$server_ip")
        
        # Web server: OpenLiteSpeed (default) or LiteSpeed Enterprise (--ent + --serial)
        if [ -n "$LS_ENT" ] && [ -n "$LS_SERIAL" ]; then
            install_args+=("--ent" "$LS_ENT" "--serial" "$LS_SERIAL")
        fi
        # Default: OpenLiteSpeed, Full installation (postfix, powerdns, ftp), Local MySQL
        install_args+=("--postfix" "ON")
        install_args+=("--powerdns" "ON")
        install_args+=("--ftp" "ON")
        install_args+=("--remotemysql" "OFF")
        # Only pass --mariadb-version if this install.py supports it (avoids "unrecognized arguments" on older archives)
        if grep -q "mariadb-version\|mariadb_version" "$installer_py" 2>/dev/null; then
            install_args+=("--mariadb-version" "${MARIADB_VER:-11.8}")
        fi
        
        if [ "$DEBUG_MODE" = true ]; then
            # Note: install.py doesn't have --debug, but we can set it via environment
            export DEBUG_MODE=true
        fi
        
        # CRITICAL: If CyberPanel Python does not exist yet, patch installer to use system Python.
        # Fixes FileNotFoundError when archive is cached/old and still references /usr/local/CyberPanel/bin/python.
        if [ ! -f /usr/local/CyberPanel/bin/python ]; then
            sys_python="$CP_INSTALL_PY"
            [ -x "$sys_python" ] || sys_python="/usr/bin/python3"
            [ -x "$sys_python" ] || sys_python="/usr/local/bin/python3"
            if [ -x "$sys_python" ]; then
                for f in install/install_utils.py install/install.py; do
                    if [ -f "$f" ] && grep -q '/usr/local/CyberPanel/bin/python' "$f" 2>/dev/null; then
                        sed -i "s|/usr/local/CyberPanel/bin/python|$sys_python|g" "$f"
                        print_status "Patched $f to use $sys_python (CyberPanel python not yet installed)"
                    fi
                done
            fi
        fi
        
        # Run the Python installer directly
        if [ "$DEBUG_MODE" = true ]; then
            "$CP_INSTALL_PY" "$installer_py" "${install_args[@]}" 2>&1 | tee /var/log/CyberPanel/install_output.log
        else
            "$CP_INSTALL_PY" "$installer_py" "${install_args[@]}" 2>&1 | tee /var/log/CyberPanel/install_output.log
        fi
    else
        # Fallback to cyberpanel_installer.sh if install.py not found
        print_status "WARNING: install/install.py not found, using cyberpanel_installer.sh (may be interactive)"
        
        local installer_script="cyberpanel_installer.sh"
        if [ ! -f "$installer_script" ]; then
            print_status "ERROR: cyberpanel_installer.sh not found in current directory: $(pwd)"
            return 1
        fi
        
        # Get absolute path to installer script
        local installer_path
        if [[ "$installer_script" = /* ]]; then
            installer_path="$installer_script"
        else
            installer_path="$(pwd)/$installer_script"
        fi
        
        # If MariaDB 10.x is installed, disable repositories right before running installer
        if [ -n "$MARIADB_VERSION" ] && [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
            # Call the disable function one more time before installer runs
            if type disable_mariadb_repos >/dev/null 2>&1; then
                disable_mariadb_repos
            fi
        fi
        
        if [ "$DEBUG_MODE" = true ]; then
            bash "$installer_path" --debug 2>&1 | tee /var/log/CyberPanel/install_output.log
        else
            bash "$installer_path" 2>&1 | tee /var/log/CyberPanel/install_output.log
        fi
    fi
    
    local install_exit_code=${PIPESTATUS[0]}
    
    # Stop the repository monitor
    if [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
        local monitor_pid=$(cat /tmp/cyberpanel_repo_monitor.pid 2>/dev/null)
        if [ -n "$monitor_pid" ] && kill -0 "$monitor_pid" 2>/dev/null; then
            kill "$monitor_pid" 2>/dev/null
        fi
        rm -f /tmp/cyberpanel_repo_monitor.pid
    fi
    touch /tmp/cyberpanel_install_complete 2>/dev/null || true

    # Extract the generated password from the installation output
    local generated_password=""
    generated_password=$(grep -E "Panel password:|Password:" /var/log/CyberPanel/install_output.log 2>/dev/null | tail -1 | awk '{print $NF}')
    if [ -z "$generated_password" ] && [ -f /etc/cyberpanel/adminPass ]; then
        generated_password=$(tr -d '\r\n' < /etc/cyberpanel/adminPass 2>/dev/null)
    fi
    if [ -n "$generated_password" ]; then
        echo "Captured CyberPanel password: $generated_password"
        echo "$generated_password" > /root/.cyberpanel_password
        chmod 600 /root/.cyberpanel_password
        mkdir -p /etc/cyberpanel
        echo "$generated_password" > /etc/cyberpanel/adminPass
        chmod 600 /etc/cyberpanel/adminPass
    fi
    
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION COMPLETED"
    echo "==============================================================================================================="
    echo ""
    echo "  Installation logs (for troubleshooting):"
    echo "    • /var/log/CyberPanel/install.log       (installer script messages)"
    echo "    • /var/log/CyberPanel/install_output.log (Python installer stdout/stderr)"
    echo "    • /var/log/installLogs.txt              (install.py detailed log)"
    echo ""
    
    # Check if installation was successful
    if [ $install_exit_code -ne 0 ]; then
        print_status "ERROR: CyberPanel installation failed with exit code $install_exit_code"
        echo ""
        echo "Installation log (last 50 lines):"
        echo "==============================================================================================================="
        tail -50 /var/log/CyberPanel/install_output.log 2>/dev/null || echo "Could not read installation log"
        echo "==============================================================================================================="
        echo ""
        echo "Full installation log available at: /var/log/CyberPanel/install_output.log"
        echo ""
        return 1
    fi
    
    # Clean up temporary directory
    cd /tmp
    rm -rf "$temp_dir" 2>/dev/null || true
    
    # Check if installation was successful
    if [ $install_exit_code -eq 0 ]; then
        # Installation succeeded, but don't print success message yet
        # The CyberPanel installer has already shown its summary

        # Run static file permission fixes (critical for LiteSpeed) silently
        fix_static_file_permissions >/dev/null 2>&1

        return 0
    else
        print_status "ERROR: CyberPanel installation failed (exit code: $install_exit_code)"
        echo ""
        echo "==============================================================================================================="
        echo "                                    INSTALLATION FAILED"
        echo "==============================================================================================================="
        echo ""
        echo "The CyberPanel installation has failed. Here's how to troubleshoot:"
        echo ""
        echo "📋 LOG FILES LOCATION:"
        echo "  • Main installer log: /var/log/CyberPanel/install.log"
        echo "  • Installation output: /var/log/CyberPanel/install_output.log"
        echo "  • System logs: /var/log/messages"
        echo ""
        echo "🔍 TROUBLESHOOTING STEPS:"
        echo "  1. Check the installation output log for specific errors"
        echo "  2. Verify your system meets the requirements"
        echo "  3. Ensure you have sufficient disk space and memory"
        echo "  4. Check your internet connection"
        echo "  5. Try running the installer again"
        echo ""
        echo "📄 LAST 30 LINES OF INSTALLATION LOG:"
        echo "==============================================================================================================="
        if [ -f "/var/log/CyberPanel/install_output.log" ]; then
            tail -30 /var/log/CyberPanel/install_output.log 2>/dev/null || echo "Could not read installation log"
        else
            echo "Installation log not found at /var/log/CyberPanel/install_output.log"
        fi
        echo "==============================================================================================================="
        echo ""
        echo "💡 QUICK DEBUG COMMANDS:"
        echo "  • View full log: cat /var/log/CyberPanel/install_output.log"
        echo "  • Check system: free -h && df -h"
        echo "  • Check network: ping -c 3 google.com"
        echo "  • Retry installation: Run the installer again"
        echo ""
        echo "🆘 NEED HELP?"
        echo "  • CyberPanel Documentation: https://docs.cyberpanel.net"
        echo "  • CyberPanel Community: https://forums.cyberpanel.net"
        echo "  • GitHub Issues: https://github.com/usmannasir/cyberpanel/issues"
        echo ""
        return 1
    fi
}
