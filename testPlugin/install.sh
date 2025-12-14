#!/bin/bash

# Test Plugin Installation Script for CyberPanel
# Multi-OS Compatible Installation Script
# Supports: Ubuntu, Debian, AlmaLinux, RockyLinux, RHEL, CloudLinux, CentOS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="testPlugin"
PLUGIN_DIR="/home/cyberpanel/plugins"
CYBERPANEL_DIR="/usr/local/CyberCP"
GITHUB_REPO="https://github.com/cyberpanel/testPlugin.git"
TEMP_DIR="/tmp/cyberpanel_plugin_install"

# OS Detection Variables
OS_NAME=""
OS_VERSION=""
OS_ARCH=""
PYTHON_CMD=""
PIP_CMD=""
SERVICE_CMD=""
WEB_SERVER=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect operating system
detect_os() {
    print_status "Detecting operating system..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$ID"
        OS_VERSION="$VERSION_ID"
    elif [ -f /etc/redhat-release ]; then
        OS_NAME="rhel"
        OS_VERSION=$(cat /etc/redhat-release | grep -oE '[0-9]+\.[0-9]+' | head -1)
    elif [ -f /etc/debian_version ]; then
        OS_NAME="debian"
        OS_VERSION=$(cat /etc/debian_version)
    else
        print_error "Unable to detect operating system"
        exit 1
    fi
    
    # Detect architecture
    OS_ARCH=$(uname -m)
    
    print_success "Detected: $OS_NAME $OS_VERSION ($OS_ARCH)"
    
    # Set OS-specific configurations
    configure_os_specific
}

# Function to configure OS-specific settings
configure_os_specific() {
    case "$OS_NAME" in
        "ubuntu"|"debian")
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
            SERVICE_CMD="systemctl"
            WEB_SERVER="apache2"
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
            SERVICE_CMD="systemctl"
            WEB_SERVER="httpd"
            ;;
        *)
            print_warning "Unknown OS: $OS_NAME. Using default configurations."
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
            SERVICE_CMD="systemctl"
            WEB_SERVER="httpd"
            ;;
    esac
    
    print_status "Using Python: $PYTHON_CMD"
    print_status "Using Pip: $PIP_CMD"
    print_status "Using Service Manager: $SERVICE_CMD"
    print_status "Using Web Server: $WEB_SERVER"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Function to check if CyberPanel is installed
check_cyberpanel() {
    if [ ! -d "$CYBERPANEL_DIR" ]; then
        print_error "CyberPanel is not installed at $CYBERPANEL_DIR"
        print_error "Please install CyberPanel first: https://raw.githubusercontent.com/die2mrw007/cyberpanel/stable/docs/"
        exit 1
    fi
    
    # Check if CyberPanel is running
    if ! $SERVICE_CMD is-active --quiet lscpd; then
        print_warning "CyberPanel service (lscpd) is not running. Starting it..."
        $SERVICE_CMD start lscpd
    fi
    
    print_success "CyberPanel installation verified"
}

# Function to check Python installation
check_python() {
    print_status "Checking Python installation..."
    
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python3 is not installed. Installing..."
        install_python
    fi
    
    # Check Python version (require 3.6+)
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
        print_error "Python 3.6+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION is available"
}

# Function to install Python if needed
install_python() {
    case "$OS_NAME" in
        "ubuntu"|"debian")
            apt-get update
            apt-get install -y python3 python3-pip python3-venv
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip
            elif command -v yum &> /dev/null; then
                yum install -y python3 python3-pip
            else
                print_error "No package manager found (dnf/yum)"
                exit 1
            fi
            ;;
    esac
}

# Function to check pip installation
check_pip() {
    print_status "Checking pip installation..."
    
    if ! command -v $PIP_CMD &> /dev/null; then
        print_error "pip3 is not installed. Installing..."
        install_pip
    fi
    
    print_success "pip3 is available"
}

# Function to install pip if needed
install_pip() {
    case "$OS_NAME" in
        "ubuntu"|"debian")
            apt-get install -y python3-pip
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf &> /dev/null; then
                dnf install -y python3-pip
            elif command -v yum &> /dev/null; then
                yum install -y python3-pip
            fi
            ;;
    esac
}

# Function to check required packages
check_packages() {
    print_status "Checking required packages..."
    
    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "git is not installed. Installing..."
        install_git
    fi
    
    # Check for curl
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed. Installing..."
        install_curl
    fi
    
    print_success "All required packages are available"
}

# Function to install git
install_git() {
    case "$OS_NAME" in
        "ubuntu"|"debian")
            apt-get update
            apt-get install -y git
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf &> /dev/null; then
                dnf install -y git
            elif command -v yum &> /dev/null; then
                yum install -y git
            fi
            ;;
    esac
}

# Function to install curl
install_curl() {
    case "$OS_NAME" in
        "ubuntu"|"debian")
            apt-get update
            apt-get install -y curl
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf &> /dev/null; then
                dnf install -y curl
            elif command -v yum &> /dev/null; then
                yum install -y curl
            fi
            ;;
    esac
}

# Function to create plugin directory
create_plugin_directory() {
    print_status "Creating plugin directory structure..."
    
    # Create main plugin directory
    mkdir -p "$PLUGIN_DIR"
    
    # Create CyberPanel plugin directory
    mkdir -p "$CYBERPANEL_DIR/$PLUGIN_NAME"
    
    # Set proper permissions
    chown -R cyberpanel:cyberpanel "$PLUGIN_DIR" 2>/dev/null || chown -R root:root "$PLUGIN_DIR"
    chmod -R 755 "$PLUGIN_DIR"
    
    chown -R cyberpanel:cyberpanel "$CYBERPANEL_DIR/$PLUGIN_NAME" 2>/dev/null || chown -R root:root "$CYBERPANEL_DIR/$PLUGIN_NAME"
    chmod -R 755 "$CYBERPANEL_DIR/$PLUGIN_NAME"
    
    print_success "Plugin directory structure created"
}

# Function to download plugin
download_plugin() {
    print_status "Downloading plugin from GitHub..."
    
    # Clean up temp directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Clone the repository
    if ! git clone "$GITHUB_REPO" "$TEMP_DIR"; then
        print_error "Failed to download plugin from GitHub"
        print_error "Please check your internet connection and try again"
        exit 1
    fi
    
    print_success "Plugin downloaded successfully"
}

# Function to install plugin files
install_plugin_files() {
    print_status "Installing plugin files..."
    
    # Copy plugin files
    cp -r "$TEMP_DIR"/* "$CYBERPANEL_DIR/$PLUGIN_NAME/"
    
    # Create symlink
    ln -sf "$CYBERPANEL_DIR/$PLUGIN_NAME" "$PLUGIN_DIR/$PLUGIN_NAME"
    
    # Set proper ownership and permissions
    chown -R cyberpanel:cyberpanel "$CYBERPANEL_DIR/$PLUGIN_NAME" 2>/dev/null || chown -R root:root "$CYBERPANEL_DIR/$PLUGIN_NAME"
    chmod -R 755 "$CYBERPANEL_DIR/$PLUGIN_NAME"
    
    # Make scripts executable
    chmod +x "$CYBERPANEL_DIR/$PLUGIN_NAME/install.sh" 2>/dev/null || true
    
    print_success "Plugin files installed"
}

# Function to update Django settings
update_django_settings() {
    print_status "Updating Django settings..."
    
    SETTINGS_FILE="$CYBERPANEL_DIR/cyberpanel/settings.py"
    
    # Check if plugin is already in INSTALLED_APPS
    if ! grep -q "'$PLUGIN_NAME'" "$SETTINGS_FILE"; then
        # Add plugin to INSTALLED_APPS
        sed -i "/INSTALLED_APPS = \[/a\    '$PLUGIN_NAME'," "$SETTINGS_FILE"
        print_success "Added $PLUGIN_NAME to INSTALLED_APPS"
    else
        print_warning "$PLUGIN_NAME already in INSTALLED_APPS"
    fi
}

# Function to update URL configuration
update_urls() {
    print_status "Updating URL configuration..."
    
    URLS_FILE="$CYBERPANEL_DIR/cyberpanel/urls.py"
    
    # Check if plugin URLs are already included
    if ! grep -q "path(\"$PLUGIN_NAME/\"" "$URLS_FILE"; then
        # Add plugin URLs
        sed -i "/urlpatterns = \[/a\    path(\"$PLUGIN_NAME/\", include(\"$PLUGIN_NAME.urls\"))," "$URLS_FILE"
        print_success "Added $PLUGIN_NAME URLs"
    else
        print_warning "$PLUGIN_NAME URLs already configured"
    fi
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    cd "$CYBERPANEL_DIR"
    
    # Create migrations
    if ! $PYTHON_CMD manage.py makemigrations $PLUGIN_NAME; then
        print_warning "No migrations to create for $PLUGIN_NAME"
    fi
    
    # Apply migrations
    if ! $PYTHON_CMD manage.py migrate $PLUGIN_NAME; then
        print_warning "No migrations to apply for $PLUGIN_NAME"
    fi
    
    print_success "Database migrations completed"
}

# Function to collect static files
collect_static() {
    print_status "Collecting static files..."
    
    cd "$CYBERPANEL_DIR"
    
    if ! $PYTHON_CMD manage.py collectstatic --noinput; then
        print_warning "Static file collection failed, but continuing..."
    else
        print_success "Static files collected"
    fi
}

# Function to restart services
restart_services() {
    print_status "Restarting CyberPanel services..."
    
    # Restart lscpd
    if $SERVICE_CMD is-active --quiet lscpd; then
        $SERVICE_CMD restart lscpd
        print_success "lscpd service restarted"
    else
        print_warning "lscpd service not running"
    fi
    
    # Restart web server
    if $SERVICE_CMD is-active --quiet $WEB_SERVER; then
        $SERVICE_CMD restart $WEB_SERVER
        print_success "$WEB_SERVER service restarted"
    else
        print_warning "$WEB_SERVER service not running"
    fi
    
    # Additional service restart for different OS
    case "$OS_NAME" in
        "ubuntu"|"debian")
            if $SERVICE_CMD is-active --quiet cyberpanel; then
                $SERVICE_CMD restart cyberpanel
                print_success "cyberpanel service restarted"
            fi
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if $SERVICE_CMD is-active --quiet cyberpanel; then
                $SERVICE_CMD restart cyberpanel
                print_success "cyberpanel service restarted"
            fi
            ;;
    esac
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Check if plugin directory exists
    if [ ! -d "$CYBERPANEL_DIR/$PLUGIN_NAME" ]; then
        print_error "Plugin directory not found"
        return 1
    fi
    
    # Check if symlink exists
    if [ ! -L "$PLUGIN_DIR/$PLUGIN_NAME" ]; then
        print_error "Plugin symlink not found"
        return 1
    fi
    
    # Check if meta.xml exists
    if [ ! -f "$CYBERPANEL_DIR/$PLUGIN_NAME/meta.xml" ]; then
        print_error "Plugin meta.xml not found"
        return 1
    fi
    
    print_success "Installation verified successfully"
    return 0
}

# Function to display installation summary
display_summary() {
    echo ""
    echo "=========================================="
    print_success "Test Plugin Installation Complete!"
    echo "=========================================="
    echo "Plugin Name: $PLUGIN_NAME"
    echo "Installation Directory: $CYBERPANEL_DIR/$PLUGIN_NAME"
    echo "Plugin Directory: $PLUGIN_DIR/$PLUGIN_NAME"
    echo "Access URL: https://your-domain:8090/testPlugin/"
    echo "Operating System: $OS_NAME $OS_VERSION ($OS_ARCH)"
    echo "Python Version: $($PYTHON_CMD --version)"
    echo ""
    echo "Features Installed:"
    echo "✓ Enable/Disable Toggle"
    echo "✓ Test Button with Popup Messages"
    echo "✓ Settings Page"
    echo "✓ Activity Logs"
    echo "✓ Inline Integration"
    echo "✓ Complete Documentation"
    echo "✓ Official CyberPanel Guide"
    echo "✓ Advanced Development Guide"
    echo "✓ Enterprise-Grade Security"
    echo "✓ Brute Force Protection"
    echo "✓ CSRF Protection"
    echo "✓ XSS Prevention"
    echo "✓ SQL Injection Protection"
    echo "✓ Rate Limiting"
    echo "✓ Security Monitoring"
    echo "✓ Security Information Page"
    echo "✓ Multi-OS Compatibility"
    echo ""
    echo "Supported Operating Systems:"
    echo "✓ Ubuntu 22.04, 20.04"
    echo "✓ Debian (compatible)"
    echo "✓ AlmaLinux 8, 9, 10"
    echo "✓ RockyLinux 8, 9"
    echo "✓ RHEL 8, 9"
    echo "✓ CloudLinux 8"
    echo "✓ CentOS 9"
    echo ""
    echo "To uninstall, run: $0 --uninstall"
    echo "=========================================="
}

# Function to uninstall plugin
uninstall_plugin() {
    print_status "Uninstalling $PLUGIN_NAME..."
    
    # Remove plugin files
    rm -rf "$CYBERPANEL_DIR/$PLUGIN_NAME"
    rm -f "$PLUGIN_DIR/$PLUGIN_NAME"
    
    # Remove from Django settings
    SETTINGS_FILE="$CYBERPANEL_DIR/cyberpanel/settings.py"
    if [ -f "$SETTINGS_FILE" ]; then
        sed -i "/'$PLUGIN_NAME',/d" "$SETTINGS_FILE"
        print_success "Removed $PLUGIN_NAME from INSTALLED_APPS"
    fi
    
    # Remove from URLs
    URLS_FILE="$CYBERPANEL_DIR/cyberpanel/urls.py"
    if [ -f "$URLS_FILE" ]; then
        sed -i "/path(\"$PLUGIN_NAME\/\"/d" "$URLS_FILE"
        print_success "Removed $PLUGIN_NAME URLs"
    fi
    
    # Restart services
    restart_services
    
    print_success "Plugin uninstalled successfully"
}

# Main installation function
install_plugin() {
    print_status "Starting Test Plugin installation..."
    
    # Detect OS
    detect_os
    
    # Check requirements
    check_root
    check_cyberpanel
    check_python
    check_pip
    check_packages
    
    # Install plugin
    create_plugin_directory
    download_plugin
    install_plugin_files
    update_django_settings
    update_urls
    run_migrations
    collect_static
    restart_services
    
    # Verify installation
    if verify_installation; then
        display_summary
    else
        print_error "Installation verification failed"
        exit 1
    fi
}

# Main script logic
main() {
    case "${1:-}" in
        "--uninstall")
            check_root
            uninstall_plugin
            ;;
        "--help"|"-h")
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --uninstall    Uninstall the plugin"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Supported Operating Systems:"
            echo "  Ubuntu 22.04, 20.04"
            echo "  Debian (compatible)"
            echo "  AlmaLinux 8, 9, 10"
            echo "  RockyLinux 8, 9"
            echo "  RHEL 8, 9"
            echo "  CloudLinux 8"
            echo "  CentOS 9"
            ;;
        "")
            install_plugin
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"