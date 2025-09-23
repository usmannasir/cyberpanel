#!/bin/bash

# CyberPanel Repository Sync Fix Script
# This script resolves the current sync conflict between GitHub and Gitee

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="https://github.com/usmannasir/cyberpanel.git"
GITEE_REPO="https://gitee.com/qtwrk/cyberpanel.git"
TEMP_DIR="/tmp/cyberpanel-sync-$(date +%s)"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists git; then
        print_error "Git is not installed. Please install git first."
        exit 1
    fi
    
    if ! command_exists ssh; then
        print_warning "SSH is not available. HTTPS will be used for authentication."
    fi
    
    print_success "Prerequisites check completed"
}

# Setup Git configuration
setup_git_config() {
    print_status "Setting up Git configuration..."
    
    git config --global user.name "CyberPanel Sync Bot"
    git config --global user.email "support@cyberpanel.net"
    git config --global init.defaultBranch main
    git config --global pull.rebase false
    git config --global push.default simple
    
    print_success "Git configuration completed"
}

# Clone and sync repositories
sync_repositories() {
    print_status "Starting repository synchronization..."
    
    # Create temporary directory
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Clone GitHub repository
    print_status "Cloning GitHub repository..."
    git clone --mirror "$GITHUB_REPO" cyberpanel.git
    cd cyberpanel.git
    
    # Add Gitee remote
    print_status "Adding Gitee remote..."
    git remote add gitee "$GITEE_REPO"
    
    # Fetch from Gitee to check current state
    print_status "Fetching from Gitee..."
    if git fetch gitee --all --prune; then
        print_success "Successfully fetched from Gitee"
    else
        print_warning "Failed to fetch from Gitee, continuing with force push"
    fi
    
    # Push all branches and tags to Gitee
    print_status "Pushing all branches to Gitee..."
    if git push gitee --all --force; then
        print_success "Successfully pushed all branches to Gitee"
    else
        print_error "Failed to push branches to Gitee"
        exit 1
    fi
    
    print_status "Pushing all tags to Gitee..."
    if git push gitee --tags --force; then
        print_success "Successfully pushed all tags to Gitee"
    else
        print_warning "Failed to push some tags to Gitee"
    fi
    
    print_success "Repository synchronization completed"
}

# Verify sync
verify_sync() {
    print_status "Verifying synchronization..."
    
    cd "$TEMP_DIR/cyberpanel.git"
    
    # Check if main branches exist
    for branch in main stable v2.5.5-dev v2.4.0-dev; do
        if git show-ref --verify --quiet "refs/remotes/gitee/$branch"; then
            print_success "Branch $branch exists on Gitee"
        else
            print_error "Branch $branch missing on Gitee"
        fi
    done
    
    # Show recent commits
    print_status "Recent commits on main branch:"
    git log --oneline -5 refs/remotes/origin/main || true
}

# Cleanup
cleanup() {
    print_status "Cleaning up temporary files..."
    
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        print_success "Cleanup completed"
    fi
}

# Main execution
main() {
    print_status "Starting CyberPanel Repository Sync Fix"
    print_status "========================================"
    
    # Set up error handling
    trap cleanup EXIT
    
    # Execute steps
    check_prerequisites
    setup_git_config
    sync_repositories
    verify_sync
    
    print_success "Repository sync fix completed successfully!"
    print_status "The GitHub Actions workflow should now work properly."
}

# Run main function
main "$@"
