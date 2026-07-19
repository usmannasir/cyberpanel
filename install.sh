#!/bin/sh

# CyberPanel v2.5.5-dev Installer
# Simplified approach similar to stable branch

# Full install requires root (packages, /usr/local, services)
if [ "$(id -u)" -ne 0 ]; then
    _branch="${CYBERPANEL_BRANCH:-v2.5.5-dev}"
    if command -v sudo >/dev/null 2>&1; then
        echo "CyberPanel install requires root. Re-running with sudo..."
        _install_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/${_branch}/install.sh"
        exec sudo -E env CYBERPANEL_BRANCH="${_branch}" sh -c "curl -sL '${_install_url}' | sh -s"
    fi
    echo "ERROR: Run the installer as root."
    echo "  curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.5.5-dev/install.sh | sudo sh"
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "WSL: the same command from your AlmaLinux shell (sudo will prompt for your Linux password)."
    fi
    exit 1
fi

# Determine branch from arguments or use default (preserve "$@" for cyberpanel.sh)
BRANCH_NAME="${CYBERPANEL_BRANCH:-v2.5.5-dev}"
_arg_i=1
while [ "$_arg_i" -le "$#" ]; do
    eval "_arg=\${$_arg_i}"
    case "$_arg" in
        -b|--branch)
            _next=$((_arg_i + 1))
            eval "_branch_val=\${$_next}"
            if [ -n "${_branch_val:-}" ]; then
                BRANCH_NAME="$_branch_val"
            else
                echo "ERROR: -b/--branch requires a branch name"
                exit 1
            fi
            ;;
    esac
    _arg_i=$((_arg_i + 1))
done

# When install is piped (curl | sh), default to non-interactive unless --auto already set
if [ ! -t 0 ]; then
    _has_auto=0
    for _a in "$@"; do
        case "$_a" in --auto) _has_auto=1 ;; esac
    done
    if [ "$_has_auto" -eq 0 ]; then
        echo "Piped install detected: enabling --auto --mariadb-version 11.8 (override with explicit flags)"
        set -- "$@" --auto --mariadb-version 11.8
    fi
fi

# Check disk space (10GB minimum)
check_disk_space() {
    if command -v df >/dev/null 2>&1; then
        available_gb=$(df -BG / 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//' | cut -d. -f1)
        if [ -z "$available_gb" ] || ! [[ "$available_gb" =~ ^[0-9]+$ ]]; then
            available_gb=$(df / 2>/dev/null | awk 'NR==2 {print $4}' | awk '{printf "%.0f", $1/1024/1024}')
        fi
        if [[ "$available_gb" =~ ^[0-9]+$ ]]; then
            echo "💾 Disk space: ${available_gb}GB available (10GB minimum required)"
            if [ "$available_gb" -lt 10 ]; then
                echo "⚠️  Warning: Less than 10GB available. Installation may fail."
            fi
        fi
    fi
}

# Reject EOL EL7 before any install work
if [ -f /etc/os-release ] && grep -qE 'CentOS Linux 7|CloudLinux 7|VERSION_ID="7\.|VERSION_ID=7' /etc/os-release 2>/dev/null; then
    echo "CentOS 7 and CloudLinux 7 are no longer supported (EOL)."
    echo "Migrate to AlmaLinux 8, 9, or 10, then run the installer."
    exit 1
fi

# Detect OS and set SERVER_OS (similar to stable branch)
OUTPUT=$(cat /etc/*release 2>/dev/null || echo "")

if echo "$OUTPUT" | grep -q "CentOS Linux 8" ; then
    echo -e "\nDetecting CentOS 8...\n"
    SERVER_OS="CentOS8"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "AlmaLinux 8" ; then
    echo -e "\nDetecting AlmaLinux 8...\n"
    SERVER_OS="CentOS8"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "AlmaLinux 9" ; then
    echo -e "\nDetecting AlmaLinux 9...\n"
    SERVER_OS="CentOS8"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "AlmaLinux 10" ; then
    echo -e "\nDetecting AlmaLinux 10...\n"
    SERVER_OS="AlmaLinux10"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "CloudLinux 8" ; then
    echo "Checking and installing curl and wget"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
    SERVER_OS="CloudLinux"
elif echo "$OUTPUT" | grep -q "Ubuntu 18.04" ; then
    apt install -y -qq wget curl 2>/dev/null || true
    SERVER_OS="Ubuntu"
elif echo "$OUTPUT" | grep -q "Ubuntu 20.04" ; then
    apt install -y -qq wget curl 2>/dev/null || true
    SERVER_OS="Ubuntu"
elif echo "$OUTPUT" | grep -q "Ubuntu 22.04" ; then
    apt install -y -qq wget curl 2>/dev/null || true
    SERVER_OS="Ubuntu"
elif echo "$OUTPUT" | grep -q "Ubuntu 24.04" ; then
    apt install -y -qq wget curl 2>/dev/null || true
    SERVER_OS="Ubuntu"
elif echo "$OUTPUT" | grep -q "Ubuntu 26.04" ; then
    apt install -y -qq wget curl 2>/dev/null || true
    SERVER_OS="Ubuntu"
elif echo "$OUTPUT" | grep -q "openEuler 20.03" ; then
    echo -e "\nDetecting openEuler 20.03...\n"
    SERVER_OS="openEuler"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "openEuler 22.03" ; then
    echo -e "\nDetecting openEuler 22.03...\n"
    SERVER_OS="openEuler"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
else
    echo -e "\nUnable to detect your OS...\n"
    echo -e "\nCyberPanel is supported on Ubuntu 18.04, Ubuntu 20.04, Ubuntu 22.04, Ubuntu 24.04, Ubuntu 26.04, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10, CloudLinux 8/9, CentOS 8/9, Rocky Linux 8/9, RHEL 8/9...\n"
    exit 1
fi

# Check disk space
check_disk_space

# If running from repo with modular installer, use it
INSTALL_SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -n "$INSTALL_SCRIPT_DIR" ] && [ -f "$INSTALL_SCRIPT_DIR/cyberpanel.sh" ] && [ -d "$INSTALL_SCRIPT_DIR/install_modules" ]; then
    echo "Using local CyberPanel installer (modular)"
    cd "$INSTALL_SCRIPT_DIR" || exit 1
    exec bash ./cyberpanel.sh -b "${BRANCH_NAME}" "$@"
fi

# Download and execute cyberpanel.sh for the specified branch
echo "Downloading CyberPanel installer for branch: $BRANCH_NAME"

# Use absolute path for downloaded script in a writable directory
TEMP_DIR="/tmp"
SCRIPT_PATH="$TEMP_DIR/cyberpanel-$$.sh"
rm -f "$SCRIPT_PATH" "$TEMP_DIR/cyberpanel.sh" "$TEMP_DIR/install.tar.gz"

# Ensure temp directory exists and is writable
mkdir -p "$TEMP_DIR" 2>/dev/null || true

# Prefer master3395/cyberpanel raw cyberpanel.sh for known branches (includes AlmaLinux 10 etc.)
if [ "$BRANCH_NAME" = "v2.5.5-dev" ] || [ "$BRANCH_NAME" = "stable" ] || [ "$BRANCH_NAME" = "v2.4.5" ]; then
    # Try to download from the branch-specific URL
    if curl --silent -o "$SCRIPT_PATH" "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null; then
        if [ -f "$SCRIPT_PATH" ] && [ -s "$SCRIPT_PATH" ]; then
            # Make script executable
            chmod 755 "$SCRIPT_PATH" 2>/dev/null || true
            # Verify it's executable
            if [ -x "$SCRIPT_PATH" ]; then
                echo "✅ Downloaded cyberpanel.sh from branch $BRANCH_NAME"
                # Change to temp directory and execute with bash
                # Use absolute path to avoid any relative path issues
                cd "$TEMP_DIR" || cd /tmp || cd /
                export CYBERPANEL_BRANCH="${BRANCH_NAME}"
                export CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER:-usmannasir}"
                bash "$SCRIPT_PATH" -b "${BRANCH_NAME}" "$@"
                exit $?
            else
                echo "⚠️  Warning: Could not make script executable, trying alternative method..."
                cd "$TEMP_DIR" || cd /tmp || cd /
                export CYBERPANEL_BRANCH="${BRANCH_NAME}"
                bash -c "bash '$SCRIPT_PATH' -b '${BRANCH_NAME}' $(printf '%q ' "$@")"
                exit $?
            fi
        fi
    fi
fi

# Fallback to standard cyberpanel.sh download
if curl --silent -o "$SCRIPT_PATH" "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null || \
   wget -q -O "$SCRIPT_PATH" "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null; then
    if [ -f "$SCRIPT_PATH" ] && [ -s "$SCRIPT_PATH" ]; then
        # Make script executable
        chmod 755 "$SCRIPT_PATH" 2>/dev/null || true
        # Verify it's executable
        if [ -x "$SCRIPT_PATH" ]; then
            echo "✅ Downloaded cyberpanel.sh from standard source"
            # Change to temp directory and execute with bash
            # Use absolute path to avoid any relative path issues
            cd "$TEMP_DIR" || cd /tmp || cd /
            export CYBERPANEL_BRANCH="${BRANCH_NAME}"
            bash "$SCRIPT_PATH" -b "${BRANCH_NAME}" "$@"
            exit $?
        else
            echo "⚠️  Warning: Could not make script executable, trying alternative method..."
            cd "$TEMP_DIR" || cd /tmp || cd /
            export CYBERPANEL_BRANCH="${BRANCH_NAME}"
            bash -c "bash '$SCRIPT_PATH' -b '${BRANCH_NAME}' $(printf '%q ' "$@")"
            exit $?
        fi
    fi
fi

# If we get here, download failed
echo "❌ Failed to download cyberpanel.sh"
echo "Please check your internet connection and try again"
exit 1
