@echo off
REM WebAuthn Installation Script for CyberPanel (Windows)
REM This script helps install and configure WebAuthn/Passkey authentication

echo ==========================================
echo CyberPanel WebAuthn Installation Script
echo ==========================================

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as administrator
    pause
    exit /b 1
)

REM Check if CyberPanel is installed
if not exist "C:\usr\local\CyberCP" (
    echo Error: CyberPanel not found at C:\usr\local\CyberCP
    echo Please install CyberPanel first
    pause
    exit /b 1
)

echo [OK] CyberPanel installation found

REM Navigate to CyberPanel directory
cd /d C:\usr\local\CyberCP

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: Python not found. Please ensure CyberPanel is properly installed
    pause
    exit /b 1
)

echo [OK] Python installation found

REM Run database migrations
echo Running database migrations...
python manage.py makemigrations loginSystem
if %errorLevel% equ 0 (
    echo [OK] Database migrations created
) else (
    echo Error: Failed to create migrations
    pause
    exit /b 1
)

python manage.py migrate
if %errorLevel% equ 0 (
    echo [OK] Database migrations applied
) else (
    echo Error: Failed to apply migrations
    pause
    exit /b 1
)

REM Check if static files directory exists
if not exist "static\loginSystem" (
    echo Creating static files directory...
    mkdir static\loginSystem
)

REM Check if WebAuthn JavaScript file exists
if not exist "static\loginSystem\webauthn.js" (
    echo Warning: WebAuthn JavaScript file not found
    echo Please ensure webauthn.js is in static\loginSystem\
    echo You can copy it from the source files
)

REM Test the installation
echo Testing WebAuthn installation...
python -c "import sys; sys.path.append('C:/usr/local/CyberCP'); from loginSystem.webauthn_models import WebAuthnCredential, WebAuthnChallenge, WebAuthnSettings; print('[OK] WebAuthn models imported successfully')"
if %errorLevel% equ 0 (
    echo [OK] WebAuthn installation test passed
) else (
    echo Error: WebAuthn installation test failed
    pause
    exit /b 1
)

REM Create configuration file
echo Creating WebAuthn configuration...
(
echo # WebAuthn Configuration for CyberPanel
echo # Update these values according to your setup
echo.
echo WEBAUTHN_CONFIG = {
echo     'RP_ID': 'cyberpanel.local',  # Replace with your actual domain
echo     'RP_NAME': 'CyberPanel',
echo     'ORIGIN': 'https://cyberpanel.local:8090',  # Replace with your actual origin
echo     'CHALLENGE_TIMEOUT': 300,  # 5 minutes
echo     'MAX_CREDENTIALS_PER_USER': 10,
echo     'DEFAULT_TIMEOUT_SECONDS': 60,
echo }
echo.
echo # Instructions:
echo # 1. Update RP_ID to your actual domain ^(e.g., 'yourdomain.com'^)
echo # 2. Update ORIGIN to your actual origin ^(e.g., 'https://yourdomain.com:8090'^)
echo # 3. Restart CyberPanel after making changes
) > webauthn_config.py

echo [OK] Configuration file created at C:\usr\local\CyberCP\webauthn_config.py

echo.
echo ==========================================
echo WebAuthn Installation Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Update the configuration file: C:\usr\local\CyberCP\webauthn_config.py
echo 2. Replace 'cyberpanel.local' with your actual domain
echo 3. Replace 'https://cyberpanel.local:8090' with your actual origin
echo 4. Restart CyberPanel services
echo 5. Access CyberPanel and go to User Management to enable WebAuthn
echo.
echo Features available:
echo - Passkey registration and management
echo - Passwordless login option
echo - Multiple device support
echo - Admin management interface
echo.
echo For more information, see: C:\usr\local\CyberCP\to-do\WEBAUTHN_IMPLEMENTATION.md
echo.
pause
