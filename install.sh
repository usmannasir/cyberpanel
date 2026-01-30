#!/usr/bin/env bash

# CyberPanel v2.5.5-dev Installer
# Simplified approach similar to stable branch

# Logging setup
LOG_FILE="/var/log/installer.log"
mkdir -p /var/log 2>/dev/null || true
touch "$LOG_FILE" 2>/dev/null || true
exec >>"$LOG_FILE" 2>&1
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Installer started: $0 $*"

# Re-exec with elevation if not running as root
if [ "$(id -u)" -ne 0 ]; then
    SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || echo "$0")"
    for elevate in sudo doas run0 pkexec; do
        if command -v "$elevate" >/dev/null 2>&1; then
            echo "[$(date +"%Y-%m-%d %H:%M:%S")] Elevating with $elevate"
            "$elevate" env "XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-}" "SUDO_USER=$(whoami)" "$SCRIPT_PATH" "$@"
            exit $?
        fi
    done

    echo "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: No elevation tool found."
    echo "Please install sudo, doas, run0 (systemd), or pkexec (polkit) to continue."
    exit 1
fi

# Determine branch from arguments or use default
BRANCH_NAME="v2.5.5-dev"
while [ "$#" -gt 0 ]; do
    case "$1" in
        -b|--branch)
            if [ -n "${2:-}" ]; then
                BRANCH_NAME="$2"
                shift 2
            else
                echo "❌ Missing value for $1"
                exit 1
            fi
            ;;
        *)
            shift
            ;;
    esac
done

# Check disk space (10GB minimum)
check_disk_space() {
    if command -v df >/dev/null 2>&1; then
        available_gb=$(df -BG / 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//' | cut -d. -f1)
        if [ -z "$available_gb" ] || ! [[ "$available_gb" =~ ^[0-9]+$ ]]; then
            available_gb=$(df / 2>/dev/null | awk 'NR==2 {print $4}' | awk '{printf "%.0f", $1/1024/1024}')
        fi
        if [[ "$available_gb" =~ ^[0-9]+$ ]]; then
            echo "[$(date +"%Y-%m-%d %H:%M:%S")] Disk space: ${available_gb}GB available (10GB minimum required)"
            if [ "$available_gb" -lt 10 ]; then
                echo "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Less than 10GB available. Installation may fail."
            fi
        fi
    fi
}

# Detect OS and set SERVER_OS (similar to stable branch)
OUTPUT=$(cat /etc/*release 2>/dev/null || echo "")
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Detected release info:"
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "CentOS Linux 7" ; then
    echo "Checking and installing curl and wget"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
    SERVER_OS="CentOS"
elif echo "$OUTPUT" | grep -q "CentOS Linux 8" ; then
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
    SERVER_OS="CentOS8"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
elif echo "$OUTPUT" | grep -q "CloudLinux 7" ; then
    echo "Checking and installing curl and wget"
    yum install curl wget -y 1> /dev/null 2>&1 || dnf install curl wget -y 1> /dev/null 2>&1 || true
    yum update curl wget ca-certificates -y 1> /dev/null 2>&1 || dnf update curl wget ca-certificates -y 1> /dev/null 2>&1 || true
    SERVER_OS="CloudLinux"
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
    echo -e "\nCyberPanel is supported on Ubuntu 18.04, Ubuntu 20.04, Ubuntu 22.04, Ubuntu 24.04, AlmaLinux 8, AlmaLinux 9, AlmaLinux 10 and CloudLinux 7.x...\n"
    exit 1
fi

# Check disk space
echo "[$(date +"%Y-%m-%d %H:%M:%S")] SERVER_OS=$SERVER_OS BRANCH_NAME=$BRANCH_NAME"

# Check disk space
check_disk_space

# Download and execute cyberpanel.sh for the specified branch
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Downloading CyberPanel installer for branch: $BRANCH_NAME"

# Use absolute path for downloaded script in a writable directory
TEMP_DIR="/tmp"
SCRIPT_PATH="$TEMP_DIR/cyberpanel-$$.sh"
rm -f "$SCRIPT_PATH" "$TEMP_DIR/cyberpanel.sh" "$TEMP_DIR/install.tar.gz"

# Ensure temp directory exists and is writable
mkdir -p "$TEMP_DIR" 2>/dev/null || true

# For v2.5.5-dev, try to get the cyberpanel.sh from the branch
if [ "$BRANCH_NAME" = "v2.5.5-dev" ] || [ "$BRANCH_NAME" = "stable" ]; then
    # Try to download from the branch-specific URL
    if curl --silent -o "$SCRIPT_PATH" "https://raw.githubusercontent.com/master3395/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null; then
        if [ -f "$SCRIPT_PATH" ] && [ -s "$SCRIPT_PATH" ]; then
            # Make script executable
            chmod 755 "$SCRIPT_PATH" 2>/dev/null || true
            # Verify it's executable
            if [ -x "$SCRIPT_PATH" ]; then
                echo "[$(date +"%Y-%m-%d %H:%M:%S")] Downloaded cyberpanel.sh from branch $BRANCH_NAME"
                # Change to temp directory and execute with bash
                # Use absolute path to avoid any relative path issues
                cd "$TEMP_DIR" || cd /tmp || cd /
                echo "[$(date +"%Y-%m-%d %H:%M:%S")] Executing $SCRIPT_PATH"
                bash "$SCRIPT_PATH" "$@"
                exit $?
            else
                echo "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Could not make script executable, trying alternative method..."
                cd "$TEMP_DIR" || cd /tmp || cd /
                bash -c "bash '$SCRIPT_PATH' $*"
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
            echo "[$(date +"%Y-%m-%d %H:%M:%S")] Downloaded cyberpanel.sh from standard source"
            # Change to temp directory and execute with bash
            # Use absolute path to avoid any relative path issues
            cd "$TEMP_DIR" || cd /tmp || cd /
            echo "[$(date +"%Y-%m-%d %H:%M:%S")] Executing $SCRIPT_PATH"
            bash "$SCRIPT_PATH" "$@"
            exit $?
        else
            echo "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Could not make script executable, trying alternative method..."
            cd "$TEMP_DIR" || cd /tmp || cd /
            bash -c "bash '$SCRIPT_PATH' $*"
            exit $?
        fi
    fi
fi

# If we get here, download failed
echo "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Failed to download cyberpanel.sh"
echo "Please check your internet connection and try again"
exit 1
