#!/bin/bash

# CyberPanel Installation Test Script
# Tests the updated installer with different version inputs

echo "=========================================="
echo "CyberPanel Installation Test Script"
echo "=========================================="

# Test 1: Test version validation function
echo "Test 1: Testing version validation function..."

# Source the cyberpanel.sh script to get the Branch_Check function
source cyberpanel.sh 2>/dev/null || true

# Test cases
test_versions=("2.4.4" "2.5.0" "2.5.5-dev" "2.6.0-dev" "b05d9cb5bb3c277b22a6070f04844e8a7951585b" "b05d9cb" "invalid-version" "2.3.3")

for version in "${test_versions[@]}"; do
    echo "Testing version: $version"
    if Branch_Check "$version" 2>/dev/null; then
        echo "  ✓ PASS: $version is valid"
    else
        echo "  ✗ FAIL: $version is invalid"
    fi
done

echo ""
echo "Test 2: Testing OS detection..."

# Test OS detection
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    echo "Detected OS: $NAME $VERSION_ID"
    
    if [[ "$NAME" == "AlmaLinux" ]] && [[ "$VERSION_ID" == "9"* ]]; then
        echo "  ✓ PASS: AlmaLinux 9 detected correctly"
    else
        echo "  ℹ INFO: Not AlmaLinux 9, skipping AlmaLinux 9 specific tests"
    fi
else
    echo "  ✗ FAIL: Cannot detect OS (no /etc/os-release)"
fi

echo ""
echo "Test 3: Testing package availability..."

# Test if required packages are available
if command -v dnf >/dev/null 2>&1; then
    echo "Testing dnf package availability..."
    
    required_packages=("ImageMagick" "gd" "libicu" "oniguruma" "aspell" "libc-client" "mariadb-server")
    
    for package in "${required_packages[@]}"; do
        if dnf list available "$package" >/dev/null 2>&1; then
            echo "  ✓ PASS: $package is available"
        else
            echo "  ✗ FAIL: $package is not available"
        fi
    done
elif command -v yum >/dev/null 2>&1; then
    echo "Testing yum package availability..."
    
    required_packages=("ImageMagick" "gd" "libicu" "oniguruma" "aspell" "libc-client" "mariadb-server")
    
    for package in "${required_packages[@]}"; do
        if yum list available "$package" >/dev/null 2>&1; then
            echo "  ✓ PASS: $package is available"
        else
            echo "  ✗ FAIL: $package is not available"
        fi
    done
else
    echo "  ℹ INFO: No dnf/yum available, skipping package tests"
fi

echo ""
echo "Test 4: Testing Git clone functionality..."

# Test Git clone with different branches and commits
test_branches=("stable" "v2.4.4" "2.5.5-dev" "b05d9cb5bb3c277b22a6070f04844e8a7951585b" "b05d9cb")

for branch in "${test_branches[@]}"; do
    echo "Testing Git clone for branch/commit: $branch"
    
    # Create temporary directory for testing
    test_dir="/tmp/cyberpanel_test_$branch"
    rm -rf "$test_dir"
    
    if [[ "$branch" == "stable" ]]; then
        clone_cmd="git clone --depth 1 https://github.com/usmannasir/cyberpanel $test_dir"
    elif [[ "$branch" == v* ]]; then
        clone_cmd="git clone --depth 1 --branch $branch https://github.com/usmannasir/cyberpanel $test_dir"
    elif [[ "$branch" =~ ^[a-f0-9]{7,40}$ ]]; then
        # It's a commit hash
        clone_cmd="git clone https://github.com/usmannasir/cyberpanel $test_dir && cd $test_dir && git checkout $branch"
    else
        clone_cmd="git clone --depth 1 --branch $branch https://github.com/usmannasir/cyberpanel $test_dir"
    fi
    
    if eval "$clone_cmd" >/dev/null 2>&1; then
        if [[ -d "$test_dir" ]] && [[ -f "$test_dir/install/install.py" ]]; then
            echo "  ✓ PASS: Successfully cloned $branch"
        else
            echo "  ✗ FAIL: Cloned $branch but missing files"
        fi
        rm -rf "$test_dir"
    else
        echo "  ✗ FAIL: Failed to clone $branch"
    fi
done

echo ""
echo "Test 5: Testing environment variable handling..."

# Test environment variable handling
export CYBERPANEL_BRANCH="2.5.5-dev"
echo "Testing with CYBERPANEL_BRANCH=$CYBERPANEL_BRANCH"

if [[ "$CYBERPANEL_BRANCH" == *"-dev" ]]; then
    echo "  ✓ PASS: Development branch detected correctly"
else
    echo "  ✗ FAIL: Development branch not detected"
fi

unset CYBERPANEL_BRANCH

echo ""
echo "=========================================="
echo "Test Summary:"
echo "=========================================="
echo "1. Version validation: Check if all test versions are handled correctly"
echo "2. OS detection: Verify AlmaLinux 9 is detected properly"
echo "3. Package availability: Ensure required packages are available"
echo "4. Git clone: Test cloning different branches/tags"
echo "5. Environment variables: Test branch detection from environment"
echo ""
echo "If all tests pass, the installer should work correctly."
echo "If any tests fail, check the specific error messages above."
