#!/usr/bin/env bash
# CyberPanel install – install_cyberpanel, install_cyberpanel_direct (part 1). Sourced by cyberpanel.sh.

install_cyberpanel() {
    print_status "Installing CyberPanel..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    CYBERPANEL INSTALLATION IN PROGRESS"
    echo "==============================================================================================================="
    echo ""
    echo "This process may take 10-15 minutes depending on your internet speed."
    echo "Please DO NOT close this terminal or interrupt the installation."
    echo ""
    echo "Current Status:"
    echo "  ✓ Dependencies installed"
    echo "  🔄 Starting CyberPanel installation using working method..."
    echo ""
    
    # Use the working CyberPanel installation method
    install_cyberpanel_direct
}

# Function to check if CyberPanel is already installed
check_cyberpanel_installed() {
    if [ -d "/usr/local/CyberPanel" ] || [ -d "/usr/local/CyberCP" ] || [ -f "/usr/local/lsws/bin/lswsctrl" ]; then
        return 0  # CyberPanel is installed
    else
        return 1  # CyberPanel is not installed
    fi
}

# Function to clean up existing CyberPanel installation
cleanup_existing_cyberpanel() {
    echo "  🧹 Cleaning up existing CyberPanel installation..."
    
    # Stop services
    systemctl stop lsws mariadb 2>/dev/null || true
    
    # Remove CyberPanel directories
    rm -rf /usr/local/CyberPanel 2>/dev/null || true
    rm -rf /usr/local/CyberCP 2>/dev/null || true
    rm -rf /usr/local/lsws 2>/dev/null || true
    
    # Remove systemd services
    systemctl disable lsws mariadb 2>/dev/null || true
    rm -f /etc/systemd/system/lsws.service 2>/dev/null || true
    
    # Clean up databases
    $MDB_CLI -e "DROP DATABASE IF EXISTS cyberpanel;" 2>/dev/null || true
    $MDB_CLI -e "DROP USER IF EXISTS 'cyberpanel'@'localhost';" 2>/dev/null || true
    
    echo "  ✅ Cleanup completed"
}

# Function to install CyberPanel directly using the working method
install_cyberpanel_direct() {
    # Ask web server (OpenLiteSpeed vs LiteSpeed Enterprise) BEFORE MariaDB; default OpenLiteSpeed
    if [ -z "$LS_ENT" ]; then
        if [ "$AUTO_INSTALL" = true ]; then
            LS_ENT=""
            echo "  Using OpenLiteSpeed (auto mode)."
        else
            echo ""
            echo "  Web server: 1) OpenLiteSpeed (default), 2) LiteSpeed Enterprise"
            read -r -t 60 -p "  Enter 1 or 2 [1]: " LS_CHOICE || true
            LS_CHOICE="${LS_CHOICE:-1}"
            LS_CHOICE="${LS_CHOICE// /}"
            if [ "$LS_CHOICE" = "2" ]; then
                echo "  LiteSpeed Enterprise selected. Enter serial/key (required):"
                read -r -t 120 -p "  Serial: " LS_SERIAL || true
                LS_SERIAL="${LS_SERIAL:-}"
                if [ -z "$LS_SERIAL" ]; then
                    echo "  No serial provided. Defaulting to OpenLiteSpeed."
                    LS_ENT=""
                else
                    LS_ENT="ent"
                    echo "  Using LiteSpeed Enterprise with provided serial."
                fi
            else
                LS_ENT=""
                echo "  Using OpenLiteSpeed."
            fi
            echo ""
        fi
    fi

    # Ask MariaDB version (after web server choice) if not set via --mariadb-version
    if [ -z "$MARIADB_VER" ]; then
        echo ""
        echo "  MariaDB version: 10.11, 11.8 (LTS, default), 12.1, 12.2, 12.3 or other X.Y?"
        read -r -t 60 -p "  Enter version [11.8]: " MARIADB_VER || true
        MARIADB_VER="${MARIADB_VER:-11.8}"
        MARIADB_VER="${MARIADB_VER// /}"
        # Normalize to major.minor (e.g. 12.3.1 -> 12.3)
        if [[ "$MARIADB_VER" =~ ^([0-9]+)\.([0-9]+) ]]; then
            MARIADB_VER="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
        else
            MARIADB_VER="11.8"
        fi
        echo "  Using MariaDB $MARIADB_VER"
        echo ""
    fi

    echo "  🔄 Downloading CyberPanel installation files..."
    
    # Check if CyberPanel is already installed
    if check_cyberpanel_installed; then
        echo "  ⚠️  CyberPanel is already installed but may not be working properly"
        echo "  🔧 Cleaning up existing installation and reinstalling..."
        cleanup_existing_cyberpanel
    fi
    
    # Pre-installation system checks
    echo "  🔍 Running pre-installation checks..."
    
    # Ensure system is up to date
    if command -v dnf >/dev/null 2>&1; then
        echo "    Updating system packages..."
        dnf update -y >/dev/null 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
        echo "    Updating system packages..."
        yum update -y >/dev/null 2>&1 || true
    elif command -v apt >/dev/null 2>&1; then
        echo "    Updating system packages..."
        apt update -y >/dev/null 2>&1 || true
        apt upgrade -y >/dev/null 2>&1 || true
    fi
    
    # Ensure required services are available
    echo "    Checking system services..."
    systemctl enable mariadb 2>/dev/null || true
    systemctl enable lsws 2>/dev/null || true
    
    # Clear any previous install temp folders so we never use stale extracted files
    rm -rf /tmp/cyberpanel_install_* 2>/dev/null || true
    
    # Create temporary directory for installation
    local temp_dir="/tmp/cyberpanel_install_$$"
    mkdir -p "$temp_dir"
    cd "$temp_dir" || return 1
    
    # Only add dnf exclude when we want to KEEP the current MariaDB (same version as user chose).
    # If user chose 11.8 but 10.11 is installed, do NOT exclude — allow install.py to upgrade.
    if command -v rpm >/dev/null 2>&1; then
        if rpm -qa | grep -qiE "^(mariadb-server|mysql-server|MariaDB-server)" 2>/dev/null; then
            local mariadb_version=$(mysql --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            if [ -n "$mariadb_version" ]; then
                local major_ver=$(echo "$mariadb_version" | cut -d. -f1)
                local minor_ver=$(echo "$mariadb_version" | cut -d. -f2)
                local installed_majmin="${major_ver}.${minor_ver}"
                local chosen_ver="${MARIADB_VER:-11.8}"
                # Only add exclude when installed version matches user's choice (preserve, no upgrade)
                if [ "$installed_majmin" = "$chosen_ver" ]; then
                    print_status "MariaDB $mariadb_version matches chosen $chosen_ver, adding dnf exclude to preserve it"
                    
                    # Add MariaDB-server to dnf excludes (multiple formats for compatibility)
                    local dnf_conf="/etc/dnf/dnf.conf"
                    local exclude_added=false
                    
                    if [ -f "$dnf_conf" ]; then
                        # Check if [main] section exists
                        if grep -q "^\[main\]" "$dnf_conf" 2>/dev/null; then
                            # [main] section exists, add exclude there
                            if ! grep -q "exclude=.*MariaDB-server" "$dnf_conf" 2>/dev/null; then
                                if grep -q "^exclude=" "$dnf_conf" 2>/dev/null; then
                                    # Append to existing exclude line in [main] section
                                    sed -i '/^\[main\]/,/^\[/ { /^exclude=/ s/$/ MariaDB-server*/ }' "$dnf_conf"
                                else
                                    # Add new exclude line after [main]
                                    sed -i '/^\[main\]/a exclude=MariaDB-server*' "$dnf_conf"
                                fi
                                exclude_added=true
                            fi
                        else
                            # No [main] section, add it with exclude
                            if ! grep -q "exclude=.*MariaDB-server" "$dnf_conf" 2>/dev/null; then
                                echo "" >> "$dnf_conf"
                                echo "[main]" >> "$dnf_conf"
                                echo "exclude=MariaDB-server*" >> "$dnf_conf"
                                exclude_added=true
                            fi
                        fi
                    else
                        # Create dnf.conf with exclude
                        echo "[main]" > "$dnf_conf"
                        echo "exclude=MariaDB-server*" >> "$dnf_conf"
                        exclude_added=true
                    fi
                    
                    if [ "$exclude_added" = true ]; then
                        print_status "Added MariaDB-server* to dnf excludes in $dnf_conf"
                    fi
                    
                    # Also add to yum.conf for compatibility
                    local yum_conf="/etc/yum.conf"
                    if [ -f "$yum_conf" ]; then
                        if ! grep -q "exclude=.*MariaDB-server" "$yum_conf" 2>/dev/null; then
                            if grep -q "^exclude=" "$yum_conf" 2>/dev/null; then
                                sed -i 's/^exclude=\(.*\)/exclude=\1 MariaDB-server*/' "$yum_conf"
                            else
                                echo "exclude=MariaDB-server*" >> "$yum_conf"
                            fi
                            print_status "Added MariaDB-server* to yum excludes"
                        fi
                    fi
                    
                    # Create a function to disable MariaDB repositories (will be called after repository setup)
                    disable_mariadb_repos() {
                        local repo_files=(
                            "/etc/yum.repos.d/mariadb-main.repo"
                            "/etc/yum.repos.d/mariadb.repo"
                            "/etc/yum.repos.d/mariadb-12.1.repo"
                        )
                        
                        # Also check for any mariadb repo files
                        while IFS= read -r repo_file; do
                            repo_files+=("$repo_file")
                        done < <(find /etc/yum.repos.d -name "*mariadb*.repo" 2>/dev/null)
                        
                        for repo_file in "${repo_files[@]}"; do
                            if [ -f "$repo_file" ] && [ -n "$repo_file" ]; then
                                # First, try to disable by setting enabled=0
                                sed -i 's/^enabled\s*=\s*1/enabled=0/g' "$repo_file" 2>/dev/null
                                
                                # If file contains MariaDB 12.1 references, disable or remove it
                                if grep -qi "mariadb.*12\|12.*mariadb\|mariadb-main" "$repo_file" 2>/dev/null; then
                                    # Try to add enabled=0 to each [mariadb...] section
                                    python3 -c "
import re
import sys
try:
    with open('$repo_file', 'r') as f:
        content = f.read()
    
    # Replace enabled=1 with enabled=0
    content = re.sub(r'(enabled\s*=\s*)1', r'\g<1>0', content, flags=re.IGNORECASE)
    
    # Add enabled=0 after [mariadb...] sections if not present
    lines = content.split('\n')
    new_lines = []
    in_mariadb_section = False
    has_enabled = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if re.match(r'^\s*\[.*mariadb.*\]', line, re.IGNORECASE):
            in_mariadb_section = True
            has_enabled = False
        elif in_mariadb_section:
            if re.match(r'^\s*enabled\s*=', line, re.IGNORECASE):
                has_enabled = True
            elif re.match(r'^\s*\[', line) and not re.match(r'^\s*\[.*mariadb.*\]', line, re.IGNORECASE):
                if not has_enabled:
                    new_lines.insert(-1, 'enabled=0')
                in_mariadb_section = False
                has_enabled = False
    
    if in_mariadb_section and not has_enabled:
        new_lines.append('enabled=0')
    
    with open('$repo_file', 'w') as f:
        f.write('\n'.join(new_lines))
except:
    # Fallback: just rename the file
    import os
    os.rename('$repo_file', '${repo_file}.disabled')
" 2>/dev/null || \
                                    # Fallback: rename the file to disable it
                                    mv "$repo_file" "${repo_file}.disabled" 2>/dev/null || true
                                fi
                            fi
                        done
                    }
                    
                    # Export function so it can be called from installer
                    export -f disable_mariadb_repos
                    export MARIADB_VERSION="$mariadb_version"
                    
                    # Also set up a background process to monitor and disable repos
                    (
                        while [ ! -f /tmp/cyberpanel_install_complete ]; do
                            sleep 2
                            if [ -f /etc/yum.repos.d/mariadb-main.repo ] || [ -f /etc/yum.repos.d/mariadb.repo ]; then
                                disable_mariadb_repos
                            fi
                        done
                    ) &
                    local monitor_pid=$!
                    echo "$monitor_pid" > /tmp/cyberpanel_repo_monitor.pid
                    print_status "Started background process to monitor and disable MariaDB repositories"
                else
                    # User chose a different version (e.g. 11.8) than installed (e.g. 10.11) — allow upgrade
                    print_status "MariaDB $mariadb_version installed but you chose $chosen_ver; not adding dnf exclude (installer will upgrade)"
                    # Remove any existing MariaDB exclude from a previous run so install can proceed
                    for c in /etc/dnf/dnf.conf /etc/yum.conf; do
                        if [ -f "$c" ] && grep -q "exclude=.*MariaDB-server" "$c" 2>/dev/null; then
                            sed -i 's/ *MariaDB-server\* *//g; s/exclude= *$/exclude=/; s/exclude=\s*$/exclude=/' "$c" 2>/dev/null
                            if grep -q "^exclude=\s*$" "$c" 2>/dev/null; then
                                sed -i '/^exclude=\s*$/d' "$c" 2>/dev/null
                            fi
                            print_status "Removed MariaDB-server from excludes in $c to allow upgrade"
                        fi
                    done
                fi
            fi
        fi
    fi
    
    # Download CyberPanel install tree (fork first, then upstream)
    local _cp_owner="${CYBERPANEL_GITHUB_OWNER:-master3395}"
    local _cp_branch="${BRANCH_NAME:-v2.5.5-dev}"
    echo "Downloading from: https://raw.githubusercontent.com/${_cp_owner}/cyberpanel/${_cp_branch}/cyberpanel.sh"
    
    # GitHub: branch archives use refs/heads/BRANCH; GitHub returns 302 redirect to codeload, so we must use -L
    local archive_url=""
    local installer_url="https://raw.githubusercontent.com/${_cp_owner}/cyberpanel/${_cp_branch}/cyberpanel.sh"
    local _archive_candidates=(
        "https://github.com/${_cp_owner}/cyberpanel/archive/refs/heads/${_cp_branch}.tar.gz"
        "https://github.com/${_cp_owner}/cyberpanel/archive/${_cp_branch}.tar.gz"
    )
    _github_archive_ok() {
        local url="$1"
        local code
        code=$(curl -sL -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        [[ "$code" == "200" || "$code" == "302" ]]
    }

    local _cand _found=0
    for _cand in "${_archive_candidates[@]}"; do
        if _github_archive_ok "$_cand"; then
            archive_url="$_cand"
            echo "    Using branch ${_cp_branch} from ${_cp_owner}/cyberpanel"
            _found=1
            break
        fi
    done
    if [[ "$_found" -eq 0 ]] && [[ "$_cp_owner" != "usmannasir" ]]; then
        echo "    Fork archive not found, trying usmannasir/cyberpanel..."
        _cp_owner="usmannasir"
        installer_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/${_cp_branch}/cyberpanel.sh"
        for _cand in \
            "https://github.com/usmannasir/cyberpanel/archive/refs/heads/${_cp_branch}.tar.gz" \
            "https://github.com/usmannasir/cyberpanel/archive/${_cp_branch}.tar.gz"; do
            if _github_archive_ok "$_cand"; then
                archive_url="$_cand"
                echo "    Using branch ${_cp_branch} from usmannasir/cyberpanel"
                _found=1
                break
            fi
        done
    fi
    if [[ "$_found" -eq 0 ]]; then
        echo "    Development branch archive not available, trying installer script directly..."
        if ! _github_archive_ok "$installer_url"; then
            echo "    Development branch not available, falling back to stable"
            installer_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh"
            archive_url="https://github.com/usmannasir/cyberpanel/archive/stable.tar.gz"
        else
            archive_url="https://github.com/${_cp_owner}/cyberpanel/archive/refs/heads/${_cp_branch}.tar.gz"
        fi
    fi
    
    curl --silent -o cyberpanel_installer.sh "$installer_url" 2>/dev/null
    if [ $? -ne 0 ] || [ ! -s "cyberpanel_installer.sh" ]; then
        print_status "ERROR: Failed to download CyberPanel installer"
        return 1
    fi
    
    # Do NOT patch installer to add --exclude=MariaDB-server*: it blocks initial MariaDB install
    # and causes "MariaDB-server requires MariaDB-client but none of the providers can be installed".
    
    # Make script executable (use full path in case cwd has noexec)
    chmod 755 cyberpanel_installer.sh 2>/dev/null || chmod +x cyberpanel_installer.sh 2>/dev/null || true
    if [ ! -x "cyberpanel_installer.sh" ]; then
        print_status "Note: Script will be run with bash (executable bit not set)"
    fi
    
    # Download the install directory (use archive_url set above; may be branch or stable)
    echo "Downloading installation files..."
    if [ -z "$archive_url" ] || [ "$installer_url" = "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh" ]; then
        archive_url="https://github.com/usmannasir/cyberpanel/archive/stable.tar.gz"
    fi
    # Append cache-bust so CDNs/proxies don't serve old installer (GitHub ignores query params)
    archive_url="${archive_url}?nocache=$(date +%s 2>/dev/null || echo 0)"
    
    curl --silent -L -o install_files.tar.gz "$archive_url" 2>/dev/null
    if [ $? -ne 0 ] || [ ! -s "install_files.tar.gz" ]; then
        print_status "ERROR: Failed to download installation files"
        return 1
    fi
    
    # Extract the installation files
    tar -xzf install_files.tar.gz 2>/dev/null
    if [ $? -ne 0 ]; then
        print_status "ERROR: Failed to extract installation files"
        return 1
    fi
    
    # Copy install directory to current location
    if [ "$installer_url" = "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh" ]; then
        if [ -d "cyberpanel-stable" ]; then
            cp -r cyberpanel-stable/install . 2>/dev/null || true
            cp -r cyberpanel-stable/install.sh . 2>/dev/null || true
        fi
    else
        if [ -d "cyberpanel-v2.5.5-dev" ]; then
            cp -r cyberpanel-v2.5.5-dev/install . 2>/dev/null || true
            cp -r cyberpanel-v2.5.5-dev/install.sh . 2>/dev/null || true
        fi
    fi
    
    # Verify install directory was copied
    if [ ! -d "install" ]; then
        print_status "ERROR: install directory not found after extraction"
        print_status "Archive contents:"
        ls -la 2>/dev/null | head -20
        return 1
    fi
    
    print_status "Verified install directory exists"
    install_cyberpanel_direct_cont
}

